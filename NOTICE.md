# Third-party notices

The MIT license in `LICENSE` covers this repository's source code. The models
and data downloaded at runtime carry their own licenses:

| Component | Source | License |
| --- | --- | --- |
| `pritamdeka/S-PubMedBert-MS-MARCO` | Hugging Face | CC BY-NC 2.0 (non-commercial) |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | Hugging Face | Apache-2.0 |
| `HuggingFaceH4/zephyr-7b-beta` | Hugging Face | MIT |
| MedGemma (`medgemma:4b`, optional Ollama generator) | Ollama / Google | Health AI Developer Foundations license ("other") |
| `keivalya/MedQuad-MedicalQnADataset` | Hugging Face | No license declared (derived from NIH/NIDDK public pages) |
| PubMed abstracts (optional `jsonl` corpus) | NLM E-utilities | NLM terms; abstract copyright remains with the publisher |
| `qiaojin/PubMedQA` (retrieval evaluation) | Hugging Face | See the dataset card; use for evaluation only |

The embedding model is **non-commercial**. Do not deploy this pipeline in a
commercial product without replacing it with a permissively licensed embedder
(for example a PubMedBERT model released under Apache-2.0).

The MedQuad dataset does not declare a license. Verify the terms of the
underlying NIH pages before redistributing the corpus.
