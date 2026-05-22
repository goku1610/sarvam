#!/usr/bin/env python3
"""Run evaluation harness against the Deep Research Agent."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure repo root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent_pipeline import run_follow_up_chat, run_research_case
from eval.judge import judge_answer
from eval.metrics import compute_metrics
from main import JsonSessionStore, ResearchPlanner, load_local_env
from search import WebSearchScraper

DATASET_PATH = Path(__file__).parent / "dataset.json"
RESULTS_DIR = Path(__file__).parent / "results"
EVAL_MODE = "deep_research"
EVAL_MAX_HOPS = 3
VALID_CATEGORIES = {
    "factual",
    "multi_hop",
    "comparison",
    "insufficient_evidence",
    "conflicting_sources",
    "multi_turn",
}


def load_dataset(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cases", data if isinstance(data, list) else [])


def validate_dataset(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for case in cases:
        case_id = case.get("id")
        if not case_id:
            errors.append("Case missing id")
            continue
        if case_id in seen_ids:
            errors.append(f"Duplicate id: {case_id}")
        seen_ids.add(case_id)
        if case.get("category") not in VALID_CATEGORIES:
            errors.append(f"{case_id}: invalid category {case.get('category')}")
        if not case.get("query") and not case.get("turns"):
            errors.append(f"{case_id}: missing query")
        if case.get("category") == "multi_turn" and not case.get("turns"):
            errors.append(f"{case_id}: multi_turn requires turns array")
        if case.get("deep_research") is False:
            errors.append(
                f"{case_id}: deep_research must be true (evaluation runs in deep research mode only)"
            )
    return errors


def check_prerequisites(skip_keys: bool = False) -> list[str]:
    missing = []
    if not skip_keys:
        if not os.environ.get("TAVILY_API_KEY"):
            missing.append("TAVILY_API_KEY")
        if not os.environ.get("GEMINI_API_KEY"):
            missing.append("GEMINI_API_KEY")
    return missing


def serialize_plan(plan: Any) -> dict[str, Any]:
    return {
        "title": plan.title,
        "plan_steps": plan.plan_steps,
        "search_queries": plan.search_queries,
    }


def serialize_search(search: Any) -> dict[str, Any]:
    return {
        "search_queries": search.search_queries,
        "pages_count": len(search.pages),
        "chunks_count": len(search.chunks),
        "hop_count": search.hop_count,
        "selected_count": search.selected_count,
        "unreachable_count": search.unreachable_count,
        "urls_opened": sorted({p.get("url", "") for p in search.pages if p.get("url")}),
        "intermediate_answers": search.intermediate_answers,
    }


def serialize_answer(answer: Any) -> dict[str, Any]:
    return {
        "raw_answer": answer.raw_answer,
        "final_answer": answer.final_answer,
        "citation_validation": answer.citation_validation,
        "gap_analysis": answer.gap_analysis,
    }


async def run_single_case(
    case: dict[str, Any],
    session_store: JsonSessionStore,
    with_judge: bool,
) -> dict[str, Any]:
    from main import build_history_context

    planner = ResearchPlanner()
    scraper = WebSearchScraper()
    session = session_store.get_or_create()
    session_id = session["session_id"]

    start = time.perf_counter()
    follow_up_artifact: dict[str, Any] | None = None

    query = case.get("query", "")
    if case.get("category") == "multi_turn" and case.get("turns"):
        first_turn = case["turns"][0]
        query = first_turn.get("query") or case.get("query", "")

    result = await run_research_case(
        planner,
        scraper,
        query,
        deep_research=True,
        max_hops=EVAL_MAX_HOPS,
        session_store=session_store,
        session_id=session_id,
    )

    if case.get("category") == "multi_turn" and case.get("turns") and len(case["turns"]) > 1:
        follow_up = case["turns"][1].get("follow_up", "")
        session_store.append_message(session_id, "user", follow_up)
        updated_session = session_store.get(session_id) or session
        follow_up_artifact = await run_follow_up_chat(
            planner,
            scraper,
            updated_session,
            follow_up,
            build_history_context,
            __import__("main").trim_text,
            __import__("main").validate_answer_citations,
        )
        session_store.append_message(session_id, "assistant", follow_up_artifact["final_answer"])
        session_store.record_turn(
            session_id,
            {
                "query": follow_up,
                "search_queries_issued": follow_up_artifact.get("search_queries", []),
                "urls_opened": follow_up_artifact.get("urls_opened", []),
                "context_snippets_selected": follow_up_artifact.get("chunks", []),
                "final_answer": follow_up_artifact["final_answer"],
                "citation_validation": follow_up_artifact.get("citation_validation", {}),
                "answered_from_existing_context": follow_up_artifact.get(
                    "answered_from_existing_context", False
                ),
            },
        )

    answer_text = result["answer"].final_answer
    citation_validation = result["answer"].citation_validation
    chunks = result["search"].chunks

    if follow_up_artifact:
        answer_text = follow_up_artifact["final_answer"]
        citation_validation = follow_up_artifact.get("citation_validation", {})
        chunks = follow_up_artifact.get("chunks", chunks)

    search_artifact = serialize_search(result["search"])

    elapsed = time.perf_counter() - start
    metrics = compute_metrics(
        case,
        answer_text,
        citation_validation,
        search_artifact,
        follow_up_artifact,
    )

    judge_scores: dict[str, Any] | None = None
    if with_judge:
        judge_scores = judge_answer(
            planner,
            case.get("query", ""),
            answer_text,
            chunks,
            case.get("category", ""),
        )

    return {
        "id": case["id"],
        "category": case.get("category"),
        "query": case.get("query"),
        "mode": EVAL_MODE,
        "deep_research": True,
        "max_hops": EVAL_MAX_HOPS,
        "session_id": session_id,
        "elapsed_seconds": round(elapsed, 2),
        "plan": serialize_plan(result["plan"]),
        "search": search_artifact,
        "answer": {
            **serialize_answer(result["answer"]),
            "final_answer": answer_text,
            "citation_validation": citation_validation,
        },
        "follow_up": follow_up_artifact,
        "metrics": metrics,
        "judge": judge_scores,
    }


def aggregate_results(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in case_results:
        by_category[item["category"]].append(item)

    category_summaries = {}
    for category, items in by_category.items():
        passed = sum(1 for i in items if i["metrics"]["category_pass"])
        category_summaries[category] = {
            "total": len(items),
            "passed": passed,
            "pass_rate": round(passed / len(items), 3) if items else 0,
            "avg_grounded_citation_rate": round(
                sum(i["metrics"]["grounded_citation_rate"] for i in items) / len(items), 3
            ),
            "avg_citation_count": round(
                sum(i["metrics"]["citation_count"] for i in items) / len(items), 2
            ),
        }

    total_passed = sum(1 for i in case_results if i["metrics"]["category_pass"])
    return {
        "total_cases": len(case_results),
        "passed": total_passed,
        "pass_rate": round(total_passed / len(case_results), 3) if case_results else 0,
        "by_category": category_summaries,
    }


def write_summary_md(summary: dict[str, Any], case_results: list[dict[str, Any]], run_id: str) -> str:
    lines = [
        f"# Evaluation Summary — {run_id}",
        "",
        f"**Evaluation mode:** deep research (max_hops={summary.get('max_hops', EVAL_MAX_HOPS)})  ",
        f"**Total cases:** {summary['total_cases']}  ",
        f"**Passed:** {summary['passed']}  ",
        f"**Pass rate:** {summary['pass_rate']:.1%}",
        "",
        "## By category",
        "",
        "| Category | Total | Passed | Pass rate | Avg grounded citations |",
        "|----------|-------|--------|-----------|--------------------------|",
    ]
    for cat, stats in summary["by_category"].items():
        lines.append(
            f"| {cat} | {stats['total']} | {stats['passed']} | "
            f"{stats['pass_rate']:.1%} | {stats['avg_grounded_citation_rate']:.2f} |"
        )
    lines.extend(["", "## Per-case results", ""])
    for item in case_results:
        status = "PASS" if item["metrics"]["category_pass"] else "FAIL"
        failures = item["metrics"].get("failures", [])
        fail_text = f" — {', '.join(failures)}" if failures else ""
        lines.append(f"- **{item['id']}** [{status}]{fail_text} ({item['elapsed_seconds']}s)")
    lines.append("")
    return "\n".join(lines)


async def main_async(args: argparse.Namespace) -> int:
    load_local_env(REPO_ROOT / ".env")

    cases = load_dataset(Path(args.dataset))
    errors = validate_dataset(cases)
    if errors:
        print("Dataset validation errors:")
        for err in errors:
            print(f"  - {err}")
        return 1

    if args.dry_run:
        print(f"Dataset OK: {len(cases)} cases across {len(VALID_CATEGORIES)} categories.")
        print(f"Evaluation mode: {EVAL_MODE} only (max_hops={EVAL_MAX_HOPS})")
        for cat in sorted({c["category"] for c in cases}):
            count = sum(1 for c in cases if c["category"] == cat)
            print(f"  {cat}: {count}")
        return 0

    missing = check_prerequisites()
    if missing:
        print("Missing required environment variables:", ", ".join(missing))
        return 1

    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"Case not found: {args.case}")
            return 1

    if args.limit:
        cases = cases[: args.limit]

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    run_dir = RESULTS_DIR / run_id
    cases_dir = run_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    eval_sessions_path = str(REPO_ROOT / "data" / "eval_sessions.json")
    session_store = JsonSessionStore(path=eval_sessions_path)

    print(
        f"Running {len(cases)} case(s) in {EVAL_MODE} mode "
        f"(max_hops={EVAL_MAX_HOPS}) → {run_dir}"
    )

    case_results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']} ({case['category']})...")
        try:
            artifact = await run_single_case(
                case,
                session_store,
                with_judge=args.with_judge,
            )
            case_results.append(artifact)
            case_path = cases_dir / f"{case['id']}.json"
            with open(case_path, "w", encoding="utf-8") as f:
                json.dump(artifact, f, indent=2)
            status = "PASS" if artifact["metrics"]["category_pass"] else "FAIL"
            print(f"  → {status}")
        except Exception as error:
            print(f"  → ERROR: {error}")
            case_results.append({
                "id": case["id"],
                "category": case.get("category"),
                "error": str(error),
                "metrics": {"category_pass": False, "failures": [str(error)]},
            })

    valid_results = [r for r in case_results if "error" not in r]
    summary = aggregate_results(valid_results) if valid_results else {
        "total_cases": len(case_results),
        "passed": 0,
        "pass_rate": 0,
        "by_category": {},
    }
    summary["run_id"] = run_id
    summary["mode"] = EVAL_MODE
    summary["max_hops"] = EVAL_MAX_HOPS
    summary["with_judge"] = args.with_judge
    summary["timestamp"] = datetime.now().isoformat()

    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "cases": case_results}, f, indent=2)

    md = write_summary_md(summary, case_results, run_id)
    with open(run_dir / "summary.md", "w", encoding="utf-8") as f:
        f.write(md)

    print("\n" + md)
    print(f"\nResults written to {run_dir}")
    return 0 if summary.get("passed", 0) == summary.get("total_cases", 0) else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Deep Research Agent")
    parser.add_argument("--dataset", default=str(DATASET_PATH), help="Path to dataset JSON")
    parser.add_argument("--case", help="Run a single case by id")
    parser.add_argument("--limit", type=int, help="Max cases to run")
    parser.add_argument("--with-judge", action="store_true", help="Enable LLM judge scores")
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset only")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
