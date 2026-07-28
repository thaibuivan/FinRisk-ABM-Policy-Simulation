from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "token_cost_feasibility_assumptions.json"
OUT_DIR = ROOT / "data" / "token_cost_feasibility"
REPORT_DIR = ROOT / "reports" / "feasibility"


def load_config() -> Dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def llm_calls(scale: Dict, architecture: Dict) -> int:
    return int(
        scale["scenarios"]
        * scale["rounds_per_scenario"]
        * scale["replications"]
        * architecture["llm_agents"]
        * architecture["calls_per_agent_round"]
    )


def token_cost_usd(input_tokens: float, output_tokens: float, cache_ratio: float, model: Dict) -> float:
    cached_input = input_tokens * cache_ratio
    uncached_input = input_tokens - cached_input
    return (
        uncached_input / 1_000_000 * model["input_usd_per_1m_tokens"]
        + cached_input / 1_000_000 * model["cached_input_usd_per_1m_tokens"]
        + output_tokens / 1_000_000 * model["output_usd_per_1m_tokens"]
    )


def format_money(value: float) -> str:
    return f"${value:,.4f}"


def estimate_rows(config: Dict) -> List[Dict]:
    baseline_benefit = float(config["baseline"]["policy_net_benefit_usd"])
    rows: List[Dict] = []
    for scale in config["experiment_scales"]:
        rounds_batches = scale["scenarios"] * scale["rounds_per_scenario"] * scale["replications"]
        for arch in config["architectures"]:
            calls = llm_calls(scale, arch)
            input_tokens = calls * arch["avg_input_tokens_per_call"]
            output_tokens = calls * arch["avg_output_tokens_per_call"]
            total_tokens = input_tokens + output_tokens
            for model in config["pricing_sources"]:
                for cache_ratio in config["cache_ratios"]:
                    cost = token_cost_usd(input_tokens, output_tokens, cache_ratio, model)
                    sequential_latency_seconds = calls * model["avg_latency_seconds_per_call"]
                    parallel_by_round_seconds = 0 if arch["llm_agents"] == 0 else rounds_batches * model["avg_latency_seconds_per_call"]
                    break_even_pct = 0.0 if baseline_benefit == 0 else cost / baseline_benefit
                    low_improvement = baseline_benefit * arch["expected_policy_improvement_pct_low"]
                    mid_improvement = baseline_benefit * arch["expected_policy_improvement_pct_mid"]
                    high_improvement = baseline_benefit * arch["expected_policy_improvement_pct_high"]
                    rows.append({
                        "scale": scale["name"],
                        "scenarios": scale["scenarios"],
                        "rounds_per_scenario": scale["rounds_per_scenario"],
                        "replications": scale["replications"],
                        "architecture": arch["name"],
                        "model": model["model"],
                        "cache_ratio": cache_ratio,
                        "llm_calls": calls,
                        "input_tokens": round(input_tokens, 2),
                        "output_tokens": round(output_tokens, 2),
                        "total_tokens": round(total_tokens, 2),
                        "token_cost_usd": round(cost, 6),
                        "cost_per_scenario_usd": round(cost / scale["scenarios"], 6) if scale["scenarios"] else 0,
                        "sequential_latency_minutes": round(sequential_latency_seconds / 60, 2),
                        "parallel_by_round_latency_minutes": round(parallel_by_round_seconds / 60, 2),
                        "break_even_improvement_usd": round(cost, 6),
                        "break_even_improvement_pct_of_baseline_net_benefit": round(break_even_pct, 8),
                        "expected_improvement_low_usd": round(low_improvement, 2),
                        "expected_improvement_mid_usd": round(mid_improvement, 2),
                        "expected_improvement_high_usd": round(high_improvement, 2),
                        "net_value_low_usd": round(low_improvement - cost, 2),
                        "net_value_mid_usd": round(mid_improvement - cost, 2),
                        "net_value_high_usd": round(high_improvement - cost, 2),
                    })
    return rows


def write_csv(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: Iterable[Dict], columns: List[str]) -> str:
    rows = list(rows)
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(str(row[col]) for col in columns) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def create_pilot_template(path: Path) -> None:
    rows = [
        {
            "run_id": "pilot_001",
            "scenario": "baseline",
            "architecture": "hybrid_analyst_policy",
            "agent_role": "policy_maker",
            "round": 1,
            "model": "gpt-4o-mini",
            "prompt_tokens": "",
            "cached_prompt_tokens": "",
            "completion_tokens": "",
            "total_tokens": "",
            "latency_seconds": "",
            "cost_usd": "",
            "selected_policy": "",
            "policy_net_benefit_usd": "",
            "notes": "Fill from API usage or LangSmith trace after empirical pilot",
        }
    ]
    write_csv(path, rows)


