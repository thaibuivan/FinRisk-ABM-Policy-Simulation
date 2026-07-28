from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "token_cost_feasibility_assumptions.json"
POLICY_PATH = ROOT / "data" / "policy_comparisons" / "policy_comparison_20260721_110642.csv"
SCENARIO_PATH = ROOT / "data" / "scenario_comparisons" / "scenario_comparison_20260721_100604.csv"
OUT_DIR = ROOT / "data" / "token_cost_feasibility"
REPORT_DIR = ROOT / "reports" / "feasibility"

SYSTEM_PROMPT = (
    "You are a research assistant inside a thesis experiment on transaction risk policy simulation. "
    "You must reason only from the supplied simulation metrics. Do not invent data. "
    "Return concise plain text. Focus on policy trade-offs: recall, precision, workload, overflow, false positive cost, fraud loss prevented, net benefit, and token cost feasibility."
)


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_config() -> Dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def model_pricing(config: Dict, model_name: str) -> Dict:
    for item in config["pricing_sources"]:
        if item["model"] == model_name:
            return item
    raise ValueError(f"Model pricing not found in config: {model_name}")


def estimate_tokens(text: str) -> int:
    # Conservative fallback for planning when API usage is unavailable.
    # English/Vietnamese mixed prompts are roughly 3.5-4 chars/token; using 4 is acceptable for dry-run only.
    return max(1, int(len(text) / 4))


def token_cost(input_tokens: int, output_tokens: int, cached_input_tokens: int, pricing: Dict) -> float:
    uncached_input = max(0, input_tokens - cached_input_tokens)
    return (
        uncached_input / 1_000_000 * pricing["input_usd_per_1m_tokens"]
        + cached_input_tokens / 1_000_000 * pricing["cached_input_usd_per_1m_tokens"]
        + output_tokens / 1_000_000 * pricing["output_usd_per_1m_tokens"]
    )


def scenario_summary(rows: List[Dict[str, str]], scenario_name: str) -> Optional[Dict[str, str]]:
    for row in rows:
        if row.get("scenario") == scenario_name:
            return row
    return rows[0] if rows else None


def policy_rows(rows: List[Dict[str, str]], cost_scenario: str = "base_cost") -> List[Dict[str, str]]:
    return [row for row in rows if row.get("cost_scenario") == cost_scenario]


def compact_policy_table(rows: Iterable[Dict[str, str]]) -> str:
    cols = ["policy_name", "precision_reviewed", "recall_reviewed", "analyst_reviewed", "review_overflow", "false_positive_cost", "analyst_cost", "net_benefit"]
    lines = ["policy_name | precision_reviewed | recall_reviewed | analyst_reviewed | overflow | false_positive_cost | analyst_cost | net_benefit"]
    for row in rows:
        lines.append(" | ".join(str(row.get(col, "")) for col in cols))
    return "\n".join(lines)


def build_policy_prompt(scenario: Dict[str, str], policies: List[Dict[str, str]], round_idx: int, replication: int) -> str:
    return f"""Role: policy-maker agent.

Task: choose the most reasonable transaction-risk review policy for this simulated environment. Explain the decision in 5-7 sentences.

Scenario metrics:
- scenario: {scenario.get('scenario')}
- fraud_rate: {scenario.get('fraud_rate')}
- transactions: {scenario.get('transactions')}
- fraud_count: {scenario.get('fraud_count')}
- analyst_capacity_per_day: {scenario.get('analyst_capacity_per_day')}
- baseline alerts_sent_to_analyst: {scenario.get('alerts_sent_to_analyst')}
- baseline analyst_reviewed: {scenario.get('analyst_reviewed')}
- baseline review_overflow: {scenario.get('review_overflow')}
- baseline net_benefit: {scenario.get('net_benefit')}

Policy comparison table:
{compact_policy_table(policies)}

Round: {round_idx}
Replication: {replication}

Please answer:
1. Which policy should be selected?
2. Why is it better under capacity/cost constraints?
3. What risk remains?
"""


