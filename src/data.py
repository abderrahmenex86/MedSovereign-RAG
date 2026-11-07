import hashlib
import json
import os
import pickle
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

CACHE_VERSION = 4


def chunk_text(text, chunk_size=300, overlap=50):
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            f"overlap must be in [0, chunk_size), got overlap={overlap}, chunk_size={chunk_size}"
        )

    words = text.split()
    if not words:
        return []

    chunks = []
    step = chunk_size - overlap
    for index in range(0, len(words), step):
        chunks.append(" ".join(words[index : index + chunk_size]))
        if index + chunk_size >= len(words):
            break
    return chunks


def parse_corpus(corpus_path, chunk_size=300, overlap=50):
    if not os.path.exists(corpus_path):
        raise FileNotFoundError(f"Sanity Check Failed: Corpus missing at {corpus_path}")

    with open(corpus_path, encoding="utf-8") as file_handle:
        raw_documents = json.load(file_handle)

    if not isinstance(raw_documents, list):
        raise ValueError(f"Corpus at {corpus_path} must be a JSON list, got {type(raw_documents).__name__}")

    chunked_corpus = []

    for index, document in enumerate(raw_documents):
        if not isinstance(document, dict):
            continue

        answer_text = (
            document.get("Answer")
            or document.get("answer")
            or document.get("content")
            or document.get("text")
            or ""
        )
        question_text = document.get("Question") or document.get("question") or ""
        focus_text = document.get("Focus") or document.get("focus") or ""

        if not answer_text or len(answer_text) < 20:
            continue

        chunks = chunk_text(answer_text, chunk_size, overlap)

        for chunk_index, chunk in enumerate(chunks):
            chunked_corpus.append(
                {
                    "chunk_id": f"doc_{index}_chunk_{chunk_index}",
                    "doc_id": f"doc_{index}",
                    "title": question_text.strip(),
                    "question": question_text.strip(),
                    "focus": focus_text.strip(),
                    "source": "medquad",
                    "published": "",
                    "url": "",
                    "license": "unknown",
                    "section": "",
                    "pmid": "",
                    "meta": {},
                    "text": chunk,
                }
            )

    return chunked_corpus


def build_index_text(chunk):
    """Text used for retrieval: title and section add topical signal."""
    title = (chunk.get("title") or chunk.get("question") or "").strip()
    section = (chunk.get("section") or "").strip()
    text = chunk.get("text") or ""

    prefix = "\n".join(part for part in (title, section) if part)
    if not prefix:
        return text
    return f"{prefix}\n{text}"


