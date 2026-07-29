import json
import os
import random
from datetime import datetime

import numpy as np
import torch
from tqdm.auto import tqdm


def set_determinism(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def log_message(category, message, log_file=None):
    timestamp = datetime.now().strftime("%m/%d - %H:%M")
    formatted_message = f"[{category.upper()}] [{timestamp}] {message}"
    tqdm.write(formatted_message)

    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(formatted_message + "\n")


def serialize_trace(trace_dict, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(trace_dict, f, indent=4, ensure_ascii=False)


def calculate_token_distribution(tokenizer, texts, out_path):
    import matplotlib.pyplot as plt

    lengths = [len(tokenizer.encode(t)) for t in texts]

    plt.figure(figsize=(10, 6), dpi=300)
    plt.hist(lengths, bins=50, color="#1A56DB", alpha=0.8)
    plt.title("Document Chunk Token Length Distribution")
    plt.xlabel("Token Count")
    plt.ylabel("Frequency")
    plt.grid(True, linestyle="--", alpha=0.5)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
