import json
import os

from datasets import load_dataset


def download_medquad():
    os.makedirs("dataset", exist_ok=True)
    out_path = "dataset/medquad_corpus.json"

    print("[INFO] Downloading MedQuad dataset from Hugging Face...")
    dataset = load_dataset("keivalya/MedQuad-MedicalQnADataset", split="train")

    corpus = []
    for row in dataset:
        answer = row.get("Answer") or row.get("answer") or row.get("text") or ""
        question = row.get("Question") or row.get("question") or ""

        if answer:
            corpus.append({"Question": question, "Answer": answer})

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=4)

    print(f"[SUCCESS] {len(corpus)} medical records successfully parsed and saved to {out_path}!")


if __name__ == "__main__":
    download_medquad()