def create_report(config: Dict, rows: List[Dict]) -> str:
    baseline = config["baseline"]
    pilot_focus = [
        row for row in rows
        if row["scale"] in {"pilot", "small_thesis_batch", "medium_thesis_batch"}
        and row["model"] == "gpt-4o-mini"
        and row["cache_ratio"] == 0.5
        and row["architecture"] in {"rule_based_abm", "hybrid_policy_only", "hybrid_analyst_policy", "full_llm_abm"}
    ]
    gpt4o_focus = [
        row for row in rows
        if row["scale"] == "medium_thesis_batch"
        and row["cache_ratio"] == 0.5
        and row["architecture"] in {"hybrid_analyst_policy", "full_llm_abm"}
    ]
    cols = [
        "scale",
        "architecture",
        "model",
        "llm_calls",
        "total_tokens",
        "token_cost_usd",
        "cost_per_scenario_usd",
        "parallel_by_round_latency_minutes",
        "break_even_improvement_pct_of_baseline_net_benefit",
    ]
    source_lines = "\n".join(
        f"- {m['model']}: input ${m['input_usd_per_1m_tokens']}/1M, cached input ${m['cached_input_usd_per_1m_tokens']}/1M, output ${m['output_usd_per_1m_tokens']}/1M. Source: {m['source_url']}"
        for m in config["pricing_sources"]
    )
    return f"""# Token Cost Feasibility for Hybrid LLM Multi-Agent Simulation

## 1. Why this analysis matters

The submitted thesis prototype is a rule-based Agent-Based Model (ABM). It does not use LLM tokens. If the thesis is extended toward LLM/hybrid multi-agent simulation, the first question is not whether the API can run, but whether the extra LLM cost and latency are justified by better policy decisions.

Core feasibility condition:

`LLM simulation net value = improvement in policy net benefit - token cost`

The LLM extension is economically feasible only if the improvement in policy net benefit is larger than the token cost, while latency remains acceptable for repeated experiments.

## 2. Baseline

- Baseline architecture: `{baseline['architecture']}`
- Baseline policy: `{baseline['policy']}`
- Cost scenario: `{baseline['cost_scenario']}`
- Baseline policy net benefit: `${baseline['policy_net_benefit_usd']:,.2f}`
- Source: `{baseline['source']}`

This baseline is important because token cost alone does not prove feasibility. We compare token cost against the value of selecting a better policy.

## 3. Model pricing assumptions

{source_lines}

Prices are current assumptions for feasibility analysis and should be rechecked before final thesis experiments.

## 4. Architectures compared

- `rule_based_abm`: current baseline, no LLM calls.
- `hybrid_policy_only`: only the policy-maker uses LLM to interpret simulation outcomes and select/explain policy.
- `hybrid_analyst_policy`: analyst and policy-maker use LLM; customer/fraud/system behavior remains rule-based.
- `full_llm_abm`: multiple agents use LLM reasoning.

## 5. Main estimate: GPT-4o mini with 50% cached input

{markdown_table(pilot_focus, cols)}

## 6. Sensitivity: GPT-4o mini vs GPT-4o at 1,000 scenarios

{markdown_table(gpt4o_focus, cols)}

## 7. Interpretation

At the current assumed token sizes, GPT-4o mini makes the token cost small even for 1,000 scenarios. The larger concern is not direct token spend, but experiment design quality: whether LLM agents produce better policy selection, more realistic behavioral adaptation, or clearer decision explanations than the rule-based baseline.

Full LLM ABM is more expensive and slower because every simulated round requires more LLM calls. The safer research path is hybrid: keep high-volume customer/fraud/system behavior rule-based, and use LLM only for roles where language reasoning is useful, such as analyst interpretation and policy-maker explanation.

## 8. What still needs empirical measurement

This report is still an estimate. To conclude more rigorously, the next step is an empirical pilot with API/LangSmith logs:

1. Run 20-50 LLM calls under the `hybrid_analyst_policy` architecture.
2. Record prompt tokens, cached tokens, completion tokens, latency, and selected policy.
3. Replace the estimated token assumptions with measured averages.
4. Compare whether hybrid LLM selects a policy with higher net benefit than the rule-based baseline.
5. Conclude feasibility using: `policy improvement > token cost`.

## 9. Preliminary conclusion

The estimated cost suggests that hybrid LLM multi-agent simulation is technically affordable, especially with GPT-4o mini. However, the research claim should not be “LLM is cheap, so use it.” The stronger claim is: hybrid LLM is feasible only if it improves policy selection or interpretation enough to exceed its token and latency cost.
"""


def main() -> None:
    config = load_config()
    rows = estimate_rows(config)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "token_cost_architecture_model_comparison.csv", rows)
    # Backward-compatible concise output used by earlier notes.
    concise_cols = [
        "scale", "architecture", "model", "cache_ratio", "llm_calls", "total_tokens",
        "token_cost_usd", "cost_per_scenario_usd", "break_even_improvement_pct_of_baseline_net_benefit"
    ]
    concise_rows = [
        {k: row[k] for k in concise_cols}
        for row in rows
        if row["model"] == "gpt-4o-mini" and row["cache_ratio"] == 0.5
    ]
    write_csv(OUT_DIR / "token_cost_architecture_comparison.csv", concise_rows)
    create_pilot_template(OUT_DIR / "llm_pilot_usage_template.csv")
    report = create_report(config, rows)
    (REPORT_DIR / "token_cost_feasibility.md").write_text(report, encoding="utf-8-sig")
    print("Wrote token cost feasibility outputs")


if __name__ == "__main__":
    main()
