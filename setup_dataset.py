import argparse
import json
import os
from pathlib import Path

from datasets import load_dataset

DATASET_NAME = "keivalya/MedQuad-MedicalQnADataset"
OUTPUT_PATH = Path("dataset/medquad_corpus.json")


def download_medquad(output_path=OUTPUT_PATH, force=False):
    if output_path.exists() and not force:
        print(f"[INFO] {output_path} already exists. Use --force to re-download.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Downloading {DATASET_NAME} from Hugging Face...")
    dataset = load_dataset(DATASET_NAME, split="train")

    corpus = []
    seen_answers = set()

    for row in dataset:
        answer = row.get("Answer") or row.get("answer") or row.get("text") or ""
        question = row.get("Question") or row.get("question") or ""
        focus = row.get("Focus") or row.get("focus") or ""

        if not answer:
            continue

        # MedQuad contains duplicate answers scraped from several pages.
        fingerprint = " ".join(answer.lower().split())
        if fingerprint in seen_answers:
            continue
        seen_answers.add(fingerprint)

        corpus.append({"Question": question, "Answer": answer, "Focus": focus})

    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with open(temporary_path, "w", encoding="utf-8") as file_handle:
        json.dump(corpus, file_handle, indent=4)
    os.replace(temporary_path, output_path)

    print(f"[SUCCESS] {len(corpus)} unique records saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Download and normalize the MedQuad corpus.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Destination JSON file.")
    parser.add_argument("--force", action="store_true", help="Re-download even if the file exists.")
    arguments = parser.parse_args()
    download_medquad(arguments.output, arguments.force)


if __name__ == "__main__":
    main()
