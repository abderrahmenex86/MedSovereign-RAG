#!/usr/bin/env python3
"""Download PubMed abstracts into the JSONL corpus format.

PubMed ESearch returns at most 9,999 records. For a larger corpus use
`scripts/fetch_europepmc.py`.

Examples:
    python scripts/fetch_pubmed.py --limit 5000
    python scripts/fetch_pubmed.py --limit 5000 --include-pubmedqa
    python scripts/fetch_pubmed.py --reuse-manifest --resume
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pubmed import (  # noqa: E402
    DEFAULT_QUERY,
    fetch_pubmed_documents,
    make_client,
    search_pubmed,
)


def load_pubmedqa_pmids(limit=None):
    from datasets import load_dataset

    dataset = load_dataset("qiaojin/PubMedQA", "pqa_labeled", split="train")
    pmids = []

    for row in dataset:
        pmid = str(row.get("pubid") or "").strip()
        if pmid:
            pmids.append(pmid)
        if limit and len(pmids) >= limit:
            break

    return pmids


def read_manifest(path):
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def write_manifest(path, pmids):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for pmid in pmids:
            handle.write(f"{pmid}\n")


def existing_pmids(output_path):
    if not output_path.exists():
        return set()

    pmids = set()
    with open(output_path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                document = json.loads(line)
            except json.JSONDecodeError:
                continue
            if document.get("pmid"):
                pmids.add(str(document["pmid"]))
    return pmids


def dedupe(values):
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch PubMed abstracts as JSONL.")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--limit", type=int, default=9999)
    parser.add_argument("--output", type=Path, default=Path("dataset/pubmed.jsonl"))
    parser.add_argument("--pmids-file", type=Path, default=Path("dataset/pubmed_pmids.txt"))
    parser.add_argument("--sort", default="relevance", choices=["relevance", "pub_date"])
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--api-key", default=os.getenv("NCBI_API_KEY"))
    parser.add_argument("--email", default=os.getenv("NCBI_EMAIL"))
    parser.add_argument("--include-pubmedqa", action="store_true")
    parser.add_argument("--reuse-manifest", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.limit > 9999:
        raise SystemExit(
            "PubMed ESearch caps at 9,999 records. "
            "Use scripts/fetch_europepmc.py for larger corpora."
        )

    if args.output.exists() and not (args.resume or args.force):
        raise SystemExit(f"{args.output} exists; use --resume or --force")

    client = make_client()

    if args.reuse_manifest and args.pmids_file.exists():
        pmids = read_manifest(args.pmids_file)[: args.limit]
        print(f"[INFO] Reusing {len(pmids)} PMIDs from {args.pmids_file}")
    else:
        print(f"[INFO] Searching PubMed: {args.query}")
        pmids = search_pubmed(
            client,
            args.query,
            args.limit,
            api_key=args.api_key,
            email=args.email,
            sort=args.sort,
        )
        print(f"[INFO] Search returned {len(pmids)} PMIDs")

        if args.include_pubmedqa:
            pubmedqa_pmids = load_pubmedqa_pmids()
            print(f"[INFO] Adding {len(pubmedqa_pmids)} PubMedQA PMIDs")
            pmids = dedupe(pmids + pubmedqa_pmids)

        write_manifest(args.pmids_file, pmids)
        print(f"[INFO] Wrote manifest to {args.pmids_file}")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    already = existing_pmids(args.output) if args.resume else set()
    pending = [pmid for pmid in pmids if pmid not in already]
    mode = "a" if args.resume else "w"

    if not pending:
        print("[INFO] Nothing to fetch")
        return

    print(f"[INFO] Fetching {len(pending)} abstracts in batches of {args.batch_size}")

    written = 0
    with open(args.output, mode, encoding="utf-8") as handle:
        for document in fetch_pubmed_documents(
            client,
            pending,
            api_key=args.api_key,
            email=args.email,
            batch_size=args.batch_size,
        ):
            handle.write(json.dumps(document, ensure_ascii=False) + "\n")
            written += 1

            if written % 500 == 0:
                handle.flush()
                print(f"[INFO] {written}/{len(pending)}")

        handle.flush()

    print(f"[SUCCESS] Wrote {written} documents to {args.output}")


if __name__ == "__main__":
    main()
