#!/usr/bin/env python3
"""Build (or load) the index cache without starting the API.

Examples:
    CORPUS_FORMAT=jsonl CORPUS_PATH=dataset/pubmed.jsonl python scripts/build_index.py
    python scripts/build_index.py --corpus dataset/pubmed.jsonl --format jsonl --limit-docs 10000
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402

from src.config import Config  # noqa: E402
from src.index import load_or_build_index  # noqa: E402
from src.models import ClinicalEmbedder  # noqa: E402
from src.utils import configure_logging  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Build the hybrid index cache.")
    parser.add_argument("--corpus", type=Path, help="Corpus path (defaults to CORPUS_PATH)")
    parser.add_argument("--format", choices=["medquad", "jsonl"], help="Corpus format")
    parser.add_argument("--limit-docs", type=int, help="Index only the first N documents")
    parser.add_argument("--cache-dir", type=Path, help="Index cache directory")
    args = parser.parse_args()

    configure_logging()
    config = Config.from_env()
    overrides = {}

    if args.corpus:
        overrides["corpus_path"] = args.corpus
    if args.format:
        overrides["corpus_format"] = args.format
    if args.limit_docs is not None:
        overrides["max_corpus_docs"] = args.limit_docs
    if args.cache_dir:
        overrides["cache_dir"] = args.cache_dir

    config = replace(config, **overrides)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    embedder = ClinicalEmbedder(config.embedder_model, device)
    loaded = load_or_build_index(config, embedder)

    print(
        json.dumps(
            {
                "corpus": str(config.corpus_path),
                "format": config.corpus_format,
                "chunks": loaded.chunk_count,
                "documents": len({chunk["doc_id"] for chunk in loaded.index.corpus_mapping}),
                "cache_dir": str(loaded.cache_dir),
                "from_cache": loaded.from_cache,
                "device": str(device),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