def build_analyst_prompt(scenario: Dict[str, str], policies: List[Dict[str, str]], round_idx: int, replication: int) -> str:
    return f"""Role: fraud operations analyst agent.

Task: review the simulated workload pressure and explain whether the policy choice is operationally acceptable.

Scenario metrics:
- scenario: {scenario.get('scenario')}
- fraud_rate: {scenario.get('fraud_rate')}
- transactions: {scenario.get('transactions')}
- fraud_count: {scenario.get('fraud_count')}
- analyst_capacity_per_day: {scenario.get('analyst_capacity_per_day')}
- alerts_sent_to_analyst: {scenario.get('alerts_sent_to_analyst')}
- analyst_reviewed: {scenario.get('analyst_reviewed')}
- review_overflow: {scenario.get('review_overflow')}
- precision_flagged: {scenario.get('precision_flagged')}
- recall_flagged: {scenario.get('recall_flagged')}
- net_benefit: {scenario.get('net_benefit')}

Policy comparison table:
{compact_policy_table(policies)}

Round: {round_idx}
Replication: {replication}

Please answer:
1. Is workload manageable?
2. Which trade-off is most important for an analyst team?
3. What metric should be monitored next?
"""


def call_openai_chat(model: str, user_prompt: str, max_tokens: int, temperature: float) -> Dict[str, object]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Use --dry-run or set the key before live pilot.")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            latency = time.perf_counter() - started
            parsed = json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API HTTP {exc.code}: {body}") from exc

    usage = parsed.get("usage", {})
    content = parsed.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {
        "response_text": content,
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
        "cached_prompt_tokens": int((usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0),
        "latency_seconds": latency,
    }


def run_pilot(args: argparse.Namespace) -> List[Dict[str, object]]:
    config = load_config()
    pricing = model_pricing(config, args.model)
    scenario_rows = read_csv(SCENARIO_PATH)
    policies = policy_rows(read_csv(POLICY_PATH), args.cost_scenario)

    selected_scenarios = args.scenarios.split(",") if args.scenarios else ["baseline"]
    roles = ["policy_maker"] if args.architecture == "hybrid_policy_only" else ["analyst", "policy_maker"]
    rows: List[Dict[str, object]] = []

    for scenario_name in selected_scenarios:
        scenario = scenario_summary(scenario_rows, scenario_name.strip())
        if not scenario:
            raise ValueError("No scenario comparison rows available.")
        for replication in range(1, args.replications + 1):
            for round_idx in range(1, args.rounds + 1):
                for role in roles:
                    prompt = build_policy_prompt(scenario, policies, round_idx, replication) if role == "policy_maker" else build_analyst_prompt(scenario, policies, round_idx, replication)
                    full_input = SYSTEM_PROMPT + "\n\n" + prompt
                    started_at = datetime.now().isoformat(timespec="seconds")
                    error = ""
                    if args.dry_run:
                        prompt_tokens = estimate_tokens(full_input)
                        completion_tokens = args.estimated_output_tokens
                        cached_prompt_tokens = int(prompt_tokens * args.cache_ratio)
                        total_tokens = prompt_tokens + completion_tokens
                        latency_seconds = pricing["avg_latency_seconds_per_call"]
                        response_text = "DRY RUN: no API call. Replace with live output after running without --dry-run."
                    else:
                        try:
                            result = call_openai_chat(args.model, prompt, args.max_tokens, args.temperature)
                            prompt_tokens = int(result["prompt_tokens"])
                            completion_tokens = int(result["completion_tokens"])
                            total_tokens = int(result["total_tokens"])
                            cached_prompt_tokens = int(result["cached_prompt_tokens"])
                            latency_seconds = float(result["latency_seconds"])
                            response_text = str(result["response_text"])
                        except Exception as exc:  # write row and continue if requested
                            if not args.continue_on_error:
                                raise
                            prompt_tokens = estimate_tokens(full_input)
                            completion_tokens = 0
                            total_tokens = prompt_tokens
                            cached_prompt_tokens = 0
                            latency_seconds = 0.0
                            response_text = ""
                            error = str(exc)

                    cost = token_cost(prompt_tokens, completion_tokens, cached_prompt_tokens, pricing)
                    rows.append({
                        "run_id": args.run_id,
                        "dry_run": args.dry_run,
                        "started_at": started_at,
                        "scenario": scenario.get("scenario"),
                        "architecture": args.architecture,
                        "agent_role": role,
                        "round": round_idx,
                        "replication": replication,
                        "model": args.model,
                        "prompt_tokens": prompt_tokens,
                        "cached_prompt_tokens": cached_prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "latency_seconds": round(latency_seconds, 4),
                        "cost_usd": round(cost, 8),
                        "selected_policy_hint": "policy_maker_output" if role == "policy_maker" else "analyst_review_output",
                        "response_preview": response_text.replace("\n", " ")[:500],
                        "error": error,
                    })
    return rows


def summarize(rows: List[Dict[str, object]]) -> Dict[str, object]:
    total_calls = len(rows)
    total_prompt = sum(int(row["prompt_tokens"]) for row in rows)
    total_completion = sum(int(row["completion_tokens"]) for row in rows)
    total_tokens = sum(int(row["total_tokens"]) for row in rows)
    total_cost = sum(float(row["cost_usd"]) for row in rows)
    total_latency = sum(float(row["latency_seconds"]) for row in rows)
    avg_prompt = total_prompt / total_calls if total_calls else 0
    avg_completion = total_completion / total_calls if total_calls else 0
    avg_latency = total_latency / total_calls if total_calls else 0
    return {
        "llm_calls": total_calls,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 8),
        "avg_prompt_tokens_per_call": round(avg_prompt, 2),
        "avg_completion_tokens_per_call": round(avg_completion, 2),
        "avg_latency_seconds_per_call": round(avg_latency, 4),
    }


