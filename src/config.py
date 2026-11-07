"""Runtime configuration.

Every value can be overridden with an environment variable so the app can be
moved between a laptop, a GPU box, and a container without editing code. The
defaults target a local, single-user deployment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_EMBEDDER = "pritamdeka/S-PubMedBert-MS-MARCO"
DEFAULT_RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_GENERATOR = "HuggingFaceH4/zephyr-7b-beta"
DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def _env_int(name: str, default: int, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc

    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


def _env_float(name: str, default: float | None) -> float | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default

    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default

    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean, got {raw!r}")


def _env_optional_bool(name: str, default: bool | None = None) -> bool | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return _env_bool(name, default=False)


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Config:
    embedder_model: str
    reranker_model: str
    generator_model: str
    corpus_path: Path
    corpus_format: str
    cache_dir: Path
    trace_dir: Path
    chunk_size: int
    chunk_overlap: int
    max_corpus_docs: int
    max_concurrent_requests: int
    persist_traces: bool
    trace_retention: int
    min_rerank_score: float | None
    cors_origins: tuple[str, ...]
    host: str
    port: int
    seed: int
    model_dtype: str
    max_query_length: int
    generator_backend: str
    ollama_base_url: str
    ollama_model: str
    ollama_num_ctx: int
    ollama_think: bool | None
    ollama_request_timeout: int
    ollama_keep_alive: str

    @classmethod
    def from_env(cls) -> Config:
        chunk_size = _env_int("CHUNK_SIZE", 300, minimum=1)
        chunk_overlap = _env_int("CHUNK_OVERLAP", 50, minimum=0)

        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"CHUNK_OVERLAP ({chunk_overlap}) must be smaller than CHUNK_SIZE ({chunk_size})"
            )

        generator_backend = _env_str("GENERATOR_BACKEND", "transformers").lower()
        if generator_backend not in {"transformers", "ollama"}:
            raise ValueError(
                f"GENERATOR_BACKEND must be 'transformers' or 'ollama', got {generator_backend!r}"
            )

        corpus_format = _env_str("CORPUS_FORMAT", "medquad").lower()
        if corpus_format not in {"medquad", "jsonl"}:
            raise ValueError(
                f"CORPUS_FORMAT must be 'medquad' or 'jsonl', got {corpus_format!r}"
            )

        return cls(
            embedder_model=_env_str("EMBEDDER_MODEL", DEFAULT_EMBEDDER),
            reranker_model=_env_str("RERANKER_MODEL", DEFAULT_RERANKER),
            generator_model=_env_str("GENERATOR_MODEL", DEFAULT_GENERATOR),
            corpus_path=Path(_env_str("CORPUS_PATH", "dataset/medquad_corpus.json")),
            corpus_format=corpus_format,
            cache_dir=Path(_env_str("INDEX_CACHE_DIR", "artifacts/index_cache")),
            trace_dir=Path(_env_str("TRACE_DIR", "artifacts/production_api")),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            max_corpus_docs=_env_int("MAX_CORPUS_DOCS", 0, minimum=0),
            max_concurrent_requests=_env_int("MAX_CONCURRENT_REQUESTS", 1, minimum=1),
            persist_traces=_env_bool("PERSIST_TRACES", True),
            trace_retention=_env_int("TRACE_RETENTION", 200, minimum=1),
            min_rerank_score=_env_float("MIN_RERANK_SCORE", None),
            cors_origins=_env_list("CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
            host=_env_str("HOST", "127.0.0.1"),
            port=_env_int("PORT", 8000, minimum=1),
            seed=_env_int("SEED", 42),
            model_dtype=_env_str("MODEL_DTYPE", "auto").lower(),
            max_query_length=_env_int("MAX_QUERY_LENGTH", 2000, minimum=1),
            generator_backend=generator_backend,
            ollama_base_url=_env_str("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            ollama_model=_env_str("OLLAMA_MODEL", "medgemma:4b"),
            ollama_num_ctx=_env_int("OLLAMA_NUM_CTX", 8192, minimum=512),
            ollama_think=_env_optional_bool("OLLAMA_THINK", None),
            ollama_request_timeout=_env_int("OLLAMA_REQUEST_TIMEOUT", 600, minimum=10),
            ollama_keep_alive=_env_str("OLLAMA_KEEP_ALIVE", "10m"),
        )
