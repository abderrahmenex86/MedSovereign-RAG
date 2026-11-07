"""Generic document ingestion.

Documents are stored as JSONL, one object per line:

    {
      "id": "PMID:12345678",
      "source": "pubmed",
      "title": "Article title",
      "text": "Full abstract",
      "sections": [{"heading": "METHODS", "text": "..."}],
      "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
      "published": "2024-03-01",
      "license": "PubMed terms",
      "pmid": "12345678",
      "meta": {"journal": "...", "publication_types": ["Randomized Controlled Trial"]}
    }

`sections` is optional; when present, each section is chunked independently so
a passage never straddles a heading.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.data import chunk_text


def _text(value):
    return " ".join(str(value or "").split()).strip()


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-")


def parse_jsonl_corpus(corpus_path, chunk_size=300, overlap=50):
    path = Path(corpus_path)

    if not path.exists():
        raise FileNotFoundError(f"Sanity Check Failed: Corpus missing at {corpus_path}")

    chunks = []
    seen_chunks = set()

    with open(path, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                document = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON ({exc.msg})") from exc

            if not isinstance(document, dict):
                continue

            source = _text(document.get("source")) or "unknown"
            doc_id = _text(document.get("id") or document.get("doc_id"))
            if not doc_id:
                doc_id = f"{source}:{line_number}"

            title = _text(document.get("title"))
            published = _text(document.get("published"))
            url = _text(document.get("url"))
            license_name = _text(document.get("license"))
            pmid = _text(document.get("pmid"))
            meta = document.get("meta") if isinstance(document.get("meta"), dict) else {}

            sections = document.get("sections")
            if not isinstance(sections, list) or not sections:
                body = document.get("text") or document.get("abstract") or ""
                sections = [{"heading": "", "text": body}]

            for section in sections:
                if not isinstance(section, dict):
                    continue

                heading = _text(section.get("heading"))
                section_text = section.get("text") or ""

                for chunk_index, chunk in enumerate(chunk_text(section_text, chunk_size, overlap)):
                    chunk_id = f"{doc_id}#{_slug(heading) or 'body'}-{chunk_index}"
                    if chunk_id in seen_chunks:
                        continue
                    seen_chunks.add(chunk_id)

                    chunks.append(
                        {
                            "chunk_id": chunk_id,
                            "doc_id": doc_id,
                            "title": title,
                            # Kept for the MedQuad-era prompt and UI.
                            "question": title,
                            "source": source,
                            "published": published,
                            "url": url,
                            "license": license_name,
                            "section": heading,
                            "pmid": pmid,
                            "meta": meta,
                            "text": chunk,
                        }
                    )

    return chunks
