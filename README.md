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
- Rewrites the query and retrieves again on a failed check, up to three retries,
  then refuses instead of returning an unverified draft.

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

## Configuration

Every setting has an environment variable; see `.env.example` for the full list.

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | API bind address |
| `GENERATOR_MODEL` | `HuggingFaceH4/zephyr-7b-beta` | Answer and judge model |
| `MODEL_DTYPE` | `auto` | `auto`, `bf16`, `fp16`, or `fp32` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `300` / `50` | Word-level chunking |
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

The response is newline-delimited JSON. Events:

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
rewritten, and retrieval repeats. Three failures produce a refusal rather than a
partial answer.

Retrieval indexes the question together with the answer, because MedQuad answers
rarely repeat the topic they belong to. The generator is decoded greedily so a
trace can be reproduced. The judge returns a single token, parsed by the first
`PASS`/`FAIL` it emits.

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

- Answers are grounded in MedQuad, which is a corpus of question-answer pairs
  rather than real clinical notes, so free-text records are untested.
- The judge is another language model. A confidently wrong draft that matches the
  retrieved text can still pass. No benchmark or human evaluation is committed
  yet, so the self-correction loop's benefit over a single pass is unmeasured.
- The embedding model is licensed CC BY-NC 2.0, which forbids commercial use.
  See `NOTICE.md`.
- Not a medical device and not validated for clinical use.

## Stack

Python · PyTorch · Hugging Face Transformers · FAISS · BM25 · FastAPI · React

## License

MIT for the source code. Third-party model and dataset licenses are listed in
`NOTICE.md`.
