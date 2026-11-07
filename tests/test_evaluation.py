from src.evaluation import recall_at_k, reciprocal_rank, summarize_retrieval


def test_recall_at_k():
    ranked = ["a", "b", "c"]

    assert recall_at_k(ranked, "b", 1) == 0
    assert recall_at_k(ranked, "b", 2) == 1
    assert recall_at_k(ranked, "missing", 3) == 0


def test_reciprocal_rank():
    assert reciprocal_rank(["a", "b", "c"], "a") == 1.0
    assert reciprocal_rank(["a", "b", "c"], "b") == 0.5
    assert reciprocal_rank(["a", "b", "c"], "missing") == 0.0


def test_summarize_retrieval():
    ranked_lists = [["a", "b"], ["c"], ["d", "e"]]
    targets = ["a", "c", "missing"]

    metrics = summarize_retrieval(ranked_lists, targets, ks=(1, 2))

    assert metrics["recall@1"] == 2 / 3
    assert metrics["recall@2"] == 2 / 3
    assert metrics["mrr@2"] == (1.0 + 1.0 + 0.0) / 3
    assert metrics["n"] == 3


def test_summary_rejects_mismatched_lengths():
    try:
        summarize_retrieval([["a"]], ["a", "b"])
    except ValueError as exc:
        assert "same length" in str(exc)
    else:
        raise AssertionError("expected ValueError")
