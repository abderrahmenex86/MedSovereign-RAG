import json
import threading
from pathlib import Path

from src.engine import (
    SYSTEM_CRITIQUE,
    clean_generated_text,
    execute_agentic_rag,
    parse_verdict,
    sanitize_query,
    select_context,
)


class FakeEmbedder:
    def encode(self, texts):
        return None


class FakeIndex:
    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = 0

    def retrieve(self, query, embedding, top_k=15):
        self.calls += 1
        return list(self.candidates)


class FakeReranker:
    def score(self, query, candidates):
        return sorted(
            [{**candidate, "rerank_score": float(candidate.get("rank", 0))} for candidate in candidates],
            key=lambda item: item["rerank_score"],
            reverse=True,
        )


class FakeGenerator:
    def __init__(self, critique="PASS", fail_after=None):
        self.critique = critique
        self.fail_after = fail_after
        self.critique_calls = 0
        self.rewrite_calls = 0

    def generate(self, system_prompt, user_prompt, max_tokens=256):
        if system_prompt == SYSTEM_CRITIQUE:
            self.critique_calls += 1
            return self.critique
        self.rewrite_calls += 1
        return "better query"

    def generate_stream(self, system_prompt, user_prompt, max_tokens=256, cancel_event=None):
        if self.fail_after == 0:
            raise RuntimeError("CUDA out of memory")

        for index, token in enumerate(["The ", "answer ", "is ", "grounded."]):
            if self.fail_after is not None and index >= self.fail_after:
                raise RuntimeError("CUDA out of memory")
            yield token


def _run(candidates, generator, max_retries=3, persist=False, run_dir=None, cancel_event=None):
    events = list(
        execute_agentic_rag(
            "what is asthma",
            FakeIndex(candidates),
            FakeEmbedder(),
            FakeReranker(),
            generator,
            {"max_retries": max_retries, "top_k_retrieve": 5, "top_k_generate": 3},
            run_dir=run_dir,
            persist_trace=persist,
            cancel_event=cancel_event,
        )
    )
    parsed = [json.loads(event) for event in events]
    return parsed


def _candidates():
    return [
        {"chunk_id": "doc_0_chunk_0", "doc_id": "doc_0", "question": "asthma", "text": "asthma text", "rank": 5},
        {"chunk_id": "doc_1_chunk_0", "doc_id": "doc_1", "question": "copd", "text": "copd text", "rank": 1},
    ]


def test_parse_verdict_is_first_token_wins():
    assert parse_verdict("PASS. The answer is supported,")
    assert not parse_verdict("FAIL: contradicts the context")
    assert parse_verdict("The answer is supported. PASS")
    assert not parse_verdict("")
    assert not parse_verdict("no verdict here")


def test_clean_generated_text_strips_answer_header():
    assert clean_generated_text("ANSWER: rest and fluids") == "rest and fluids"
    assert clean_generated_text("  rest and fluids  ") == "rest and fluids"


def test_sanitize_query_strips_prefix_and_quotes():
    assert sanitize_query('NEW QUERY: "acute bronchitis"', "fallback") == "acute bronchitis"
    assert sanitize_query("", "fallback") == "fallback"


def test_select_context_keeps_one_chunk_per_document():
    candidates = _candidates() + [
        {"chunk_id": "doc_0_chunk_1", "doc_id": "doc_0", "question": "asthma", "text": "duplicate", "rank": 9}
    ]

    selected = select_context(candidates, limit=3)

    assert [chunk["doc_id"] for chunk in selected] == ["doc_0", "doc_1"]


def test_successful_run_ends_with_done_success():
    events = _run(_candidates(), FakeGenerator(critique="PASS"))

    assert events[-1]["event"] == "done"
    assert events[-1]["trace"]["status"] == "SUCCESS"
    assert events[-1]["trace"]["final_answer"] == "The answer is grounded."
    assert events[-1]["trace"]["attempts"] == 1


def test_empty_answer_is_rejected_without_calling_the_judge():
    class EmptyGenerator(FakeGenerator):
        def generate_stream(
            self, system_prompt, user_prompt, max_tokens=256, cancel_event=None
        ):
            return
            yield  # pragma: no cover

    generator = EmptyGenerator()
    events = _run(_candidates(), generator, max_retries=1)

    assert events[-1]["trace"]["status"] == "REFUSED"
    assert generator.critique_calls == 0
    assert events[-1]["trace"]["iterations"][0]["critique"] == "FAIL - Empty answer"


def test_refusal_after_max_attempts():
    generator = FakeGenerator(critique="FAIL")
    events = _run(_candidates(), generator, max_retries=2)

    trace = events[-1]["trace"]
    assert trace["status"] == "REFUSED"
    assert trace["attempts"] == 2
    assert trace["final_answer"] is None
    assert generator.rewrite_calls == 1


def test_empty_retrieval_rewrites_and_does_not_generate():
    generator = FakeGenerator()
    events = _run([], generator, max_retries=2)

    assert events[-1]["trace"]["status"] == "REFUSED"
    assert generator.critique_calls == 0
    assert generator.rewrite_calls == 1


def test_pipeline_error_still_emits_done(tmp_path: Path):
    events = _run(_candidates(), FakeGenerator(fail_after=1), persist=True, run_dir=tmp_path)

    assert any(event["event"] == "error" for event in events)
    assert events[-1]["event"] == "done"
    assert events[-1]["trace"]["status"] == "ERROR"
    assert "CUDA out of memory" in events[-1]["trace"]["error"]
    assert len(list(tmp_path.glob("trace_*.json"))) == 1


def test_cancellation_stops_before_first_attempt():
    cancel_event = threading.Event()
    cancel_event.set()

    events = _run(_candidates(), FakeGenerator(), cancel_event=cancel_event)

    assert events[-1]["trace"]["status"] == "CANCELLED"
    assert events[-1]["trace"]["attempts"] == 0
