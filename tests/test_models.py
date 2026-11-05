import queue
import threading

import pytest
import torch

from src.models import ClinicalGenerator, resolve_torch_dtype


class _FakeInputs(dict):
    def to(self, device):
        return self


class _FakeTokenizer:
    eos_token_id = 0

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "prompt"

    def __call__(self, prompt, return_tensors="pt"):
        return _FakeInputs(input_ids=torch.zeros((1, 3), dtype=torch.long))

    def decode(self, token_ids, **kwargs):
        return "x" * len(token_ids)


class _ExplodingModel:
    def generate(self, **kwargs):
        raise RuntimeError("CUDA out of memory")


def test_resolve_torch_dtype_on_cpu():
    assert resolve_torch_dtype(torch.device("cpu"), "auto") == torch.float32
    assert resolve_torch_dtype(torch.device("cpu"), "fp32") == torch.float32

    with pytest.raises(ValueError):
        resolve_torch_dtype(torch.device("cpu"), "bf16")

    with pytest.raises(ValueError):
        resolve_torch_dtype(torch.device("cpu"), "unknown")


def test_generate_stream_propagates_model_errors_without_hanging():
    generator = object.__new__(ClinicalGenerator)
    generator.tokenizer = _FakeTokenizer()  # type: ignore[assignment]
    generator.model = _ExplodingModel()
    generator.device = torch.device("cpu")

    result: queue.Queue = queue.Queue()

    def consume():
        try:
            list(generator.generate_stream("system", "user"))
            result.put(("ok", None))
        except BaseException as exc:  # noqa: BLE001 - the test inspects the error
            result.put(("error", exc))

    worker = threading.Thread(target=consume, daemon=True)
    worker.start()
    worker.join(timeout=5.0)

    assert not worker.is_alive(), "generate_stream blocked instead of propagating the model error"

    kind, value = result.get_nowait()
    assert kind == "error"
    assert isinstance(value, RuntimeError)
    assert "CUDA out of memory" in str(value)
