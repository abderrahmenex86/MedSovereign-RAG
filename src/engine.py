import json
import os
import time

from src.utils import log_message, serialize_trace


def clean_generated_text(text):
    if "ANSWER:" in text:
        text = text.split("ANSWER:")[-1]
    elif "Answer:" in text:
        text = text.split("Answer:")[-1]
    return text.strip()


def execute_agentic_rag(original_query, hybrid_index, embedder, reranker, generator, config, run_dir):
    trace = {"original_query": original_query, "iterations": [], "final_answer": None, "status": "FAILED"}
    current_query = original_query
    attempt = 0
    max_attempts = config.get("max_retries", 3)

    system_qa = (
        "You are a precise clinical AI. Answer the user's query strictly using the provided context. "
        "DO NOT repeat the context, query, or any headers in your output. Provide ONLY the direct clinical answer. "
        "If the context does not contain the answer, output EXACTLY and ONLY the phrase: 'CONTEXT_MISSING'."
    )
    system_critique = "You are a strict medical auditor. Evaluate the provided ANSWER against the provided CONTEXT. Does the ANSWER contain hallucinations? Output exactly one word: 'PASS' if the answer is fully supported, or 'FAIL' if it is not."
    system_rewrite = "You are a search query optimizer. The previous search failed. Rewrite the original query into a better, highly specific keyword search query. Output ONLY the raw search query without quotes."

    while attempt < max_attempts:
        attempt += 1
        iteration_trace = {"attempt": attempt, "query_used": current_query}

        yield json.dumps(
            {
                "event": "status",
                "step": "search",
                "message": f"Attempt {attempt}: Searching keywords -> '{current_query}'",
            }
        ) + "\n"

        query_embedding = embedder.encode([current_query])
        raw_candidates = hybrid_index.retrieve(current_query, query_embedding, top_k=config.get("top_k_retrieve", 15))

        if not raw_candidates:
            yield json.dumps({"event": "correction", "message": "No documents found. Rewriting query..."}) + "\n"

        yield json.dumps(
            {"event": "status", "step": "rerank", "message": "Cross-Encoder reranking candidates..."}
        ) + "\n"
        reranked_candidates = reranker.score(current_query, raw_candidates)
        top_chunks = reranked_candidates[: config.get("top_k_generate", 3)]

        yield json.dumps({"event": "sources", "data": top_chunks}) + "\n"

        context_string = "\n\n".join([f"Document {c['doc_id']}:\n{c['text']}" for c in top_chunks])
        iteration_trace["retrieved_context"] = context_string

        yield json.dumps({"event": "status", "step": "drafting", "message": "Drafting clinical response..."}) + "\n"

        user_prompt = f"CONTEXT:\n{context_string}\n\nQUERY:\n{original_query}"
        generated_answer = ""
        for token in generator.generate_stream(system_qa, user_prompt, max_tokens=1024):
            generated_answer += token
            yield json.dumps({"event": "token", "data": token}) + "\n"

        generated_answer = clean_generated_text(generated_answer)
        iteration_trace["generated_answer"] = generated_answer

        if "CONTEXT_MISSING" in generated_answer.upper():
            critique_result = "FAIL - Context Missing"
        else:
            yield json.dumps(
                {"event": "status", "step": "critique", "message": "Auditor evaluating response for hallucinations..."}
            ) + "\n"
            critique_prompt = f"CONTEXT:\n{context_string}\n\nANSWER:\n{generated_answer}"
            critique_result = generator.generate(system_critique, critique_prompt, max_tokens=50)

        iteration_trace["critique"] = critique_result
        trace["iterations"].append(iteration_trace)

        if "PASS" in critique_result.upper() and "FAIL" not in critique_result.upper():
            yield json.dumps(
                {"event": "status", "step": "success", "message": "Critique PASSED. Answer verified."}
            ) + "\n"
            trace["final_answer"] = generated_answer
            trace["status"] = "SUCCESS"
            break
        else:
            yield json.dumps(
                {"event": "correction", "message": "Hallucination detected. Correcting reasoning..."}
            ) + "\n"
            if attempt < max_attempts:
                rewrite_prompt = f"ORIGINAL QUERY: {original_query}\nPREVIOUS FAILED QUERY: {current_query}\nGenerate the next search query:"
                raw_new_query = generator.generate(system_rewrite, rewrite_prompt, max_tokens=50)
                current_query = raw_new_query.replace('"', "").replace("'", "").replace("NEW QUERY:", "").strip()

    timestamp = str(time.time()).replace(".", "")
    trace_path = os.path.join(run_dir, f"trace_{timestamp}.json")
    serialize_trace(trace, trace_path)

    yield json.dumps({"event": "done", "trace": trace}) + "\n"
