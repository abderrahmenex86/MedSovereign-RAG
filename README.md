# MedSovereign-RAG

A retrieval-augmented question answering system for clinical text, built
directly on PyTorch, Hugging Face Transformers, and FAISS rather than a RAG
framework. It answers from retrieved passages and refuses to answer when it
cannot verify the result.

![System architecture](docs/figs/architecture-1.png)

## What it does

- Retrieves with two methods at once: dense search over PubMedBERT embeddings in
  FAISS, and BM25 for exact drug names and clinical terms.
- Reranks the merged candidates with a cross-encoder, which reads query and
  passage together, so only the strongest contexts reach the generator.
- Deduplicates by source document, so three chunks of the same article cannot
  crowd out the rest of the evidence.
- Runs the answer through a state machine where an LLM judge checks whether each
  claim is supported by the retrieved context **and** whether it answers the
  question.
- Rewrites the query and retrieves again on a failed check, up to three
  attempts, then refuses instead of returning an unverified draft.

## Why no framework

LangChain and LlamaIndex hide the execution graph, and with it the control over
retrieval order, prompt construction, and streaming events that this pipeline
needs. Keeping the loop explicit also makes the failure modes visible: every
attempt is written to a trace you can inspect.

## Requirements

- Python 3.11 or newer.
- 24 GB of GPU memory is recommended. Zephyr-7B in bfloat16 is about 14 GB of
  weights, plus the embedder, reranker, and KV cache. 16 GB cards may run out of
  memory; `MODEL_DTYPE=fp16` helps on GPUs without bfloat16 (T4, V100).
- No GPU? Set `GENERATOR_BACKEND=ollama` and run a quantized model such as
  `medgemma:4b` (3.3 GB). Expect roughly 5–10 tokens/sec on a laptop CPU.
- The pipeline runs on CPU, but a 7B generator on CPU is far too slow for
  interactive use.
- About 20 GB of disk for model weights, plus the corpus and index cache.

## Run it

```bash
git clone https://github.com/abderrahmenex86/MedSovereign-RAG
cd MedSovereign-RAG

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python setup_dataset.py   # download and normalize the MedQuad corpus
python main.py            # start the FastAPI server
```

The first start downloads the models and builds the indices; later starts load
the cache from `artifacts/index_cache/`. The server listens on
`http://127.0.0.1:8000` by default. Check readiness with:

```bash
curl http://127.0.0.1:8000/health
```

The frontend runs separately:

```bash
cd frontend
npm install
npm run dev
```

If the API is not on `localhost:8000`, copy `frontend/.env.example` to
`frontend/.env` and set `VITE_API_URL`.

To preview the interface without starting the API, run the frontend in demo mode:

```bash
cd frontend
VITE_DEMO_MODE=true npm run dev
# or open http://localhost:5173/?demo=1
```

### No GPU: run the generator through Ollama

The embedder and reranker stay local; only the generator moves to Ollama.

```bash
sudo systemctl enable --now ollama
ollama pull medgemma:4b

GENERATOR_BACKEND=ollama python main.py
```

The first request loads the model into memory (about a minute on a laptop CPU).
`OLLAMA_KEEP_ALIVE=10m` keeps it resident between requests so later queries do
not pay that cost again. `medgemma:4b` follows the grounding and judge prompts
reasonably well, but a 4B model is a weaker auditor than Zephyr-7B.
On a CPU-only laptop (Ryzen 5 4650U, 14 GB RAM) a verified answer took about 62
seconds, including retrieval and the judge. Embedding the full 21k-chunk corpus
on that CPU takes roughly two hours; the result is cached afterwards. For a
quick demo, build a smaller index:

```bash
MAX_CORPUS_DOCS=1000 GENERATOR_BACKEND=ollama python main.py
```

That indexes about 1,300 chunks in 8–10 minutes. The cache key includes
`MAX_CORPUS_DOCS`, so full and subset indices do not collide. You can also build
the full index once on a GPU machine and copy `artifacts/index_cache/` to the
CPU host.

### GPU box (vast.ai)

For the full-size generator, rent a 24 GB card (RTX 3090/4090, A5000, L4) with at
least 50 GB of disk and 16 GB of host RAM. A 3090 on vast.ai is typically around
$0.20–0.35/hour, so a short demo costs well under $1.

On a 24 GB card, the recommended generator is **`qwen3:14b`** through Ollama
(~9 GB at Q4, leaving room for the embedder, reranker, and KV cache). Zephyr-7B
via Transformers still works as a no-Ollama fallback.

