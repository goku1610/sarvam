# Evaluation Harness

This directory contains the Part 3 evaluation setup for the Deep Research Agent.

**All evaluation runs use deep research mode only** (`deep_research=True`, `max_hops=3`): multi-hop search, broader query plans, comprehensive answers with gap refinement, and larger context windows. Fast/single-hop mode is not used for scoring.

## What we measure

| Metric | Rationale |
|--------|-----------|
| `grounded_citation_rate` | Citations must map to URLs from retrieved chunks — core grounding requirement |
| `format_compliance_rate` | Answers should use `[Title — domain](URL)` per assignment spec |
| `citation_count` / `unique_domains_cited` | Claim-heavy answers need sources with diversity |
| `sources_retrieved` / `hop_count` | Deep research search and multi-hop pipeline actually ran |
| `uncertainty_language` | Insufficient-evidence cases should hedge, not hallucinate |
| `conflict_language` | Conflicting-source cases should note disagreement and cite multiple sides |
| `comparison_structure` | Comparison cases should use tables or explicit compare language |
| `category_pass` | Per-case expectations from the dataset |

Optional `--with-judge` adds LLM scores (1–5) for grounding, usefulness, and uncertainty handling.

## Dataset

[`dataset.json`](dataset.json) includes 12 cases (all `deep_research: true`):

- **factual** (2): single verifiable facts
- **multi_hop** (2): chained reasoning (director → spouse, Nobel → birthplace)
- **comparison** (2): React vs Vue, EV vs hybrid
- **insufficient_evidence** (2): unknowable or future data
- **conflicting_sources** (2): coffee & heart health, intermittent fasting
- **multi_turn** (2): follow-up using session history after an initial deep research pass

## Run

From the repo root, with `.env` containing `TAVILY_API_KEY` and `GEMINI_API_KEY`:

```bash
# Validate dataset only
python -m eval.run_eval --dry-run

# Smoke eval (2 cases, deep research)
python -m eval.run_eval --limit 2

# Full evaluation (all 12 cases, deep research)
python -m eval.run_eval

# Single case
python -m eval.run_eval --case factual_capital_australia

# With LLM judge (extra Gemini calls)
python -m eval.run_eval --limit 3 --with-judge
```

Outputs are written to `eval/results/<run_id>/`:

- `cases/<id>.json` — full artifacts per question
- `summary.json` — aggregate metrics (`mode: deep_research`, `max_hops: 3`)
- `summary.md` — human-readable report for README/PDF

Eval sessions are stored separately in `data/eval_sessions.json` (not production UI sessions).

## Limitations

- Web search results are non-deterministic; re-runs may differ.
- No golden reference answers — we use structural and grounding checks, not automatic correctness labels.
- Live API calls are required (Tavily + Gemini); deep research runs are slower (~3–8 minutes per case).
- LLM judge scores are subjective; use for qualitative review, not as sole pass/fail.

## Architecture

The harness calls [`agent_pipeline.py`](../agent_pipeline.py) — the same Plan → Search → Answer path used by the FastAPI app in deep research mode — so evaluation reflects real deep research behavior.
