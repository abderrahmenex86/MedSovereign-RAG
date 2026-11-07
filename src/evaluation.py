"""Small retrieval metrics used by the evaluation script."""

from __future__ import annotations


def recall_at_k(ranked_ids, target, k):
    return int(target in ranked_ids[:k])


def reciprocal_rank(ranked_ids, target):
    for position, document_id in enumerate(ranked_ids, start=1):
        if document_id == target:
            return 1.0 / position
    return 0.0


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def summarize_retrieval(ranked_lists, targets, ks=(1, 5, 10)):
    if len(ranked_lists) != len(targets):
        raise ValueError("ranked_lists and targets must have the same length")

    metrics = {}
    for k in ks:
        metrics[f"recall@{k}"] = mean(
            recall_at_k(ranked, target, k)
            for ranked, target in zip(ranked_lists, targets, strict=True)
        )

    reciprocal_ranks = [
        reciprocal_rank(ranked[: max(ks)], target)
        for ranked, target in zip(ranked_lists, targets, strict=True)
    ]
    metrics[f"mrr@{max(ks)}"] = mean(reciprocal_ranks)
    metrics["n"] = len(targets)
    return metrics
