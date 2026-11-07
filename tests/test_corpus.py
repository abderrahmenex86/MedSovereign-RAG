import json

import pytest

from src.corpus import parse_jsonl_corpus
from src.data import build_index_text, index_cache_key
from src.engine import format_context


def _write_jsonl(path, documents):
    path.write_text(
        "".join(json.dumps(document) + "\n" for document in documents),
        encoding="utf-8",
    )


def test_parse_jsonl_corpus_preserves_metadata_and_sections(tmp_path):
    corpus = tmp_path / "pubmed.jsonl"
    _write_jsonl(
        corpus,
        [
            {
                "id": "PMID:123",
                "source": "pubmed",
                "title": "Acute bronchitis in adults",
                "text": "Background text.\n\nResults text.",
                "sections": [
                    {"heading": "BACKGROUND", "text": "Background text."},
                    {"heading": "RESULTS", "text": "Results text."},
                ],
                "url": "https://pubmed.ncbi.nlm.nih.gov/123/",
                "published": "2024-01-01",
                "license": "PubMed terms",
                "pmid": "123",
                "meta": {"journal": "Example Journal"},
            }
        ],
    )

    chunks = parse_jsonl_corpus(corpus, chunk_size=50, overlap=10)

    assert len(chunks) == 2
    assert chunks[0]["doc_id"] == "PMID:123"
    assert chunks[0]["title"] == "Acute bronchitis in adults"
    assert chunks[0]["source"] == "pubmed"
    assert chunks[0]["published"] == "2024-01-01"
    assert chunks[0]["pmid"] == "123"
    assert chunks[0]["section"] == "BACKGROUND"
    assert chunks[0]["meta"]["journal"] == "Example Journal"
    assert chunks[0]["chunk_id"] != chunks[1]["chunk_id"]


def test_parse_jsonl_corpus_falls_back_to_text(tmp_path):
    corpus = tmp_path / "docs.jsonl"
    _write_jsonl(corpus, [{"id": "d1", "title": "Title", "text": "A" * 200}])

    chunks = parse_jsonl_corpus(corpus, chunk_size=100, overlap=10)

    assert len(chunks) > 0
    assert chunks[0]["source"] == "unknown"
    assert chunks[0]["section"] == ""


def test_parse_jsonl_corpus_reports_bad_json(tmp_path):
    corpus = tmp_path / "bad.jsonl"
    corpus.write_text("{not json}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid JSON"):
        parse_jsonl_corpus(corpus)


def test_build_index_text_uses_title_and_section():
    text = build_index_text({"title": "Asthma", "section": "RESULTS", "text": "Inflammation."})

    assert "Asthma" in text
    assert "RESULTS" in text
    assert "Inflammation." in text


def test_format_context_includes_citation_metadata():
    context = format_context(
        [
            {
                "doc_id": "PMID:123",
                "title": "Acute bronchitis",
                "source": "pubmed",
                "published": "2024-01-01",
                "section": "RESULTS",
                "text": "Symptoms improve within two weeks.",
            }
        ]
    )

    assert "[PMID:123]" in context
    assert "pubmed" in context
    assert "Acute bronchitis" in context
    assert "RESULTS" in context


def test_index_cache_key_includes_corpus_format(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text('{"text": "x"}\n', encoding="utf-8")

    first = index_cache_key(corpus, 300, 50, "model", corpus_format="jsonl")
    second = index_cache_key(corpus, 300, 50, "model", corpus_format="medquad")

    assert first != second
