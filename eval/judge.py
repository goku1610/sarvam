"""Optional LLM-as-judge for evaluation runs."""

from __future__ import annotations

import json
import re
from typing import Any

from google.genai import types


def judge_answer(
    planner: Any,
    query: str,
    answer: str,
    chunks: list[dict[str, Any]],
    category: str,
) -> dict[str, Any]:
    """Score grounding, usefulness, and uncertainty handling on a 1-5 scale."""
    source_catalog = [
        {
            "title": chunk.get("title", "Unknown"),
            "domain": chunk.get("domain", ""),
            "url": chunk.get("url", ""),
        }
        for chunk in chunks[:20]
    ]

    prompt = (
        "You are evaluating a deep research agent's answer. Score each dimension from 1 (poor) to 5 (excellent).\n"
        "Grounding: claims supported by the listed sources, citations align with evidence.\n"
        "Usefulness: answers the question clearly and completely for the category.\n"
        "Uncertainty handling: appropriately hedges when evidence is weak (especially for insufficient_evidence category).\n\n"
        "Respond only with valid JSON:\n"
        '{"grounding": 1, "usefulness": 1, "uncertainty_handling": 1, "rationale": "one paragraph"}\n\n'
        f"Category: {category}\n"
        f"Question: {query}\n"
        f"Source catalog: {json.dumps(source_catalog, indent=2)}\n\n"
        f"Answer (excerpt):\n{answer[:5000]}"
    )

    try:
        response = planner.client.models.generate_content(
            model=planner.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                temperature=0.1,
            ),
        )
        raw = (response.text or "{}").strip()
        if raw.startswith("{"):
            parsed = json.loads(raw)
        else:
            match = re.search(r"\{[\s\S]*\}", raw)
            parsed = json.loads(match.group(0)) if match else {}

        for key in ("grounding", "usefulness", "uncertainty_handling"):
            val = int(parsed.get(key, 3))
            parsed[key] = max(1, min(5, val))
        parsed["rationale"] = str(parsed.get("rationale", "")).strip()
        parsed["judge_available"] = True
        return parsed
    except Exception as error:
        return {
            "grounding": None,
            "usefulness": None,
            "uncertainty_handling": None,
            "rationale": str(error),
            "judge_available": False,
        }