1. Rent an **on-demand** (not interruptible) PyTorch/CUDA 12.x image.
2. From your machine:

   ```bash
   ./push.sh root@HOST -p PORT
   ```

3. On the instance, install Ollama and pull the model:

   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   nohup ollama serve > /tmp/ollama.log 2>&1 &
   ollama pull qwen3:14b

   cd /workspace/MedSovereign-RAG
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt

   cp deploy/vast.env.example .env
   python scripts/fetch_europepmc.py --limit 100000 --include-pubmedqa
   python scripts/build_index.py
   python scripts/evaluate_retrieval.py --limit 200

   python main.py
   ```

4. Tunnel the API to your laptop and run the UI locally. This keeps the
   unauthenticated API off the public internet:

   ```bash
   ssh -p PORT root@HOST -L 8000:127.0.0.1:8000
   # in another shell
   cd frontend && npm run dev
   ```

5. Fetch the GPU-built index and its corpus so the laptop does not spend hours
   embedding:

   ```bash
   ./fetch.sh root@HOST -p PORT --all
   scp -P PORT root@HOST:/workspace/MedSovereign-RAG/dataset/pubmed.jsonl dataset/
   ```

The index cache key hashes the corpus contents, so a cache built on the GPU box
matches the same corpus on the laptop. Use the same corpus file on both sides
(`dataset/pubmed.jsonl` for the literature corpus). `push.sh` excludes `.env`;
keep the HF token out of the repo. Public models do not need a token.

To use Zephyr instead, remove `GENERATOR_BACKEND` from the instance `.env` (or set
it to `transformers`). If the image does not already have a CUDA-enabled torch,
install the wheel that matches its CUDA version before the requirements file, for
example `pip install torch --index-url https://download.pytorch.org/whl/cu124`.
`MODEL_DTYPE=auto` selects bfloat16 on Ampere/Ada and float16 on T4/V100.

A 12–16 GB card also works with `GENERATOR_BACKEND=ollama` and a quantized
`qwen3:8b` (~5 GB) or `medgemma:4b` (3.3 GB), which is cheaper and faster but a
weaker judge.

## Corpus

The default `setup_dataset.py` downloads MedQuad, which is useful for a quick
demo but is a set of consumer Q&A pairs, not clinical evidence. For a real
retrieval workload, use the Europe PMC JSONL corpus. PubMed's ESearch only
returns the first 9,999 records; Europe PMC exposes the same MEDLINE records
with cursor-based paging.

```bash
python scripts/fetch_europepmc.py --limit 100000 --include-pubmedqa

CORPUS_FORMAT=jsonl CORPUS_PATH=dataset/pubmed.jsonl python scripts/build_index.py
CORPUS_FORMAT=jsonl CORPUS_PATH=dataset/pubmed.jsonl python main.py
```

The default query targets guidelines, systematic reviews, meta-analyses, and
randomized trials from 2015 onward. `--include-pubmedqa` adds the PMIDs needed by
the retrieval evaluation. The fetcher writes `dataset/pubmed_pmids.txt`; continue
an interrupted download with `--reuse-manifest --resume`. Corpus files are
ignored by git and fetched at build time.

Evaluate retrieval against PubMedQA's labeled PMIDs:

```bash
CORPUS_FORMAT=jsonl CORPUS_PATH=dataset/pubmed.jsonl \
  python scripts/evaluate_retrieval.py --limit 200 --k 10
```

This writes recall@1/5/10 and MRR@10 to `artifacts/eval/pubmedqa.json`.
`missing_targets` reports questions whose labeled PMID is not in the corpus, so
fetch with `--include-pubmedqa` before trusting the numbers.

100k abstracts produce roughly 110k–130k chunks. Build that on the GPU box
(roughly 10–20 minutes) and copy `artifacts/index_cache/` back. On CPU, index a
few thousand documents instead, for example `MAX_CORPUS_DOCS=2000`.

The repository does not redistribute the corpus. PubMed abstracts remain under
NLM and publisher terms. PMC full text, DailyMed, and MedlinePlus adapters are the
next sources.

## Configuration

