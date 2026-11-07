import json

import numpy as np
import pytest
import torch

from src.data import (
    HybridIndex,
    build_index_text,
    chunk_text,
    index_cache_key,
    limit_corpus,
    parse_corpus,
)


def test_chunk_text_respects_overlap():
    words = [f"w{i}" for i in range(10)]
    chunks = chunk_text(" ".join(words), chunk_size=5, overlap=2)

    assert chunks[0].split() == words[0:5]
    assert chunks[1].split() == words[3:8]
    assert chunks[-1].split()[-1] == "w9"


def test_chunk_text_handles_short_text():
    assert chunk_text("only three words", chunk_size=300, overlap=50) == ["only three words"]


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("one two three", chunk_size=2, overlap=2)


def test_chunk_text_rejects_zero_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("one two three", chunk_size=0, overlap=0)


def test_parse_corpus_keeps_question_and_drops_short_answers(tmp_path):
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(
        json.dumps(
            [
                {"Question": "What is asthma?", "Answer": "A" * 500, "Focus": "Asthma"},
                {"Question": "Too short", "Answer": "nope"},
                {"Question": "No answer", "Answer": ""},
            ]
        ),
        encoding="utf-8",
    )

    chunks = parse_corpus(corpus_path, chunk_size=50, overlap=10)

    assert len(chunks) > 0
    assert all(chunk["doc_id"] == "doc_0" for chunk in chunks)
    assert chunks[0]["question"] == "What is asthma?"
    assert chunks[0]["focus"] == "Asthma"
    assert chunks[0]["chunk_id"].startswith("doc_0_chunk_")


def test_parse_corpus_rejects_non_list(tmp_path):
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(json.dumps({"Answer": "x"}), encoding="utf-8")

    with pytest.raises(ValueError):
        parse_corpus(corpus_path)


def test_build_index_text_prefers_question():
    assert build_index_text({"question": "What is asthma?", "text": "Inflammation."}) == (
        "What is asthma?\nInflammation."
    )
    assert build_index_text({"question": "", "text": "Inflammation."}) == "Inflammation."


def _corpus():
    return [
        {"chunk_id": "doc_0_chunk_0", "doc_id": "doc_0", "question": "asthma", "focus": "", "text": "asthma treatment"},
        {"chunk_id": "doc_1_chunk_0", "doc_id": "doc_1", "question": "diabetes", "focus": "", "text": "diabetes diet"},
        {"chunk_id": "doc_1_chunk_1", "doc_id": "doc_1", "question": "diabetes", "focus": "", "text": "diabetes medication"},
    ]


def _embedding(row, dimension=8):
    vector = np.zeros((1, dimension), dtype="float32")
    vector[0, row] = 1.0
    return torch.from_numpy(vector)


def test_retrieve_deduplicates_by_document():
    corpus = _corpus()
    embeddings = torch.cat([_embedding(0), _embedding(1), _embedding(1)], dim=0)
    index = HybridIndex(embedding_dimension=8)
    index.build_indexes(corpus, embeddings)

    results = index.retrieve("diabetes", _embedding(1), top_k=3)

    assert [result["doc_id"] for result in results].count("doc_1") == 1
    assert all("dense_score" in result for result in results)


def test_index_cache_round_trip(tmp_path):
    corpus = _corpus()
    embeddings = torch.cat([_embedding(0), _embedding(1), _embedding(1)], dim=0)
    index = HybridIndex(embedding_dimension=8)
    index.build_indexes(corpus, embeddings)
    index.save(tmp_path / "cache")

    assert HybridIndex.cache_exists(tmp_path / "cache")

    loaded = HybridIndex.load(tmp_path / "cache", embedding_dimension=8)
    original = index.retrieve("diabetes", _embedding(1), top_k=3)
    restored = loaded.retrieve("diabetes", _embedding(1), top_k=3)

    assert [item["doc_id"] for item in original] == [item["doc_id"] for item in restored]


def test_index_cache_key_changes_with_chunking(tmp_path):
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text("[]", encoding="utf-8")

    first = index_cache_key(corpus_path, 300, 50, "model-a")
    second = index_cache_key(corpus_path, 200, 50, "model-a")
    limited = index_cache_key(corpus_path, 300, 50, "model-a", max_documents=500)

    assert first != second
    assert first != limited


def test_limit_corpus_keeps_whole_documents():
    chunks = [
        {"doc_id": "doc_0", "text": "a"},
        {"doc_id": "doc_0", "text": "b"},
        {"doc_id": "doc_1", "text": "c"},
        {"doc_id": "doc_2", "text": "d"},
    ]

    assert limit_corpus(chunks, 2) == chunks[:3]
    assert limit_corpus(chunks, 0) == chunks
    assert limit_corpus(chunks, 10) == chunks
