#!/usr/bin/env python3
"""Append topic-balanced records to an existing Europe PMC corpus.

The broad evidence query is dominated by recent oncology. This adds a fixed
number of records for the conditions used in the demo and the seeded
conversations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_europepmc import iter_query, read_existing  # noqa: E402

TOPICS = [
    "acute bronchitis",
    "type 2 diabetes",
    "low back pain",
    "anterior cruciate ligament reconstruction",
    "community-acquired pneumonia",
    "hypertension",
    "migraine",
    "atrial fibrillation",
    "chronic obstructive pulmonary disease",
    "sepsis",
    "acute kidney injury",
    "antibiotic prophylaxis",
    "iron deficiency anemia",
    "gout",
]

EVIDENCE_FILTER = (
    '(PUB_TYPE:"Guideline" OR PUB_TYPE:"Systematic Review" OR '
    'PUB_TYPE:"Meta-Analysis" OR PUB_TYPE:"Randomized Controlled Trial") '
    "AND (PUB_YEAR:[2015 TO 2026]) AND (HAS_ABSTRACT:Y)"
)


def main():
    parser = argparse.ArgumentParser(description="Add demo-topic abstracts.")
    parser.add_argument("--output", type=Path, default=Path("dataset/pubmed.jsonl"))
    parser.add_argument("--pmids-file", type=Path, default=Path("dataset/pubmed_pmids.txt"))
    parser.add_argument("--per-topic", type=int, default=2000)
    parser.add_argument("--topics", default=",".join(TOPICS))
    args = parser.parse_args()

    existing = read_existing(args.output)
    client = httpx.Client(
        timeout=httpx.Timeout(connect=20.0, read=120.0, write=30.0, pool=20.0),
        transport=httpx.HTTPTransport(retries=3),
        headers={"User-Agent": "medsovereign-rag/1.0"},
    )

    written = 0
    with open(args.output, "a", encoding="utf-8") as handle:
        for topic in [item.strip() for item in args.topics.split(",") if item.strip()]:
            query = f'("{topic}") AND {EVIDENCE_FILTER}'
            before = written

            for document in iter_query(
                client, query, args.per_topic, 1000, 0.25, existing
            ):
                handle.write(json.dumps(document, ensure_ascii=False) + "\n")
                written += 1

            handle.flush()
            print(f"[INFO] {topic}: {written - before} added")

    with open(args.pmids_file, "w", encoding="utf-8") as handle:
        for pmid in sorted(existing):
            handle.write(f"{pmid}\n")

    client.close()
    print(f"[SUCCESS] Added {written} topic documents to {args.output}")


if __name__ == "__main__":
    main()
