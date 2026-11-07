"""Corpus loading and index cache management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.corpus import parse_jsonl_corpus
from src.data import (
    HybridIndex,
    build_index_text,
    index_cache_key,
    limit_corpus,
    parse_corpus,
)
from src.utils import log_message


@dataclass
class LoadedIndex:
    index: HybridIndex
    chunk_count: int
    cache_dir: Path
    from_cache: bool


def load_corpus(config):
    if config.corpus_format == "jsonl":
        return parse_jsonl_corpus(config.corpus_path, config.chunk_size, config.chunk_overlap)
    return parse_corpus(config.corpus_path, config.chunk_size, config.chunk_overlap)


def load_or_build_index(config, embedder):
    if not config.corpus_path.exists():
        raise FileNotFoundError(
            f"Corpus missing at {config.corpus_path}. "
            "Run `python setup_dataset.py` or `python scripts/fetch_pubmed.py` first."
        )

    corpus = limit_corpus(load_corpus(config), config.max_corpus_docs)

    if not corpus:
        raise ValueError(
            "Sanity Check Failed: Corpus parsed to 0 chunks. Check the dataset path and structure."
        )

    cache_key = index_cache_key(
        config.corpus_path,
        config.chunk_size,
        config.chunk_overlap,
        config.embedder_model,
        config.max_corpus_docs,
        config.corpus_format,
    )
    cache_dir = config.cache_dir / cache_key

    if HybridIndex.cache_exists(cache_dir):
        try:
            log_message("api", f"Loading cached indices from {cache_dir}")
            index = HybridIndex.load(cache_dir, embedder.hidden_size)
            return LoadedIndex(index, len(corpus), cache_dir, from_cache=True)
        except Exception as exc:  # noqa: BLE001 - a corrupt cache should trigger a rebuild
            log_message("api", f"Index cache unusable ({exc}); rebuilding.")

    log_message("api", "Embedding corpus and building dense + sparse indices...")
    index_texts = [build_index_text(chunk) for chunk in corpus]
    corpus_embeddings = embedder.encode(index_texts)

    index = HybridIndex(embedding_dimension=corpus_embeddings.shape[1])
    index.build_indexes(corpus, corpus_embeddings, index_texts=index_texts)

    try:
        index.save(cache_dir)
        log_message("api", f"Cached indices at {cache_dir}")
    except Exception as exc:  # noqa: BLE001 - caching is best effort
        log_message("api", f"Could not write index cache: {exc}")

    return LoadedIndex(index, len(corpus), cache_dir, from_cache=False)
