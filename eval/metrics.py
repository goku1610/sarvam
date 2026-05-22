"""Deterministic evaluation metrics for research agent outputs."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

CITATION_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
FORMAT_PATTERN = re.compile(r"\[[^\]]+—[^\]]+\]\(https?://[^)\s]+\)")

UNCERTAINTY_PHRASES = [
    "insufficient",
    "could not verify",
    "could not find",
    "limited evidence",
    "unclear",
    "uncertain",
    "not enough evidence",
    "unable to confirm",
    "no reliable",
    "cannot determine",
    "lack of data",
    "not publicly available",
    "weak evidence",
]

CONFLICT_PHRASES = [
    "disagree",
    "conflicting",
    "conflict",
    "sources differ",
    "mixed evidence",
    "on the other hand",
    "however, some",
    "contradict",
    "in contrast",
    "debate",
]

COMPARISON_KEYWORDS = [" vs ", " versus ", "compared", "comparison", "compared to"]


def extract_citations(answer: str) -> list[dict[str, str]]:
    citations = []
    for match in CITATION_PATTERN.finditer(answer):
        citations.append({
            "label": match.group(1).strip(),
            "url": match.group(2).strip().rstrip(".,;:"),
        })
    return citations


def domain_from_url(url: str) -> str:
    try:
        hostname = urlparse(url).hostname or ""
        return hostname.lower().removeprefix("www.")
    except ValueError:
        return ""


def has_uncertainty_language(answer: str) -> bool:
    lower = answer.lower()
    return any(phrase in lower for phrase in UNCERTAINTY_PHRASES)


def has_conflict_language(answer: str) -> bool:
    lower = answer.lower()
    return any(phrase in lower for phrase in CONFLICT_PHRASES)


def has_comparison_structure(answer: str) -> bool:
    lower = answer.lower()
    if "|" in answer and "---" in answer:
        return True
    return any(keyword in lower for keyword in COMPARISON_KEYWORDS)


def compute_metrics(
    case: dict[str, Any],
    answer: str,
    citation_validation: dict[str, Any],
    search_artifact: dict[str, Any],
    follow_up_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute deterministic metrics and category pass/fail for one case."""
    citations = extract_citations(answer)
    citation_count = len(citations)
    removed = int(citation_validation.get("removed_citation_count", 0) or 0)
    corrected = int(citation_validation.get("corrected_citation_count", 0) or 0)
    total_before_removal = citation_count + removed
    grounded_rate = (
        (total_before_removal - removed) / total_before_removal
        if total_before_removal > 0
        else 1.0
    )

    format_matches = len(FORMAT_PATTERN.findall(answer))
    format_compliance_rate = (
        format_matches / citation_count if citation_count > 0 else 0.0
    )

    cited_domains = {domain_from_url(c["url"]) for c in citations if domain_from_url(c["url"])}
    sources_retrieved = int(search_artifact.get("pages_count", 0) or 0)
    chunks_selected = int(search_artifact.get("chunks_count", 0) or 0)
    hop_count = int(search_artifact.get("hop_count", 0) or 0)

    uncertainty = has_uncertainty_language(answer)
    conflict = has_conflict_language(answer)
    comparison = has_comparison_structure(answer)

    expectations = case.get("expectations", {})
    category = case.get("category", "")
    failures: list[str] = []

    min_citations = int(expectations.get("min_citations", 0))
    if citation_count < min_citations:
        failures.append(f"citation_count {citation_count} < min {min_citations}")

    min_domains = int(expectations.get("min_unique_domains", 0))
    if len(cited_domains) < min_domains:
        failures.append(f"unique_domains {len(cited_domains)} < min {min_domains}")

    min_sources = int(expectations.get("min_sources_retrieved", 0))
    if sources_retrieved < min_sources:
        failures.append(f"sources_retrieved {sources_retrieved} < min {min_sources}")

    if expectations.get("requires_uncertainty_language") and not uncertainty:
        failures.append("missing uncertainty language")

    if expectations.get("requires_conflict_language"):
        if not conflict:
            failures.append("missing conflict language")
        if citation_count < 2:
            failures.append("conflict case needs >= 2 citations")

    if expectations.get("requires_comparison_structure") and not comparison:
        failures.append("missing comparison structure")

    if category == "multi_hop":
        if hop_count < 2 and sources_retrieved < 3:
            failures.append("multi_hop needs hop_count>=2 or sources>=3")

    if category == "multi_turn" and follow_up_artifact:
        if expectations.get("requires_follow_up_answer") and not follow_up_artifact.get("final_answer"):
            failures.append("missing follow-up answer")
        if expectations.get("requires_history_context"):
            if not follow_up_artifact.get("history_context_nonempty"):
                failures.append("follow-up missing history context")

    category_pass = len(failures) == 0

    return {
        "citation_count": citation_count,
        "grounded_citation_rate": round(grounded_rate, 3),
        "format_compliance_rate": round(format_compliance_rate, 3),
        "unique_domains_cited": len(cited_domains),
        "cited_domains": sorted(cited_domains),
        "sources_retrieved": sources_retrieved,
        "context_chunks_selected": chunks_selected,
        "hop_count": hop_count,
        "uncertainty_language": uncertainty,
        "conflict_language": conflict,
        "comparison_structure": comparison,
        "category_pass": category_pass,
        "failures": failures,
        "citation_validation": citation_validation,
    }
