import os
from contextlib import asynccontextmanager

import torch
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.data import HybridIndex, parse_corpus
from src.engine import execute_agentic_rag
from src.models import ClinicalEmbedder, ClinicalGenerator, ClinicalReranker
from src.utils import log_message, set_determinism


class QueryPayload(BaseModel):
    query: str
    max_retries: int = 3
    top_k_retrieve: int = 15
    top_k_generate: int = 3


global_components = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_determinism(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = os.path.join("artifacts", "production_api")
    os.makedirs(run_dir, exist_ok=True)

    log_message("api", "Loading Models into VRAM...")
    embedder = ClinicalEmbedder("pritamdeka/S-PubMedBert-MS-MARCO", device)
    reranker = ClinicalReranker("cross-encoder/ms-marco-MiniLM-L-6-v2", device)
    generator = ClinicalGenerator("HuggingFaceH4/zephyr-7b-beta", device)

    log_message("api", "Parsing MedQuad corpus and building dual indices...")
    chunked_corpus = parse_corpus("dataset/medquad_corpus.json", 300, 50)

    if not chunked_corpus:
        raise ValueError("Sanity Check Failed: Corpus parsed to 0 chunks. Check dataset path and structure.")

    texts = [chunk["text"] for chunk in chunked_corpus]
    corpus_embeddings = embedder.encode(texts)

    hybrid_index = HybridIndex(embedding_dimension=corpus_embeddings.shape[1])
    hybrid_index.build_indexes(chunked_corpus, corpus_embeddings)

    global_components["embedder"] = embedder
    global_components["reranker"] = reranker
    global_components["generator"] = generator
    global_components["hybrid_index"] = hybrid_index
    global_components["run_dir"] = run_dir

    log_message("api", "System Ready. Listening for requests.")

    yield

    log_message("api", "Shutting down and clearing VRAM...")
    global_components.clear()
    torch.cuda.empty_cache()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/ask")
async def ask_agent(payload: QueryPayload):
    config = {
        "max_retries": payload.max_retries,
        "top_k_retrieve": payload.top_k_retrieve,
        "top_k_generate": payload.top_k_generate,
    }

    return StreamingResponse(
        execute_agentic_rag(
            payload.query,
            global_components["hybrid_index"],
            global_components["embedder"],
            global_components["reranker"],
            global_components["generator"],
            config,
            global_components["run_dir"],
        ),
        media_type="application/x-ndjson",
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