def _corpus_digest(corpus_path):
    """Hash the file contents so a cache built on another host still matches."""
    digest = hashlib.sha256()
    with open(corpus_path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def index_cache_key(
    corpus_path, chunk_size, overlap, embedder_model, max_documents=0, corpus_format="medquad"
):
    corpus_hash = _corpus_digest(corpus_path)
    payload = (
        f"v{CACHE_VERSION}:{corpus_hash}:{corpus_format}:{chunk_size}:"
        f"{overlap}:{embedder_model}:{max_documents}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def limit_corpus(chunks, max_documents):
    """Keep the first `max_documents` source documents (0 keeps everything).

    parse_corpus emits chunks grouped by document, so stopping at the first
    chunk of the next document is safe.
    """
    if max_documents <= 0:
        return chunks

    selected = []
    seen_documents: set[str] = set()

    for chunk in chunks:
        document_id = chunk["doc_id"]
        if document_id not in seen_documents:
            if len(seen_documents) >= max_documents:
                break
            seen_documents.add(document_id)
        selected.append(chunk)

    return selected


class HybridIndex:
    def __init__(self, embedding_dimension=768):
        self.embedding_dimension = embedding_dimension
        self.dense_index: faiss.Index = faiss.IndexFlatIP(embedding_dimension)
        self.sparse_index = None
        self.corpus_mapping = []

    def build_indexes(self, chunked_corpus, embeddings_tensor, index_texts=None):
        if len(chunked_corpus) == 0:
            raise ValueError("Sanity Check Failed: Cannot build index on an empty corpus.")

        self.corpus_mapping = chunked_corpus

        embeddings_np = embeddings_tensor.cpu().numpy().astype("float32")
        faiss.normalize_L2(embeddings_np)
        self.dense_index.add(embeddings_np)

        texts = index_texts or [build_index_text(chunk) for chunk in chunked_corpus]
        tokenized_corpus = [text.lower().split() for text in texts]
        self.sparse_index = BM25Okapi(tokenized_corpus)

    def retrieve(self, query_text, query_embedding, top_k=15):
        """Return candidate chunks, deduplicated by source document.

        Duplicates matter: leaving three chunks of the same article in the
        prompt wastes the generation budget and hides other evidence.
        """
        top_k = max(1, int(top_k))
        if self.sparse_index is None:
            raise RuntimeError("Sanity Check Failed: Sparse index has not been built.")

        query_np = query_embedding.cpu().numpy().astype("float32")
        faiss.normalize_L2(query_np)

        dense_scores, dense_indices = self.dense_index.search(query_np, top_k)

        tokenized_query = query_text.lower().split()
        sparse_scores = self.sparse_index.get_scores(tokenized_query)
        candidate_count = min(top_k, len(sparse_scores))
        if candidate_count:
            partitioned = np.argpartition(sparse_scores, -candidate_count)[-candidate_count:]
            sparse_indices = partitioned[np.argsort(sparse_scores[partitioned])[::-1]]
        else:
            sparse_indices = np.array([], dtype=np.int64)

        candidates = {}

        def add_candidate(chunk_index, dense_score=None, sparse_score=None):
            chunk = self.corpus_mapping[int(chunk_index)]
            document_id = chunk["doc_id"]
            if document_id in candidates:
                return

            candidates[document_id] = {
                **chunk,
                "dense_score": float(dense_score) if dense_score is not None else None,
                "sparse_score": float(sparse_score) if sparse_score is not None else None,
            }

        for rank, chunk_index in enumerate(dense_indices[0]):
            if chunk_index != -1:
                add_candidate(chunk_index, dense_score=dense_scores[0][rank])

        for chunk_index in sparse_indices:
            add_candidate(chunk_index, sparse_score=sparse_scores[chunk_index])

        return list(candidates.values())

    def save(self, cache_dir):
        directory = Path(cache_dir)
        directory.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.dense_index, str(directory / "dense.faiss"))
        with open(directory / "sparse.pkl", "wb") as handle:
            pickle.dump(self.sparse_index, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with open(directory / "mapping.json", "w", encoding="utf-8") as handle:
            json.dump(self.corpus_mapping, handle, ensure_ascii=False)
        with open(directory / "meta.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "version": CACHE_VERSION,
                    "dimension": self.embedding_dimension,
                    "size": len(self.corpus_mapping),
                },
                handle,
            )

    @staticmethod
    def cache_exists(cache_dir):
        directory = Path(cache_dir)
        return all(
            (directory / name).exists()
            for name in ("dense.faiss", "sparse.pkl", "mapping.json", "meta.json")
        )

    @classmethod
    def load(cls, cache_dir, embedding_dimension=None):
        directory = Path(cache_dir)
        with open(directory / "meta.json", encoding="utf-8") as handle:
            meta = json.load(handle)

        if meta.get("version") != CACHE_VERSION:
            raise ValueError(
                f"Index cache version mismatch: expected {CACHE_VERSION}, got {meta.get('version')}"
            )

        dimension = int(meta["dimension"])
        if embedding_dimension is not None and dimension != embedding_dimension:
            raise ValueError(
                f"Index dimension {dimension} does not match embedder dimension {embedding_dimension}"
            )

        index = cls(embedding_dimension=dimension)
        index.dense_index = faiss.read_index(str(directory / "dense.faiss"))
        with open(directory / "sparse.pkl", "rb") as handle:
            index.sparse_index = pickle.load(handle)
        with open(directory / "mapping.json", encoding="utf-8") as handle:
            index.corpus_mapping = json.load(handle)

        if index.dense_index.ntotal != len(index.corpus_mapping):
            raise ValueError(
                "Index cache is inconsistent: dense vectors and corpus mapping differ in size"
            )

        return index
