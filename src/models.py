from threading import Event, Thread

import torch
import torch.nn.functional as F
from tqdm.auto import tqdm
from transformers import (
    AutoModel,
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    StoppingCriteria,
    TextIteratorStreamer,
)


def resolve_torch_dtype(device, preference="auto"):
    """Pick a dtype the device actually supports.

    bfloat16 is not available on T4/V100, which are common on cheap GPU
    rentals, so requesting it unconditionally breaks at generation time.
    """
    normalized = (preference or "auto").lower()
    supported = {
        "auto",
        "bf16",
        "bfloat16",
        "fp16",
        "float16",
        "half",
        "fp32",
        "float32",
    }

    if normalized not in supported:
        raise ValueError(f"Unknown MODEL_DTYPE={preference!r}; use auto, bf16, fp16, or fp32")

    if normalized in {"fp32", "float32"}:
        return torch.float32

    if device.type != "cuda":
        if normalized in {"bf16", "bfloat16", "fp16", "float16", "half"}:
            raise ValueError(
                f"MODEL_DTYPE={preference} requires CUDA; use 'auto' or 'fp32' on CPU"
            )
        return torch.float32

    supports_bfloat16 = torch.cuda.is_bf16_supported()

    if normalized in {"bf16", "bfloat16"}:
        if not supports_bfloat16:
            raise ValueError(
                "MODEL_DTYPE=bfloat16 requested but this GPU does not support bfloat16; "
                "use 'auto' or 'fp16' instead"
            )
        return torch.bfloat16

    if normalized in {"fp16", "float16", "half"}:
        return torch.float16

    if normalized == "auto":
        return torch.bfloat16 if supports_bfloat16 else torch.float16

    raise ValueError(f"Unknown MODEL_DTYPE={preference!r}; use auto, bf16, fp16, or fp32")


class ClinicalEmbedder:
    def __init__(self, model_name, device):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(device)
        self.model.eval()
        self.device = device

    @property
    def hidden_size(self):
        return int(self.model.config.hidden_size)

    def encode(self, texts, batch_size=32):
        if not texts:
            return torch.empty((0, self.hidden_size), dtype=torch.float32)

        all_embeddings = []

        for index in tqdm(range(0, len(texts), batch_size), desc="Embedding Corpus", leave=False):
            batch_texts = texts[index : index + batch_size]
            inputs = self.tokenizer(
                batch_texts, padding=True, truncation=True, max_length=512, return_tensors="pt"
            ).to(self.device)

            with torch.inference_mode():
                outputs = self.model(**inputs)

            attention_mask = (
                inputs["attention_mask"].unsqueeze(-1).expand(outputs.last_hidden_state.size()).float()
            )
            sum_embeddings = torch.sum(outputs.last_hidden_state * attention_mask, dim=1)
            sum_mask = torch.clamp(attention_mask.sum(dim=1), min=1e-9)
            embeddings = sum_embeddings / sum_mask
            embeddings = F.normalize(embeddings, p=2, dim=1)

            all_embeddings.append(embeddings.cpu())

        return torch.cat(all_embeddings, dim=0)


class ClinicalReranker:
    def __init__(self, model_name, device):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name).to(device)
        self.model.eval()
        self.device = device

    def score(self, query, candidates, batch_size=16):
        if not candidates:
            return []

        scored = []

        for index in range(0, len(candidates), batch_size):
            batch = candidates[index : index + batch_size]
            pairs = [[query, candidate["text"]] for candidate in batch]
            inputs = self.tokenizer(
                pairs, padding=True, truncation=True, max_length=512, return_tensors="pt"
            ).to(self.device)

            with torch.inference_mode():
                logits = self.model(**inputs).logits

            scores = logits.view(-1).cpu().numpy()
            for candidate, score in zip(batch, scores, strict=True):
                # Copy instead of mutating the shared corpus mapping.
                scored.append({**candidate, "rerank_score": float(score)})

        return sorted(scored, key=lambda item: item["rerank_score"], reverse=True)


class _StopOnEvent(StoppingCriteria):
    """Stop generation when the consumer disconnects."""

    def __init__(self, stop_event):
        self.stop_event = stop_event

    def __call__(self, input_ids, scores, **kwargs):
        return self.stop_event.is_set()


class ClinicalGenerator:
    def __init__(self, model_name, device, dtype_preference="auto"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        dtype = resolve_torch_dtype(device, dtype_preference)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, dtype=dtype).to(device)
        self.model.eval()
        self.device = device

    def _build_inputs(self, system_prompt, user_prompt):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        return self.tokenizer(prompt, return_tensors="pt").to(self.device)

    def generate(self, system_prompt, user_prompt, max_tokens=256):
        inputs = self._build_inputs(system_prompt, user_prompt)

        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        generated_ids = outputs[0][inputs["input_ids"].shape[-1] :]
        decoded = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        if isinstance(decoded, list):
            decoded = decoded[0] if decoded else ""
        return decoded.strip()

    def generate_stream(self, system_prompt, user_prompt, max_tokens=256, timeout=120.0):
        inputs = self._build_inputs(system_prompt, user_prompt)
        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
            timeout=timeout,
        )
        stop_event = Event()
        errors = []

        def run_generation():
            try:
                self.model.generate(
                    **inputs,
                    streamer=streamer,
                    stopping_criteria=[_StopOnEvent(stop_event)],
                    max_new_tokens=max_tokens,
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
            except BaseException as exc:  # noqa: BLE001 - re-raised on the consumer thread
                errors.append(exc)
            finally:
                # Always unblock the consumer, even if generate() raised. Without
                # this the iterator waits on an empty queue forever.
                streamer.end()

        worker = Thread(target=run_generation, daemon=True)
        worker.start()

        try:
            yield from streamer
        finally:
            stop_event.set()
            worker.join(timeout=10.0)

        if errors:
            raise errors[0]
