# Empirical LLM Token Cost Pilot

## 1. Purpose

This pilot measures or dry-runs the token cost of adding LLM agents to the current rule-based ABM thesis framework.

- Architecture: `hybrid_analyst_policy`
- Model: `gpt-4o-mini`
- Dry run: `True`
- Scenarios: `baseline,stress_fraud`
- Rounds: `2`
- Replications: `1`

## 2. Summary

| Metric | Value |
| --- | ---: |
| LLM calls | 8 |
| Prompt tokens | 3004 |
| Completion tokens | 2080 |
| Total tokens | 5084 |
| Total cost USD | 0.0016986 |
| Avg prompt tokens/call | 375.5 |
| Avg completion tokens/call | 260.0 |
| Avg latency seconds/call | 1.2 |

## 3. Break-even interpretation

Current baseline policy net benefit is `$24,295.57` from `data/policy_comparisons/policy_comparison_20260721_110642.csv`.

For this pilot, the LLM extension needs to improve policy net benefit by at least `$0.0016986` to cover token cost. This does not yet include engineering time or infrastructure cost.

## 4. Notes

- If `dry_run=True`, token counts are estimated from prompt length and must be replaced by live API usage.
- If `dry_run=False`, token counts come from API response usage fields.
- A stronger conclusion requires comparing whether LLM-assisted policy selection improves net benefit versus the rule-based baseline.
