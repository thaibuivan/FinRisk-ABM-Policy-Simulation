# Groq Live Pilot 03: Empirical Token Cost and Scale-up

## 1. What was measured

This is a real API pilot using Groq `llama-3.1-8b-instant`, not a dry-run estimate.

- Scenarios: baseline, stress_fraud
- Architecture: hybrid_analyst_policy
- LLM roles: analyst and policy-maker
- Rounds: 2
- Replications: 1
- Total successful calls: 8
- Errors / rate-limit events: 0

## 2. Empirical usage summary

| Metric | Value |
| --- | ---: |
| Prompt tokens | 4024 |
| Completion tokens | 1353 |
| Total tokens | 5377 |
| Total cost USD | 0.00030944 |
| Avg tokens per call | 672.12 |
| Avg cost per call USD | 0.00003868 |
| Avg latency seconds per call | 1.1137 |

## 3. Scale-up from empirical averages

The scale-up below uses measured average cost/tokens/latency from the pilot. The thesis-batch assumption is 5 rounds, 3 replications, and 2 LLM roles per scenario, equivalent to 30 LLM calls per scenario.

| scale | scenarios | llm_calls | estimated_tokens | estimated_cost_usd | sequential_latency_minutes | parallel_by_round_latency_minutes |
| --- | --- | --- | --- | --- | --- | --- |
| pilot_actual | 2 | 8 | 5377.0 | 0.000309 | 0.15 | 0.07 |
| small_thesis_batch | 100 | 3000 | 2016375.0 | 0.11604 | 55.68 | 27.84 |
| medium_thesis_batch | 1000 | 30000 | 20163750.0 | 1.1604 | 556.85 | 278.43 |
| large_research_batch | 10000 | 300000 | 201637500.0 | 11.604 | 5568.5 | 2784.25 |

## 4. Interpretation

The measured token cost is much lower than the earlier OpenAI-based estimate because this pilot used Groq `llama-3.1-8b-instant`, whose token price is lower and whose responses were relatively short. Under the measured average, a 1,000-scenario hybrid analyst-policy experiment would cost roughly `$1.1604` in token usage.

The more important constraint is likely not monetary cost, but experiment design and request limits. The pilot had no rate-limit errors, but larger runs should still be batched, logged, and possibly slowed down.

## 5. Feasibility conclusion

For a small-to-medium thesis experiment, hybrid LLM multi-agent simulation appears technically and economically feasible with Groq under the current pilot assumptions. However, this does not prove that LLM agents improve policy quality. The next research step is to test whether LLM-assisted analyst/policy-maker agents select policies with higher net benefit or provide better decision explanations than the rule-based baseline.
