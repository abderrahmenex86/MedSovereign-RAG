import json
import os

import faiss
import numpy as np
from rank_bm25 import BM25Okapi


def chunk_text(text, chunk_size, overlap):
    words = text.split()
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
    return chunks


def parse_corpus(corpus_path, chunk_size=300, overlap=50):
    if not os.path.exists(corpus_path):
        raise FileNotFoundError(f"Sanity Check Failed: Corpus missing at {corpus_path}")

    with open(corpus_path, "r", encoding="utf-8") as file_handle:
        raw_documents = json.load(file_handle)

    chunked_corpus = []

    for idx, doc in enumerate(raw_documents):
        answer_text = doc.get("Answer") or doc.get("answer") or doc.get("content") or doc.get("text") or ""

        if not answer_text or len(answer_text) < 20:
            continue

        chunks = chunk_text(answer_text, chunk_size, overlap)

        for chunk_idx, chunk in enumerate(chunks):
            chunked_corpus.append({"chunk_id": f"doc_{idx}_chunk_{chunk_idx}", "doc_id": f"doc_{idx}", "text": chunk})

    return chunked_corpus


class HybridIndex:
    def __init__(self, embedding_dimension=768):
        self.dense_index = faiss.IndexFlatIP(embedding_dimension)
        self.sparse_index = None
        self.corpus_mapping = []

    def build_indexes(self, chunked_corpus, embeddings_tensor):
        if len(chunked_corpus) == 0:
            raise ValueError("Sanity Check Failed: Cannot build index on an empty corpus.")

        self.corpus_mapping = chunked_corpus

        embeddings_np = embeddings_tensor.cpu().numpy().astype("float32")
        faiss.normalize_L2(embeddings_np)
        self.dense_index.add(embeddings_np)

        tokenized_corpus = [doc["text"].lower().split() for doc in self.corpus_mapping]
        self.sparse_index = BM25Okapi(tokenized_corpus)

    def retrieve(self, query_text, query_embedding, top_k=15):
        query_np = query_embedding.cpu().numpy().astype("float32")
        faiss.normalize_L2(query_np)

        _, dense_indices = self.dense_index.search(query_np, top_k)

        tokenized_query = query_text.lower().split()
        sparse_scores = self.sparse_index.get_scores(tokenized_query)
        sparse_indices = np.argsort(sparse_scores)[::-1][:top_k]

        retrieved_candidates = {}

        for idx in dense_indices[0]:
            if idx != -1:
                retrieved_candidates[idx] = self.corpus_mapping[idx]

        for idx in sparse_indices:
            if idx not in retrieved_candidates:
                retrieved_candidates[idx] = self.corpus_mapping[idx]

        return list(retrieved_candidates.values())
