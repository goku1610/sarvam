"""Shared Plan → Search → Answer orchestration for API and evaluation."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from filtering import build_context_from_pages
from search import WebSearchScraper

ZERO_RESULT_SEARCH_RETRY_LIMIT = 2
MAX_HOPS = 3
MAX_ANSWER_REFINEMENT_LOOPS = 2


def split_plan_into_steps(plan_text: str) -> list[str]:
    return [
        step.strip()
        for step in re.split(r"(?<=[.!?])\s+|\n+", plan_text.strip())
        if step.strip()
    ]


def parse_plan_output(raw: str) -> dict[str, Any]:
    """Parse structured plan tokens from planner stream output."""
    title = ""
    plan_steps: list[str] = []
    search_queries: list[str] = []

    title_match = re.search(r"<TITLE_START>([\s\S]*?)<TITLE_END>", raw)
    if title_match:
        title = title_match.group(1).strip()

    if "<PLAN_START>" in raw:
        plan_content = raw.split("<PLAN_START>", 1)[1].split("<PLAN_END>")[0].strip()
        plan_steps = split_plan_into_steps(plan_content)

    queries_match = re.search(r"<QUERIES_START>([\s\S]*?)<QUERIES_END>", raw)
    if queries_match:
        try:
            parsed = json.loads(queries_match.group(1).strip())
            if isinstance(parsed, list):
                search_queries = [str(q).strip() for q in parsed if str(q).strip()]
        except json.JSONDecodeError:
            pass

    return {
        "title": title,
        "plan_steps": plan_steps,
        "search_queries": search_queries,
    }


@dataclass
class PlanResult:
    title: str
    plan_steps: list[str]
    search_queries: list[str]
    raw: str = ""


@dataclass
class SearchResult:
    query: str
    search_queries: list[str]
    pages: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    context: str
    hop_count: int
    intermediate_answers: list[dict[str, Any]] = field(default_factory=list)
    chunk_count: int = 0
    selected_count: int = 0
    unreachable_count: int = 0


@dataclass
class AnswerResult:
    raw_answer: str
    final_answer: str
    citation_validation: dict[str, Any]
    gap_analysis: dict[str, Any] = field(default_factory=dict)


async def run_plan(planner: Any, query: str, deep_research: bool = False) -> PlanResult:
    """Collect full plan stream into a PlanResult."""
    parts: list[str] = []
    for token in planner.generate_plan_stream(query, deep_research):
        parts.append(token)
        await asyncio.sleep(0)
    raw = "".join(parts)
    parsed = parse_plan_output(raw)
    if not parsed["search_queries"]:
        parsed["search_queries"] = [query]
    if not parsed["plan_steps"]:
        parsed["plan_steps"] = ["Research the user question on the web and synthesize findings."]
    return PlanResult(
        title=parsed["title"] or query[:48],
        plan_steps=parsed["plan_steps"],
        search_queries=parsed["search_queries"],
        raw=raw,
    )


async def run_search(
    planner: Any,
    scraper: WebSearchScraper,
    query: str,
    search_queries: list[str],
    max_hops: int = 1,
    plan_steps: list[str] | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> SearchResult:
    """Execute search + fetch + context selection (multi-hop when max_hops > 1)."""
    queries = [q.strip() for q in search_queries if q.strip()]
    max_hops = min(max_hops, MAX_HOPS)
    plan_steps = plan_steps or []

    def emit(event: dict[str, Any]) -> None:
        if on_event:
            on_event(event)

    if not queries:
        return SearchResult(
            query=query,
            search_queries=[],
            pages=[],
            chunks=[],
            context="",
            hop_count=0,
        )

    all_attempted_queries = queries[:]
    all_valid_pages: list[dict[str, Any]] = []
    all_accumulated_chunks: list[dict[str, Any]] = []
    intermediate_answers: list[dict[str, Any]] = []
    hop_queries: list[str] = []
    hop = 0

    for hop in range(1, max_hops + 1):
        active_queries = all_attempted_queries if hop == 1 else hop_queries

        if max_hops > 1:
            emit({
                "type": "hop_start",
                "hop": hop,
                "max_hops": max_hops,
                "queries": active_queries,
            })

        attempted_queries = active_queries[:]
        current_active = active_queries[:]
        valid_pages: list[dict[str, Any]] = []

        for retry_index in range(ZERO_RESULT_SEARCH_RETRY_LIMIT + 1):
            emit({
                "type": "progress",
                "message": "Searching the web" if retry_index == 0 else "Retrying with broader search queries",
                "queries": current_active,
            })
            valid_pages = await scraper.execute_concurrent_research(current_active)
            if valid_pages:
                break

            recovery_queries = await asyncio.to_thread(
                planner.generate_zero_result_queries,
                query or " ".join(queries),
                attempted_queries,
            )
            recovery_queries = [
                q
                for q in recovery_queries
                if q.strip().lower() not in {aq.lower() for aq in attempted_queries}
            ]
            if not recovery_queries:
                break
            attempted_queries.extend(recovery_queries)
            current_active = recovery_queries

        for q in attempted_queries:
            if q not in all_attempted_queries:
                all_attempted_queries.append(q)

        emit({"type": "progress", "message": "Fetching and cleaning sources"})
        for page in valid_pages:
            emit({
                "type": "result",
                "title": page.get("title", ""),
                "url": page.get("url", ""),
                "domain": page.get("domain", ""),
                "content": page.get("content", "")[:300],
                "hop": hop,
            })

        all_valid_pages.extend(valid_pages)

        emit({"type": "progress", "message": "Selecting relevant context"})
        research_context = build_context_from_pages(
            query or " ".join(queries),
            all_valid_pages,
            additional_queries=all_attempted_queries,
            deep_research=(max_hops > 1),
        )
        all_accumulated_chunks = research_context.get("chunks", [])

        emit({
            "type": "context_ready",
            "chunks": research_context["chunks"],
            "context": research_context["context"],
            "hop": hop,
            "attempted_queries": all_attempted_queries,
        })

        if max_hops <= 1 or hop >= max_hops:
            break
        if not all_accumulated_chunks:
            break

        emit({
            "type": "progress",
            "message": f"Evaluating whether context is sufficient (hop {hop} of {max_hops})",
        })
        evaluation = await asyncio.to_thread(
            planner.evaluate_context_sufficiency,
            query or " ".join(queries),
            plan_steps,
            all_accumulated_chunks,
            hop,
            max_hops,
        )
        emit({
            "type": "hop_evaluation",
            "hop": hop,
            "sufficient": evaluation["sufficient"],
            "intermediate_answer": evaluation["intermediate_answer"],
            "missing_info": evaluation["missing_info"],
            "reasoning": evaluation["reasoning"],
            "next_queries": evaluation["next_queries"],
        })

        if evaluation["intermediate_answer"]:
            intermediate_answers.append({
                "hop": hop,
                "answer": evaluation["intermediate_answer"],
            })

        if evaluation["sufficient"] or not evaluation["next_queries"]:
            break

        already_searched = {q.strip().lower() for q in all_attempted_queries}
        hop_queries = [
            q for q in evaluation["next_queries"]
            if q.strip().lower() not in already_searched
        ]
        if not hop_queries:
            break

    final_context = build_context_from_pages(
        query or " ".join(queries),
        all_valid_pages,
        additional_queries=all_attempted_queries,
        deep_research=(max_hops > 1),
    )

    return SearchResult(
        query=query,
        search_queries=all_attempted_queries,
        pages=all_valid_pages,
        chunks=final_context.get("chunks", []),
        context=final_context.get("context", ""),
        hop_count=hop,
        intermediate_answers=intermediate_answers,
        chunk_count=final_context.get("chunk_count", 0),
        selected_count=final_context.get("selected_count", 0),
        unreachable_count=final_context.get("unreachable_count", 0),
    )


async def run_answer(
    planner: Any,
    query: str,
    plan: list[str],
    search_queries: list[str],
    context: str,
    chunks: list[dict[str, Any]],
    history_context: str = "",
    intermediate_answers: list[dict[str, Any]] | None = None,
    deep_research: bool = False,
    trim_text_fn: Callable[[str, int], str] | None = None,
    validate_citations_fn: Callable[[str, list], tuple] | None = None,
    on_token: Callable[[str], None] | None = None,
    refine_gaps: bool = True,
) -> AnswerResult:
    """Generate and validate final answer from selected context."""
    from main import trim_text, validate_answer_citations

    trim_fn = trim_text_fn or trim_text
    validate_fn = validate_citations_fn or validate_answer_citations

    capped_context = trim_fn(context, 32000 if deep_research else 28000)
    if not capped_context.strip():
        return AnswerResult(
            raw_answer="",
            final_answer="",
            citation_validation={"error": "no_context"},
        )

    parts: list[str] = []
    for token in planner.generate_answer_stream(
        user_query=query,
        plan=plan,
        search_queries=search_queries,
        web_context=capped_context,
        chunks=chunks,
        history_context=history_context,
        intermediate_answers=intermediate_answers,
        deep_research=deep_research,
    ):
        parts.append(token)
        if on_token:
            on_token(token)
        await asyncio.sleep(0)

    raw_answer = "".join(parts).strip()
    final_answer, citation_validation = validate_fn(raw_answer, chunks)
    gap_analysis: dict[str, Any] = {
        "has_gaps": False,
        "gaps": [],
        "suggested_queries": [],
        "severity": "none",
    }

    if deep_research and refine_gaps:
        gap_analysis = await asyncio.to_thread(
            planner.detect_answer_gaps,
            final_answer,
            query,
            chunks,
        )
        refinement_count = 0
        while (
            gap_analysis.get("has_gaps")
            and gap_analysis.get("severity") == "major"
            and refinement_count < MAX_ANSWER_REFINEMENT_LOOPS
        ):
            refinement_count += 1
            gap_descriptions = "\n".join(f"- {g}" for g in gap_analysis.get("gaps", []))
            refined_parts: list[str] = []
            suffix = (
                f"\n\n**IMPORTANT — Previous answer had these gaps:**\n{gap_descriptions}\n"
                "Re-examine the source evidence carefully and produce a more complete answer."
            )
            for token in planner.generate_answer_stream(
                user_query=query + suffix,
                plan=plan,
                search_queries=search_queries,
                web_context=capped_context,
                chunks=chunks,
                history_context=history_context,
                intermediate_answers=intermediate_answers,
                deep_research=deep_research,
            ):
                refined_parts.append(token)
                if on_token:
                    on_token(token)
                await asyncio.sleep(0)

            refined_raw = "".join(refined_parts).strip()
            if len(refined_raw) > len(final_answer) * 0.5:
                final_answer, citation_validation = validate_fn(refined_raw, chunks)
                gap_analysis = await asyncio.to_thread(
                    planner.detect_answer_gaps,
                    final_answer,
                    query,
                    chunks,
                )
            else:
                break

    return AnswerResult(
        raw_answer=raw_answer,
        final_answer=final_answer,
        citation_validation=citation_validation,
        gap_analysis=gap_analysis,
    )


async def run_follow_up_chat(
    planner: Any,
    scraper: WebSearchScraper,
    session: dict[str, Any],
    user_message: str,
    build_history_context_fn: Callable,
    trim_text_fn: Callable[[str, int], str],
    validate_citations_fn: Callable[[str, list], tuple],
) -> dict[str, Any]:
    """Run a single follow-up turn using saved session evidence."""
    state = session.get("state", {})
    fetched_pages = state.get("fetched_pages") if isinstance(state.get("fetched_pages"), list) else []
    research_context = state.get("research_context") if isinstance(state.get("research_context"), dict) else {}

    recontextualized = (
        build_context_from_pages(user_message, fetched_pages)
        if fetched_pages
        else research_context
    )
    prior_context = trim_text_fn(str(recontextualized.get("context", "")), 18000)
    prior_chunks = recontextualized.get("chunks", [])
    if not isinstance(prior_chunks, list):
        prior_chunks = []

    history_context = build_history_context_fn(session, current_query=user_message)
    chat_plan = await asyncio.to_thread(
        planner.plan_chat_research,
        user_message,
        history_context,
        prior_context,
    )
    search_queries = chat_plan.get("search_queries", [])
    opened_urls: list[str] = []
    fresh_context: dict[str, Any] = {"chunks": [], "context": ""}

    if chat_plan.get("needs_search") and search_queries:
        attempted = search_queries[:]
        active = search_queries[:]
        valid_pages: list[dict[str, Any]] = []
        for _ in range(ZERO_RESULT_SEARCH_RETRY_LIMIT + 1):
            valid_pages = await scraper.execute_concurrent_research(active)
            if valid_pages:
                break
            recovery = await asyncio.to_thread(
                planner.generate_zero_result_queries,
                user_message,
                attempted,
            )
            recovery = [
                q for q in recovery
                if q.strip().lower() not in {a.lower() for a in attempted}
            ]
            if not recovery:
                break
            attempted.extend(recovery)
            active = recovery
        search_queries = attempted
        for page in valid_pages:
            if page.get("url"):
                opened_urls.append(page["url"])
        fresh_context = build_context_from_pages(user_message, valid_pages)

    answer_context = prior_context
    answer_chunks = prior_chunks
    if fresh_context.get("context"):
        answer_context = trim_text_fn(
            f"Previously selected context:\n{prior_context or 'None'}\n\n"
            f"Fresh follow-up context:\n{fresh_context['context']}",
            28000,
        )
        answer_chunks = prior_chunks + fresh_context.get("chunks", [])

    parts: list[str] = []
    for token in planner.generate_answer_stream(
        user_query=user_message,
        plan=[
            "Answer the follow-up using the prior conversation context.",
            (
                "Fresh web research was run because saved evidence was insufficient."
                if search_queries
                else "No fresh search was needed; use saved research context."
            ),
        ],
        search_queries=search_queries,
        web_context=answer_context,
        chunks=answer_chunks,
        history_context=history_context,
    ):
        parts.append(token)
        await asyncio.sleep(0)

    raw = "".join(parts).strip()
    final_answer, citation_validation = validate_citations_fn(raw, answer_chunks)

    return {
        "final_answer": final_answer,
        "citation_validation": citation_validation,
        "search_queries": search_queries,
        "urls_opened": sorted({u for u in opened_urls if u}),
        "chunks": answer_chunks,
        "answered_from_existing_context": not bool(search_queries),
        "follow_up_search_reason": chat_plan.get("reason", ""),
        "history_context_nonempty": bool(history_context.strip()),
    }


async def run_research_case(
    planner: Any,
    scraper: WebSearchScraper,
    query: str,
    deep_research: bool = False,
    max_hops: int | None = None,
    session_store: Any = None,
    session_id: str | None = None,
    build_history_context_fn: Callable | None = None,
    trim_text_fn: Callable | None = None,
    validate_citations_fn: Callable | None = None,
) -> dict[str, Any]:
    """End-to-end plan → search → answer for a single query."""
    from main import build_history_context, trim_text, validate_answer_citations

    hops = max_hops if max_hops is not None else (MAX_HOPS if deep_research else 1)
    history_fn = build_history_context_fn or build_history_context
    trim_fn = trim_text_fn or trim_text
    validate_fn = validate_citations_fn or validate_answer_citations

    plan = await run_plan(planner, query, deep_research)
    search = await run_search(
        planner,
        scraper,
        query,
        plan.search_queries,
        max_hops=hops,
        plan_steps=plan.plan_steps,
    )

    session = session_store.get(session_id) if session_store and session_id else None
    history_context = history_fn(session, current_query=query) if session else ""

    answer = await run_answer(
        planner,
        query,
        plan.plan_steps,
        search.search_queries,
        search.context,
        search.chunks,
        history_context=history_context,
        intermediate_answers=search.intermediate_answers,
        deep_research=deep_research,
        trim_text_fn=trim_fn,
        validate_citations_fn=validate_fn,
        refine_gaps=deep_research,
    )

    if session_store and session_id:
        session_store.append_message(session_id, "user", query)
        session_store.append_message(session_id, "assistant", answer.final_answer)
        session_store.record_turn(
            session_id,
            {
                "query": query,
                "search_queries_issued": search.search_queries,
                "urls_opened": sorted({p.get("url", "") for p in search.pages if p.get("url")}),
                "context_snippets_selected": search.chunks,
                "final_answer": answer.final_answer,
                "citation_validation": answer.citation_validation,
                "gap_analysis": answer.gap_analysis,
            },
        )
        session_store.update_state(
            session_id,
            {
                "original_query": query,
                "plan_steps": plan.plan_steps,
                "research_context": {
                    "chunks": search.chunks,
                    "context": search.context,
                    "selected_count": search.selected_count,
                },
                "fetched_pages": search.pages,
                "final_answer": answer.final_answer,
                "intermediate_answers": search.intermediate_answers,
            },
            None,
        )

    return {
        "plan": plan,
        "search": search,
        "answer": answer,
    }
