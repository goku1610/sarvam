# Evaluation Summary — 20260522_125751_04026f

**Evaluation mode:** deep research (max_hops=3)  
**Total cases:** 12  
**Passed:** 7  
**Pass rate:** 58.3%

## By category

| Category | Total | Passed | Pass rate | Avg grounded citations |
|----------|-------|--------|-----------|--------------------------|
| factual | 2 | 2 | 100.0% | 1.00 |
| multi_hop | 2 | 2 | 100.0% | 1.00 |
| comparison | 2 | 1 | 50.0% | 1.00 |
| insufficient_evidence | 2 | 0 | 0.0% | 1.00 |
| conflicting_sources | 2 | 0 | 0.0% | 1.00 |
| multi_turn | 2 | 2 | 100.0% | 1.00 |

## Per-case results

- **factual_capital_australia** [PASS] (21.49s)
- **factual_speed_of_light** [PASS] (44.84s)
- **multi_hop_oppenheimer_spouse** [PASS] (40.46s)
- **multi_hop_nobel_birthplace** [PASS] (15.64s)
- **comparison_react_vue** [PASS] (26.51s)
- **comparison_ev_hybrid** [FAIL] — citation_count 0 < min 2, unique_domains 0 < min 2 (34.35s)
- **insufficient_future_apple_project** [FAIL] — missing uncertainty language (33.73s)
- **insufficient_obscure_local** [FAIL] — missing uncertainty language (44.24s)
- **conflicting_coffee_health** [FAIL] — missing conflict language (21.64s)
- **conflicting_intermittent_fasting** [FAIL] — missing conflict language (70.61s)
- **multi_turn_summarize_sources** [PASS] (38.16s)
- **multi_turn_compare_followup** [PASS] (60.28s)