def write_report(path: Path, rows: List[Dict[str, object]], summary: Dict[str, object], args: argparse.Namespace) -> None:
    baseline = load_config()["baseline"]
    report = f"""# Empirical LLM Token Cost Pilot

## 1. Purpose

This pilot measures or dry-runs the token cost of adding LLM agents to the current rule-based ABM thesis framework.

- Architecture: `{args.architecture}`
- Model: `{args.model}`
- Dry run: `{args.dry_run}`
- Scenarios: `{args.scenarios}`
- Rounds: `{args.rounds}`
- Replications: `{args.replications}`

## 2. Summary

| Metric | Value |
| --- | ---: |
| LLM calls | {summary['llm_calls']} |
| Prompt tokens | {summary['prompt_tokens']} |
| Completion tokens | {summary['completion_tokens']} |
| Total tokens | {summary['total_tokens']} |
| Total cost USD | {summary['total_cost_usd']} |
| Avg prompt tokens/call | {summary['avg_prompt_tokens_per_call']} |
| Avg completion tokens/call | {summary['avg_completion_tokens_per_call']} |
| Avg latency seconds/call | {summary['avg_latency_seconds_per_call']} |

## 3. Break-even interpretation

Current baseline policy net benefit is `${baseline['policy_net_benefit_usd']:,.2f}` from `{baseline['source']}`.

For this pilot, the LLM extension needs to improve policy net benefit by at least `${summary['total_cost_usd']}` to cover token cost. This does not yet include engineering time or infrastructure cost.

## 4. Notes

- If `dry_run=True`, token counts are estimated from prompt length and must be replaced by live API usage.
- If `dry_run=False`, token counts come from API response usage fields.
- A stronger conclusion requires comparing whether LLM-assisted policy selection improves net benefit versus the rule-based baseline.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or dry-run an LLM token cost pilot for FinRisk ABM.")
    parser.add_argument("--run-id", default=datetime.now().strftime("pilot_%Y%m%d_%H%M%S"))
    parser.add_argument("--architecture", choices=["hybrid_policy_only", "hybrid_analyst_policy"], default="hybrid_analyst_policy")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--scenarios", default="baseline,stress_fraud")
    parser.add_argument("--cost-scenario", default="base_cost")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--replications", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true", help="Estimate tokens without calling the API.")
    parser.add_argument("--cache-ratio", type=float, default=0.0, help="Only used in dry-run estimates.")
    parser.add_argument("--estimated-output-tokens", type=int, default=260, help="Only used in dry-run estimates.")
    parser.add_argument("--max-tokens", type=int, default=350)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    rows = run_pilot(args)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / f"empirical_llm_pilot_{args.run_id}.csv"
    write_csv(csv_path, rows)
    summary = summarize(rows)
    summary_path = OUT_DIR / f"empirical_llm_pilot_{args.run_id}_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = REPORT_DIR / f"empirical_llm_pilot_{args.run_id}.md"
    write_report(report_path, rows, summary, args)
    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