Every setting has an environment variable; see `.env.example` for the full list.

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | API bind address |
| `GENERATOR_MODEL` | `HuggingFaceH4/zephyr-7b-beta` | HF generator (transformers backend) |
| `MODEL_DTYPE` | `auto` | `auto`, `bf16`, `fp16`, or `fp32` |
| `GENERATOR_BACKEND` | `transformers` | `transformers` or `ollama` |
| `OLLAMA_MODEL` | `medgemma:4b` | Any pulled Ollama model |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server |
| `OLLAMA_NUM_CTX` | `8192` | Generator context window |
| `OLLAMA_KEEP_ALIVE` | `10m` | How long the model stays loaded |
| `OLLAMA_THINK` | unset | Set `false` for thinking models such as Qwen3 |
| `OLLAMA_REQUEST_TIMEOUT` | `600` | Read timeout in seconds |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `300` / `50` | Word-level chunking |
| `CORPUS_PATH` | `dataset/medquad_corpus.json` | Corpus file |
| `CORPUS_FORMAT` | `medquad` | `medquad` or `jsonl` |
| `MAX_CORPUS_DOCS` | `0` | Index only the first N documents (`0` = all) |
| `MAX_CONCURRENT_REQUESTS` | `1` | Serialize jobs on one GPU |
| `PERSIST_TRACES` | `true` | Write traces to `TRACE_DIR` |
| `TRACE_RETENTION` | `200` | Number of trace files kept |
| `MIN_RERANK_SCORE` | unset | Optional abstention threshold on the reranker logit |
| `CORS_ORIGINS` | localhost dev servers | Comma-separated allowed origins |

Trace files contain the raw query and the retrieved context. Disable them with
`PERSIST_TRACES=false` before pointing the system at anything sensitive.
The API has no authentication. Binding `HOST` to `0.0.0.0` exposes the model to
everyone who can reach the machine; keep the default loopback bind or put a
reverse proxy with auth in front of it.

## API

`POST /api/ask`

```json
{
  "query": "What are the symptoms and treatments for acute bronchitis?",
  "max_retries": 3,
  "top_k_retrieve": 15,
  "top_k_generate": 3
}
```

The response is newline-delimited JSON. `max_retries` is the total number of
attempts, including the first. Events:

| Event | Meaning |
| --- | --- |
| `status` | Pipeline progress (`search`, `rerank`, `drafting`, `critique`, `success`) |
| `sources` | Retrieved chunks with `doc_id`, `question`, `text`, and `rerank_score` |
| `token` | One generated token |
| `correction` | Verification failed; a rewrite is coming |
| `error` | The pipeline failed; a `done` event follows |
| `done` | Final trace with `status` (`SUCCESS`, `REFUSED`, `CANCELLED`, `ERROR`) |

`GET /health` returns the device, corpus size, model names, and startup time, or
`503` while models are loading.

## How it works

![Agentic flow](docs/figs/flowchart-1.png)

A question is embedded and searched both ways, the merged candidates are
deduplicated by document and reranked, and the generator drafts an answer from
the surviving passages. The judge compares the draft against those passages and
the original question. A draft that fails is discarded, the question is
rewritten, and retrieval repeats. Three failed attempts produce a refusal rather
than a partial answer.

Retrieval indexes the question together with the answer, because MedQuad answers
rarely repeat the topic they belong to. The generator is decoded greedily so a
trace can be reproduced. The judge returns a single token, parsed by the first
`PASS`/`FAIL` it emits. The generator can be Zephyr-7B loaded by Transformers or
a quantized model served by Ollama; the engine only depends on the streaming
interface.

## Development

```bash
pip install -r requirements-dev.txt
pytest
ruff check .
mypy .

cd frontend
npm run lint
npm run build
```

## Limits

- By default, answers are grounded in MedQuad, which is a corpus of
  question-answer pairs rather than real clinical notes. The PubMed JSONL corpus
  (`CORPUS_FORMAT=jsonl`) is the recommended alternative for evidence-grade
  retrieval. Free-text clinical notes are still untested.
- The judge is another language model. A confidently wrong draft that matches the
  retrieved text can still pass. No benchmark or human evaluation is committed
  yet, so the self-correction loop's benefit over a single pass is unmeasured.
- On CPU, a 4B Ollama model generates roughly 5–10 tokens/sec; a full answer
  with verification can take a minute or more.
- The embedding model is licensed CC BY-NC 2.0, which forbids commercial use.
  MedGemma has its own license. See `NOTICE.md`.
- Not a medical device and not validated for clinical use.

## Stack

Python · PyTorch · Hugging Face Transformers · FAISS · BM25 · FastAPI · React ·
Ollama (optional)

## License

MIT for the source code. Third-party model and dataset licenses are listed in
`NOTICE.md`.
