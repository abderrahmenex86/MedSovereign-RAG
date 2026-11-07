#!/usr/bin/env python3
"""Evaluate retrieval on PubMedQA (query -> labeled PMID).

The corpus must contain the PubMedQA PMIDs. Fetch them with:
    python scripts/fetch_pubmed.py --limit 100000 --include-pubmedqa

Then:
    CORPUS_FORMAT=jsonl CORPUS_PATH=dataset/pubmed.jsonl \
        python scripts/evaluate_retrieval.py --limit 200 --k 10
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
from datasets import load_dataset  # noqa: E402

from src.config import Config  # noqa: E402
from src.evaluation import summarize_retrieval  # noqa: E402
from src.index import load_or_build_index  # noqa: E402
from src.models import ClinicalEmbedder  # noqa: E402
from src.utils import configure_logging  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Retrieval evaluation on PubMedQA.")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--split", default="pqa_labeled")
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--format", choices=["medquad", "jsonl"])
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/eval/pubmedqa.json"))
    args = parser.parse_args()

    configure_logging()
    config = Config.from_env()
    overrides = {}
    if args.corpus:
        overrides["corpus_path"] = args.corpus
    if args.format:
        overrides["corpus_format"] = args.format
    if args.cache_dir:
        overrides["cache_dir"] = args.cache_dir
    config = replace(config, **overrides)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    embedder = ClinicalEmbedder(config.embedder_model, device)
    loaded = load_or_build_index(config, embedder)

    corpus_ids = {chunk["doc_id"] for chunk in loaded.index.corpus_mapping}
    dataset = load_dataset("qiaojin/PubMedQA", args.split, split="train")

    rows = []
    missing_targets = 0

    for row in dataset:
        target = f"PMID:{row.get('pubid')}"
        if target not in corpus_ids:
            missing_targets += 1
            continue
        rows.append((row, target))
        if len(rows) >= args.limit:
            break

    if not rows:
        raise SystemExit(
            "No PubMedQA targets found in the corpus. "
            "Re-run the fetcher with --include-pubmedqa."
        )

    questions = [row["question"] for row, _ in rows]
    embeddings = embedder.encode(questions)

    ranked_lists = []
    targets = []
    failures = []

    for (row, target), embedding in zip(rows, embeddings, strict=True):
        results = loaded.index.retrieve(row["question"], embedding.unsqueeze(0), top_k=args.k)
        ranked = [result["doc_id"] for result in results]
        ranked_lists.append(ranked)
        targets.append(target)

        if target not in ranked:
            failures.append(
                {
                    "question": row["question"],
                    "target": target,
                    "top_k": ranked,
                }
            )

    ks = tuple(k for k in (1, 5, 10) if k <= args.k)
    metrics = summarize_retrieval(ranked_lists, targets, ks=ks)
    metrics["missing_targets"] = missing_targets
    metrics["evaluated"] = len(targets)
    metrics["corpus_documents"] = len(corpus_ids)
    metrics["k"] = args.k
    metrics["corpus"] = str(config.corpus_path)
    metrics["corpus_format"] = config.corpus_format

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump({"metrics": metrics, "failures": failures[:20]}, handle, indent=2)

    print(json.dumps(metrics, indent=2))
    print(f"[INFO] Wrote {args.output}")


if __name__ == "__main__":
    main()
