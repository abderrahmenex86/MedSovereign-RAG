import json
import re
import time

from src.utils import log_message, new_trace_path, prune_traces, serialize_trace

CONTEXT_MISSING = "CONTEXT_MISSING"

SYSTEM_QA = (
    "You are a precise clinical AI. Answer the user's query strictly using the provided context. "
    "DO NOT repeat the context, query, or any headers in your output. Provide ONLY the direct clinical answer. "
    "Cite the documents you used as [doc_id]. "
    "If the context does not contain the answer, output EXACTLY and ONLY the phrase: 'CONTEXT_MISSING'."
)

SYSTEM_CRITIQUE = (
    "You are a strict medical auditor. Decide whether the ANSWER is fully supported by the CONTEXT "
    "and whether it actually answers the QUESTION. Reply with exactly one word: PASS or FAIL. "
    "Do not explain."
)

SYSTEM_REWRITE = (
    "You are a search query optimizer. The previous search failed. Rewrite the original query into a "
    "better, highly specific keyword search query. Output ONLY the raw search query without quotes."
)

SYSTEM_TITLE = (
    "You name clinical consultations. Write a specific title in 3 to 6 words and at most 40 "
    "characters, naming the condition and the intervention. Use sentence case, no quotes. "
    "Output only the title. Example: Acute bronchitis treatment"
)


def sanitize_title(raw_title, fallback):
    title = (raw_title or "").strip()

    if not title:
        title = fallback

    title = title.splitlines()[0]
    title = re.sub(r"^(title|conversation title)\s*:\s*", "", title, flags=re.IGNORECASE)
    title = title.strip().strip("\"'`").strip()
    title = re.sub(r"\s+", " ", title)
    title = title.rstrip(" .,;:-")

    if len(title) > 40:
        title = title[:40].rsplit(" ", 1)[0].rstrip(" .,;:-")

    return title or fallback[:40]


def clean_generated_text(text):
    cleaned = text.strip()
    for marker in ("ANSWER:", "Answer:"):
        if marker in cleaned:
            cleaned = cleaned.split(marker)[-1]
    return cleaned.strip()


def parse_verdict(text):
    """Parse the judge's verdict, tolerating extra prose.

    The first PASS/FAIL token wins, so a truncated "PASS. The answer..."
    still passes while any leading FAIL is respected.
    """
    tokens = re.findall(r"\b(PASS|FAIL)\b", (text or "").upper())
    return bool(tokens) and tokens[0] == "PASS"


def sanitize_query(raw_query, fallback):
    cleaned = (raw_query or "").strip().splitlines()
    cleaned = cleaned[0] if cleaned else ""
    cleaned = re.sub(r"^(new query|rewritten query|query)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip().strip("\"'").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:300] if cleaned else fallback


def select_context(candidates, limit):
    """Keep the best chunk per source document, in rerank order."""
    selected = []
    seen_documents = set()

    for candidate in candidates:
        document_id = candidate["doc_id"]
        if document_id in seen_documents:
            continue

        seen_documents.add(document_id)
        selected.append(candidate)

        if len(selected) >= limit:
            break

    return selected


def format_context(chunks):
    blocks = []

    for chunk in chunks:
        title = chunk.get("title") or chunk.get("question") or ""
        source = chunk.get("source") or ""
        published = chunk.get("published") or ""
        section = chunk.get("section") or ""

        descriptor = " | ".join(part for part in (source, published) if part)
        header = f"[{chunk['doc_id']}] {descriptor}".strip()
        if title:
            header += f"\nTitle: {title}"
        if section:
            header += f"\nSection: {section}"

        blocks.append(f"{header}\n{chunk['text']}")

    return "\n\n".join(blocks)


def rewrite_query(generator, original_query, failed_query):
    rewrite_prompt = (
        f"ORIGINAL QUERY: {original_query}\n"
        f"PREVIOUS FAILED QUERY: {failed_query}\n"
        "Generate the next search query:"
    )
    raw_query = generator.generate(SYSTEM_REWRITE, rewrite_prompt, max_tokens=32)
    return sanitize_query(raw_query, fallback=original_query)


