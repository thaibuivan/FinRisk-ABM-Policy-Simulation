# Live Multi-Agent Feasibility Pilot

## 1. Purpose

This pilot extends the previous token-only test into a small multi-agent loop. Four LLM roles interact with the same scenario state: customer agent, risky actor agent, analyst agent, and policy-maker agent. The policy-maker must select a policy, and the selected policy is compared against the best policy by simulated net benefit.

## 2. Summary

| run_id | provider | model | scenarios | rounds | llm_agent_roles | llm_calls | successful_calls | errors | total_tokens | total_cost_usd | avg_cost_per_call_usd | avg_latency_seconds_per_call | policy_decision_count | exact_best_policy_match_count | policy_selection_accuracy | avg_regret_vs_best | best_policy_by_net_benefit | best_policy_net_benefit | baseline_policy | baseline_policy_net_benefit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| groq_multi_agent_01 | groq | llama-3.1-8b-instant | baseline,stress_fraud | 2 | 4 | 16 | 11 | 5 | 7082 | 0.00038902 | 2.431e-05 | 0.58 | 2 | 0 | 0.0 | 8168.64 | balanced_threshold | 24295.57 | balanced_threshold | 24295.57 |

## 3. Policy-maker decisions

| scenario | round | selected_policy | selected_net_benefit | best_policy | best_net_benefit | regret_vs_best | baseline_policy | baseline_net_benefit | improvement_vs_baseline | token_cost_usd | net_value_vs_baseline_after_token_cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 1 | strict_threshold | 16126.93 | balanced_threshold | 24295.57 | 8168.64 | balanced_threshold | 24295.57 | -8168.64 | 2.786e-05 | -8168.640028 |
| baseline | 2 | strict_threshold | 16126.93 | balanced_threshold | 24295.57 | 8168.64 | balanced_threshold | 24295.57 | -8168.64 | 2.796e-05 | -8168.640028 |

## 4. Interpretation

Decision-value feasibility is not yet proven because policy selection did not consistently match the net-benefit optimum. A larger experiment should test more scenarios and compare hybrid/full LLM agents against the rule-based baseline.

This answers the supervisor's question more completely than token cost alone:

1. Technical feasibility: number of successful calls, latency, errors/rate-limit.
2. Cost feasibility: token usage and monetary cost.
3. Decision-value feasibility: whether the LLM policy-maker selects policies with high net benefit relative to the baseline and the simulated optimum.
