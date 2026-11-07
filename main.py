import asyncio
import gc
import os
import threading
import time
from contextlib import asynccontextmanager

import torch
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.config import Config
from src.engine import execute_agentic_rag
from src.index import load_or_build_index
from src.models import ClinicalEmbedder, ClinicalGenerator, ClinicalReranker, OllamaGenerator
from src.utils import configure_logging, log_message, set_determinism

APP_CONFIG = Config.from_env()


class QueryPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(min_length=2, max_length=APP_CONFIG.max_query_length)
    max_retries: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Total number of attempts, including the first.",
    )
    top_k_retrieve: int = Field(default=15, ge=1, le=50)
    top_k_generate: int = Field(default=3, ge=1, le=10)


def _build_generator(config, device):
    if config.generator_backend == "ollama":
        generator = OllamaGenerator(
            model_name=config.ollama_model,
            base_url=config.ollama_base_url,
            num_ctx=config.ollama_num_ctx,
            think=config.ollama_think,
            timeout=config.ollama_request_timeout,
            keep_alive=config.ollama_keep_alive,
        )
        generator.check_ready()
        return generator

    return ClinicalGenerator(config.generator_model, device, config.model_dtype)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    config = APP_CONFIG
    app.state.config = config
    app.state.ready = False
    app.state.semaphore = asyncio.Semaphore(config.max_concurrent_requests)

    set_determinism(config.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    app.state.device = str(device)

    if device.type != "cuda" and config.generator_backend == "transformers":
        log_message("api", "WARNING: CUDA is not available. A 7B generator on CPU is extremely slow.")

    started_at = time.perf_counter()
    log_message("api", f"Loading models on {device}...")

    embedder = ClinicalEmbedder(config.embedder_model, device)
    reranker = ClinicalReranker(config.reranker_model, device)
    generator = _build_generator(config, device)

    loaded_index = load_or_build_index(config, embedder)
    hybrid_index = loaded_index.index
    corpus_size = loaded_index.chunk_count

    if config.persist_traces:
        os.makedirs(config.trace_dir, exist_ok=True)

    app.state.components = {
        "embedder": embedder,
        "reranker": reranker,
        "generator": generator,
        "hybrid_index": hybrid_index,
    }
    app.state.info = {
        "device": str(device),
        "corpus_chunks": corpus_size,
        "corpus_documents": len({chunk["doc_id"] for chunk in hybrid_index.corpus_mapping}),
        "corpus_limit": config.max_corpus_docs,
        "corpus_format": config.corpus_format,
        "index_from_cache": loaded_index.from_cache,
        "embedder": config.embedder_model,
        "reranker": config.reranker_model,
        "generator": generator.model_name,
        "generator_backend": config.generator_backend,
        "startup_seconds": round(time.perf_counter() - started_at, 2),
    }
    app.state.ready = True

    log_message(
        "api",
        f"System ready in {app.state.info['startup_seconds']}s "
        f"({corpus_size} chunks on {device}). Listening on {config.host}:{config.port}.",
    )

    yield

    log_message("api", "Shutting down and clearing VRAM...")
    app.state.ready = False
    close_generator = getattr(app.state.components.get("generator"), "close", None)
    if callable(close_generator):
        close_generator()
    app.state.components.clear()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


app = FastAPI(
    title="MedSovereign-RAG",
    description="Retrieval-augmented clinical question answering with a self-correcting loop.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(APP_CONFIG.cors_origins),
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)


@app.get("/health")
async def health(request: Request):
    state = request.app.state
    ready = getattr(state, "ready", False)

    if not ready:
        raise HTTPException(status_code=503, detail="Models are still loading")

    return {"status": "ok", **state.info}


async def _stream_events(body, cancel_event, semaphore):
    """Bridge the blocking pipeline to the event loop and enforce one job at a time."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[object] = asyncio.Queue()
    sentinel = object()

    def produce():
        try:
            for item in body:
                loop.call_soon_threadsafe(queue.put_nowait, item)
        except BaseException as exc:  # noqa: BLE001 - forwarded to the consumer
            loop.call_soon_threadsafe(queue.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, sentinel)

    await semaphore.acquire()
    worker = threading.Thread(target=produce, daemon=True)
    worker.start()
    completed = False

    try:
        while True:
            item = await queue.get()

            if item is sentinel:
                completed = True
                break
            if isinstance(item, BaseException):
                raise item

            yield item
    finally:
        if not completed:
            cancel_event.set()
        await asyncio.to_thread(worker.join, 30.0)
        if worker.is_alive():
            log_message("api", "Warning: pipeline worker did not stop within 30s.")
        semaphore.release()


@app.post("/api/ask")
async def ask_agent(payload: QueryPayload, request: Request):
    state = request.app.state

    if not getattr(state, "ready", False):
        raise HTTPException(status_code=503, detail="Models are still loading")

    config = state.config
    components = state.components

    engine_config = {
        "max_retries": payload.max_retries,
        "top_k_retrieve": payload.top_k_retrieve,
        "top_k_generate": payload.top_k_generate,
        "min_rerank_score": config.min_rerank_score,
        "trace_retention": config.trace_retention,
    }

    cancel_event = threading.Event()
    body = execute_agentic_rag(
        payload.query,
        components["hybrid_index"],
        components["embedder"],
        components["reranker"],
        components["generator"],
        engine_config,
        run_dir=config.trace_dir if config.persist_traces else None,
        persist_trace=config.persist_traces,
        cancel_event=cancel_event,
    )

    return StreamingResponse(
        _stream_events(body, cancel_event, state.semaphore),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=APP_CONFIG.host,
        port=APP_CONFIG.port,
        reload=False,
    )
