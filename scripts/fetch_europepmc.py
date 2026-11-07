#!/usr/bin/env python3
"""Fetch a large biomedical abstract corpus from Europe PMC.

PubMed ESearch caps retrieval at 9,999 records. Europe PMC exposes the same
MEDLINE records with cursor-based paging, so this script can build a 100k corpus.

Example:
    python scripts/fetch_europepmc.py --limit 100000 --include-pubmedqa
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
DEFAULT_QUERY = (
    '(PUB_TYPE:"Guideline" OR PUB_TYPE:"Systematic Review" OR '
    'PUB_TYPE:"Meta-Analysis" OR PUB_TYPE:"Randomized Controlled Trial") '
    "AND (PUB_YEAR:[2015 TO 2026]) AND (HAS_ABSTRACT:Y)"
)


def clean_html(value):
    text = html.unescape(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(?:p|div|h[1-6]|li)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def parse_sections(abstract_html):
    raw = html.unescape(abstract_html or "")
    parts = re.split(r"<h[34][^>]*>(.*?)</h[34]>", raw, flags=re.IGNORECASE | re.DOTALL)

    if len(parts) == 1:
        text = clean_html(raw)
        return [{"heading": "", "text": text}] if text else []

    sections = []
    intro = clean_html(parts[0])
    if intro:
        sections.append({"heading": "", "text": intro})

    for index in range(1, len(parts), 2):
        heading = clean_html(parts[index])
        body = clean_html(parts[index + 1] if index + 1 < len(parts) else "")
        if body:
            sections.append({"heading": heading, "text": body})

    return sections


def document_from_result(item):
    pmid = str(item.get("pmid") or "").strip()
    if not pmid:
        return None

    title = clean_html(item.get("title")) or "Untitled"
    sections = parse_sections(item.get("abstractText"))
    if not sections:
        return None

    journal = (
        item.get("journalTitle")
        or (item.get("journalInfo") or {}).get("journal", {}).get("title")
        or ""
    )
    publication_types = (item.get("pubTypeList") or {}).get("pubType") or []
    text = "\n\n".join(section["text"] for section in sections)

    return {
        "id": f"PMID:{pmid}",
        "source": "pubmed",
        "title": title,
        "text": text,
        "sections": sections,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "published": str(item.get("pubYear") or ""),
        "license": "Europe PMC / PubMed; publisher terms apply",
        "pmid": pmid,
        "meta": {
            "journal": journal,
            "publication_types": publication_types,
            "doi": item.get("doi") or "",
            "authors": item.get("authorString") or "",
        },
    }


def fetch_page(client, query, cursor, page_size, pause):
    params = {
        "query": query,
        "format": "json",
        "pageSize": page_size,
        "resultType": "core",
        "cursorMark": cursor or "*",
    }

    for attempt in range(5):
        response = client.get(EPMC_URL, params=params)
        if response.status_code == 429 or 500 <= response.status_code < 600:
            time.sleep(2**attempt)
            continue
        response.raise_for_status()
        payload = response.json()
        time.sleep(pause)
        return payload

    raise RuntimeError("Europe PMC request failed after retries")


def iter_query(client, query, limit, page_size, pause, skip_ids):
    cursor = "*"
    fetched = 0
    seen_cursors = set()

    while fetched < limit:
        payload = fetch_page(client, query, cursor, page_size, pause)
        results = (payload.get("resultList") or {}).get("result") or []

        if not results:
            break

        for item in results:
            document = document_from_result(item)
            if document is None or document["pmid"] in skip_ids:
                continue

            skip_ids.add(document["pmid"])
            fetched += 1
            yield document

            if fetched >= limit:
                break

        next_cursor = payload.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor or next_cursor in seen_cursors:
            break

        seen_cursors.add(cursor)
        cursor = next_cursor


def load_pubmedqa_pmids():
    from datasets import load_dataset

    dataset = load_dataset("qiaojin/PubMedQA", "pqa_labeled", split="train")
    return [str(row["pubid"]) for row in dataset if row.get("pubid")]


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch Europe PMC abstracts as JSONL.")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--limit", type=int, default=100_000)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--pause", type=float, default=0.25)
    parser.add_argument("--output", type=Path, default=Path("dataset/pubmed.jsonl"))
    parser.add_argument("--pmids-file", type=Path, default=Path("dataset/pubmed_pmids.txt"))
    parser.add_argument("--include-pubmedqa", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def read_existing(output_path):
    if not output_path.exists():
        return set()

    pmids = set()
    with open(output_path, encoding="utf-8") as handle:
        for line in handle:
            try:
                document = json.loads(line)
            except json.JSONDecodeError:
                continue
            if document.get("pmid"):
                pmids.add(str(document["pmid"]))
    return pmids


def main():
    args = parse_args()

    if args.output.exists() and not (args.resume or args.force):
        raise SystemExit(f"{args.output} exists; use --resume or --force")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    existing = read_existing(args.output) if args.resume else set()
    mode = "a" if args.resume else "w"

    client = httpx.Client(
        timeout=httpx.Timeout(connect=20.0, read=120.0, write=30.0, pool=20.0),
        transport=httpx.HTTPTransport(retries=3),
        headers={"User-Agent": "medsovereign-rag/1.0"},
    )

    written = 0
    with open(args.output, mode, encoding="utf-8") as handle:
        print(f"[INFO] Fetching up to {args.limit} records from Europe PMC")
        for document in iter_query(
            client, args.query, args.limit, args.page_size, args.pause, existing
        ):
            handle.write(json.dumps(document, ensure_ascii=False) + "\n")
            written += 1

            if written % 1000 == 0:
                handle.flush()
                print(f"[INFO] {written}/{args.limit}")

        if args.include_pubmedqa:
            pmids = load_pubmedqa_pmids()
            print(f"[INFO] Adding {len(pmids)} PubMedQA PMIDs")

            for start in range(0, len(pmids), 100):
                chunk = [pmid for pmid in pmids[start : start + 100] if pmid not in existing]
                if not chunk:
                    continue

                query = " OR ".join(f"EXT_ID:{pmid}" for pmid in chunk)
                for document in iter_query(client, query, len(chunk), 100, args.pause, existing):
                    handle.write(json.dumps(document, ensure_ascii=False) + "\n")
                    written += 1

        handle.flush()

    pmids = sorted(existing)
    with open(args.pmids_file, "w", encoding="utf-8") as handle:
        for pmid in pmids:
            handle.write(f"{pmid}\n")

    client.close()
    print(f"[SUCCESS] Wrote {written} documents to {args.output}")


if __name__ == "__main__":
    main()