def execute_agentic_rag(
    original_query,
    hybrid_index,
    embedder,
    reranker,
    generator,
    config,
    run_dir=None,
    persist_trace=True,
    cancel_event=None,
):
    started_at = time.perf_counter()
    trace = {
        "original_query": original_query,
        "iterations": [],
        "final_answer": None,
        "status": "FAILED",
        "attempts": 0,
    }

    current_query = original_query
    attempt = 0
    max_attempts = max(1, int(config.get("max_retries", 3)))
    top_k_retrieve = max(1, int(config.get("top_k_retrieve", 15)))
    top_k_generate = max(1, int(config.get("top_k_generate", 3)))
    min_rerank_score = config.get("min_rerank_score")
    error_message = None

    try:
        if config.get("generate_title", True) and not (
            cancel_event is not None and cancel_event.is_set()
        ):
            try:
                title_prompt = f"Question:\n{original_query}\n\nTitle:"
                raw_title = generator.generate(SYSTEM_TITLE, title_prompt, max_tokens=20)
                generated_title = sanitize_title(raw_title, original_query)
                trace["title"] = generated_title
                yield json.dumps({"event": "title", "data": generated_title}) + "\n"
            except Exception as exc:  # noqa: BLE001 - a title must not kill the answer
                log_message("engine", f"Title generation failed: {exc}")

        while attempt < max_attempts:
            if cancel_event is not None and cancel_event.is_set():
                trace["status"] = "CANCELLED"
                break

            attempt += 1
            trace["attempts"] = attempt
            iteration_trace = {"attempt": attempt, "query_used": current_query}

            yield json.dumps(
                {
                    "event": "status",
                    "step": "search",
                    "message": f"Attempt {attempt}: Searching keywords -> '{current_query}'",
                }
            ) + "\n"

            query_embedding = embedder.encode([current_query])
            raw_candidates = hybrid_index.retrieve(current_query, query_embedding, top_k=top_k_retrieve)

            if not raw_candidates:
                iteration_trace["outcome"] = "no_candidates"
                trace["iterations"].append(iteration_trace)
                yield json.dumps(
                    {"event": "correction", "message": "No documents found. Rewriting query..."}
                ) + "\n"

                if attempt < max_attempts:
                    current_query = rewrite_query(generator, original_query, current_query)
                continue

            yield json.dumps(
                {"event": "status", "step": "rerank", "message": "Cross-Encoder reranking candidates..."}
            ) + "\n"
            reranked_candidates = reranker.score(current_query, raw_candidates)
            top_chunks = select_context(reranked_candidates, top_k_generate)

            if not top_chunks:
                iteration_trace["outcome"] = "no_candidates_after_rerank"
                trace["iterations"].append(iteration_trace)
                yield json.dumps(
                    {"event": "correction", "message": "No relevant passages survived reranking."}
                ) + "\n"

                if attempt < max_attempts:
                    current_query = rewrite_query(generator, original_query, current_query)
                continue

            if min_rerank_score is not None and top_chunks[0]["rerank_score"] < min_rerank_score:
                iteration_trace["outcome"] = "below_score_threshold"
                iteration_trace["best_rerank_score"] = top_chunks[0]["rerank_score"]
                trace["iterations"].append(iteration_trace)
                yield json.dumps(
                    {"event": "correction", "message": "No passage passed the relevance threshold."}
                ) + "\n"

                if attempt < max_attempts:
                    current_query = rewrite_query(generator, original_query, current_query)
                continue

            yield json.dumps({"event": "sources", "data": top_chunks}) + "\n"

            context_string = format_context(top_chunks)
            iteration_trace["retrieved_context"] = context_string

            yield json.dumps(
                {"event": "status", "step": "drafting", "message": "Drafting clinical response..."}
            ) + "\n"

            user_prompt = f"CONTEXT:\n{context_string}\n\nQUERY:\n{original_query}"
            generated_parts = []
            cancelled = False
            for token in generator.generate_stream(
                SYSTEM_QA, user_prompt, max_tokens=1024, cancel_event=cancel_event
            ):
                if cancel_event is not None and cancel_event.is_set():
                    cancelled = True
                    break

                generated_parts.append(token)
                yield json.dumps({"event": "token", "data": token}) + "\n"

            if cancelled:
                trace["status"] = "CANCELLED"
                break
            generated_answer = clean_generated_text("".join(generated_parts))
            iteration_trace["generated_answer"] = generated_answer

            if not generated_answer:
                passed = False
                critique_result = "FAIL - Empty answer"
            elif CONTEXT_MISSING in generated_answer.upper():
                passed = False
                critique_result = "FAIL - Context Missing"
            else:
                yield json.dumps(
                    {
                        "event": "status",
                        "step": "critique",
                        "message": "Auditor evaluating response for hallucinations...",
                    }
                ) + "\n"
                critique_prompt = (
                    f"QUESTION:\n{original_query}\n\n"
                    f"CONTEXT:\n{context_string}\n\n"
                    f"ANSWER:\n{generated_answer}"
                )
                critique_result = generator.generate(SYSTEM_CRITIQUE, critique_prompt, max_tokens=8)
                passed = parse_verdict(critique_result)

            iteration_trace["critique"] = critique_result
            iteration_trace["outcome"] = "passed" if passed else "rejected"
            trace["iterations"].append(iteration_trace)

            if passed:
                yield json.dumps(
                    {"event": "status", "step": "success", "message": "Critique PASSED. Answer verified."}
                ) + "\n"
                trace["final_answer"] = generated_answer
                trace["status"] = "SUCCESS"
                break

            yield json.dumps(
                {"event": "correction", "message": "Hallucination detected. Correcting reasoning..."}
            ) + "\n"

            if attempt < max_attempts:
                current_query = rewrite_query(generator, original_query, current_query)
            else:
                trace["status"] = "REFUSED"

    except GeneratorExit:
        trace["status"] = "CANCELLED"
        raise
    except Exception as exc:  # noqa: BLE001 - the stream must always terminate with `done`
        trace["status"] = "ERROR"
        trace["error"] = f"{type(exc).__name__}: {exc}"
        error_message = "The pipeline failed while generating an answer. Please retry."
        log_message("engine", f"Pipeline error: {trace['error']}")
    finally:
        trace["duration_s"] = round(time.perf_counter() - started_at, 3)

        if persist_trace and run_dir:
            try:
                serialize_trace(trace, new_trace_path(run_dir))
                prune_traces(run_dir, keep=int(config.get("trace_retention", 200)))
            except OSError as exc:
                log_message("engine", f"Could not persist trace: {exc}")

    if error_message:
        yield json.dumps({"event": "error", "message": error_message}) + "\n"

    if trace["status"] == "FAILED":
        trace["status"] = "REFUSED"

    yield json.dumps({"event": "done", "trace": trace}) + "\n"
