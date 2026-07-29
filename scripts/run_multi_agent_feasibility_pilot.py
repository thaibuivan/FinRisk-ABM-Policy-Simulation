from __future__ import annotations

import argparse
import csv
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import certifi

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "token_cost_feasibility_assumptions.json"
POLICY_PATH = ROOT / "data" / "policy_comparisons" / "policy_comparison_20260721_110642.csv"
SCENARIO_PATH = ROOT / "data" / "scenario_comparisons" / "scenario_comparison_20260721_100604.csv"
OUT_DIR = ROOT / "data" / "token_cost_feasibility"
REPORT_DIR = ROOT / "reports" / "feasibility"

POLICY_NAMES = [
    "balanced_threshold",
    "sensitive_threshold",
    "strict_threshold",
    "capacity_aware",
    "cost_sensitive",
]

SYSTEM_PROMPT = (
    "You are part of a thesis pilot on multi-agent simulation for transaction risk policy design. "
    "Use only the supplied simulation state and policy metrics. Do not invent data. "
    "The research objective is feasibility analysis, not automated enforcement. "
    "If you are policy_maker, choose the policy that maximizes simulated net_benefit first; "
    "use recall, false positives, and overflow only as tie-breakers or operational explanations. "
    "If you are policy_maker, you must include exactly one line: Selected policy: <policy_name>."
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


def model_pricing(config: Dict, model_name: str, provider: str) -> Dict:
    for item in config["pricing_sources"]:
        if item["model"] == model_name and item.get("provider", "openai") == provider:
            return item
    for item in config["pricing_sources"]:
        if item["model"] == model_name:
            return item
    raise ValueError(f"Model pricing not found: {provider}/{model_name}")


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
    return None


def policy_rows(rows: List[Dict[str, str]], cost_scenario: str = "base_cost") -> List[Dict[str, str]]:
    return [row for row in rows if row.get("cost_scenario") == cost_scenario]


def fnum(value: object, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def best_policy_by_net_benefit(policies: List[Dict[str, str]]) -> Dict[str, str]:
    return max(policies, key=lambda row: fnum(row.get("net_benefit")))


def policy_by_name(policies: List[Dict[str, str]], name: str) -> Optional[Dict[str, str]]:
    normalized = name.strip().lower()
    for row in policies:
        if row.get("policy_name", "").strip().lower() == normalized:
            return row
    return None


def compact_policy_table(rows: Iterable[Dict[str, str]]) -> str:
    lines = ["policy_name | precision_reviewed | recall_reviewed | analyst_reviewed | overflow | false_positive_cost | analyst_cost | net_benefit"]
    for row in rows:
        lines.append(
            " | ".join([
                str(row.get("policy_name", "")),
                str(row.get("precision_reviewed", "")),
                str(row.get("recall_reviewed", "")),
                str(row.get("analyst_reviewed", "")),
                str(row.get("review_overflow", "")),
                str(row.get("false_positive_cost", "")),
                str(row.get("analyst_cost", "")),
                str(row.get("net_benefit", "")),
            ])
        )
    return "\n".join(lines)


def parse_selected_policy(text: str) -> str:
    match = re.search(r"selected\s+policy\s*:\s*([A-Za-z0-9_\-]+)", text, flags=re.IGNORECASE)
    if match:
        candidate = match.group(1).strip()
        for name in POLICY_NAMES:
            if candidate.lower() == name.lower():
                return name
    lowered = text.lower()
    for name in POLICY_NAMES:
        if name.lower() in lowered:
            return name
    return "unparsed"


def call_llm(
    provider: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    max_retries: int = 2,
    retry_backoff_seconds: float = 3.0,
) -> Dict[str, object]:
    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY")
        endpoint = "https://api.groq.com/openai/v1/chat/completions"
        missing = "GROQ_API_KEY is not set."
    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        endpoint = "https://api.openai.com/v1/chat/completions"
        missing = "OPENAI_API_KEY is not set."
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    if not api_key:
        raise RuntimeError(missing)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "FinRisk-ABM-Policy-Simulation/0.1",
        },
        method="POST",
    )
    context = ssl.create_default_context(cafile=certifi.where())
    started = time.perf_counter()
    parsed = None
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60, context=context) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"LLM API HTTP {exc.code}: {body}")
            if exc.code not in {408, 409, 425, 429, 500, 502, 503, 504} or attempt >= max_retries:
                raise last_error from exc
            time.sleep(retry_backoff_seconds * (attempt + 1))
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = RuntimeError(f"LLM API network error: {exc}")
            if attempt >= max_retries:
                raise last_error from exc
            time.sleep(retry_backoff_seconds * (attempt + 1))
    if parsed is None:
        raise last_error or RuntimeError("LLM API returned no response")
    latency = time.perf_counter() - started
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


def build_state(scenario: Dict[str, str], selected_policy: str) -> Dict[str, object]:
    return {
        "scenario": scenario.get("scenario"),
        "fraud_rate": fnum(scenario.get("fraud_rate")),
        "transactions": fnum(scenario.get("transactions")),
        "fraud_count": fnum(scenario.get("fraud_count")),
        "analyst_capacity_per_day": fnum(scenario.get("analyst_capacity_per_day")),
        "alerts_sent_to_analyst": fnum(scenario.get("alerts_sent_to_analyst")),
        "analyst_reviewed": fnum(scenario.get("analyst_reviewed")),
        "review_overflow": fnum(scenario.get("review_overflow")),
        "precision_flagged": fnum(scenario.get("precision_flagged")),
        "recall_flagged": fnum(scenario.get("recall_flagged")),
        "net_benefit": fnum(scenario.get("net_benefit")),
        "current_policy": selected_policy,
        "fraud_adaptation_level": 0.0,
        "customer_friction_index": 0.0,
        "analyst_backlog_pressure": fnum(scenario.get("review_overflow")),
    }


def update_state_after_policy(state: Dict[str, object], selected_policy: str, policy: Optional[Dict[str, str]]) -> None:
    state["current_policy"] = selected_policy
    if not policy:
        return
    overflow = fnum(policy.get("review_overflow"))
    fp_cost = fnum(policy.get("false_positive_cost"))
    recall = fnum(policy.get("recall_reviewed"))
    alerts = fnum(policy.get("alerts_sent_to_analyst"))
    state["analyst_backlog_pressure"] = overflow
    state["customer_friction_index"] = round(fp_cost / 10_000, 4)
    # Simple state update for this pilot: more sensitive policies and high recall create more adversarial adaptation pressure.
    state["fraud_adaptation_level"] = round(min(1.0, max(0.0, recall + alerts / 20_000)), 4)


def prompt_for_role(role: str, state: Dict[str, object], policies: List[Dict[str, str]], round_idx: int) -> str:
    policy_table = compact_policy_table(policies)
    state_json = json.dumps(state, ensure_ascii=False, indent=2)
    if role == "customer_agent":
        task = "Explain how legitimate customers would react to the current policy friction. Mention whether friction is acceptable."
    elif role == "risky_actor_agent":
        task = "Explain how a strategic risky actor might adapt if this policy is used. Do not provide actionable fraud instructions; stay at a high-level risk-policy perspective."
    elif role == "analyst_agent":
        task = "Assess whether analyst workload is manageable and which operational metric is most concerning."
    elif role == "policy_maker_agent":
        task = (
            "Choose one policy from the table. Primary rule: select the policy with the highest net_benefit. "
            "Then explain the trade-off using recall_reviewed, precision_reviewed, false_positive_cost, analyst_reviewed, "
            "and review_overflow. Include exactly one line: Selected policy: <policy_name>."
        )
    else:
        raise ValueError(role)
    return f"""Role: {role}
Round: {round_idx}

Current simulation state:
{state_json}

Available policy metrics:
{policy_table}

Task: {task}
"""


def run(args: argparse.Namespace) -> Dict[str, object]:
    config = load_config()
    pricing = model_pricing(config, args.model, args.provider)
    scenario_rows = read_csv(SCENARIO_PATH)
    policies = policy_rows(read_csv(POLICY_PATH), args.cost_scenario)
    best_policy = best_policy_by_net_benefit(policies)
    best_policy_name = best_policy.get("policy_name", "")
    best_net_benefit = fnum(best_policy.get("net_benefit"))
    baseline_policy = policy_by_name(policies, args.baseline_policy)
    baseline_net_benefit = fnum(baseline_policy.get("net_benefit")) if baseline_policy else 0.0

    roles = ["customer_agent", "risky_actor_agent", "analyst_agent", "policy_maker_agent"]
    outputs: List[Dict[str, object]] = []
    decisions: List[Dict[str, object]] = []

    for scenario_name in [s.strip() for s in args.scenarios.split(",") if s.strip()]:
        scenario = scenario_summary(scenario_rows, scenario_name)
        if not scenario:
            raise ValueError(f"Scenario not found: {scenario_name}")
        state = build_state(scenario, args.baseline_policy)
        for round_idx in range(1, args.rounds + 1):
            for role in roles:
                prompt = prompt_for_role(role, state, policies, round_idx)
                error = ""
                try:
                    result = call_llm(
                        args.provider,
                        args.model,
                        prompt,
                        args.max_tokens,
                        args.temperature,
                        args.max_retries,
                        args.retry_backoff_seconds,
                    )
                except Exception as exc:
                    if not args.continue_on_error:
                        raise
                    result = {
                        "response_text": "",
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cached_prompt_tokens": 0,
                        "latency_seconds": 0.0,
                    }
                    error = str(exc)
                cost = 0.0 if error else token_cost(
                    int(result["prompt_tokens"]),
                    int(result["completion_tokens"]),
                    int(result["cached_prompt_tokens"]),
                    pricing,
                )
                selected_policy = ""
                selected_net_benefit = ""
                regret = ""
                improvement_vs_baseline = ""
                net_value_vs_baseline = ""
                if role == "policy_maker_agent" and not error:
                    selected_policy = parse_selected_policy(str(result["response_text"]))
                    selected_row = policy_by_name(policies, selected_policy)
                    if selected_row:
                        selected_nb = fnum(selected_row.get("net_benefit"))
                        selected_net_benefit = round(selected_nb, 2)
                        regret = round(best_net_benefit - selected_nb, 2)
                        improvement = selected_nb - baseline_net_benefit
                        improvement_vs_baseline = round(improvement, 2)
                        net_value_vs_baseline = round(improvement - cost, 6)
                        update_state_after_policy(state, selected_policy, selected_row)
                    decisions.append({
                        "scenario": scenario_name,
                        "round": round_idx,
                        "selected_policy": selected_policy,
                        "selected_net_benefit": selected_net_benefit,
                        "best_policy": best_policy_name,
                        "best_net_benefit": round(best_net_benefit, 2),
                        "regret_vs_best": regret,
                        "baseline_policy": args.baseline_policy,
                        "baseline_net_benefit": round(baseline_net_benefit, 2),
                        "improvement_vs_baseline": improvement_vs_baseline,
                        "token_cost_usd": round(cost, 8),
                        "net_value_vs_baseline_after_token_cost": net_value_vs_baseline,
                    })
                outputs.append({
                    "run_id": args.run_id,
                    "started_at": datetime.now().isoformat(timespec="seconds"),
                    "provider": args.provider,
                    "model": args.model,
                    "scenario": scenario_name,
                    "round": round_idx,
                    "agent_role": role,
                    "prompt_tokens": int(result["prompt_tokens"]),
                    "cached_prompt_tokens": int(result["cached_prompt_tokens"]),
                    "completion_tokens": int(result["completion_tokens"]),
                    "total_tokens": int(result["total_tokens"]),
                    "latency_seconds": round(float(result["latency_seconds"]), 4),
                    "cost_usd": round(cost, 8),
                    "selected_policy": selected_policy,
                    "selected_net_benefit": selected_net_benefit,
                    "regret_vs_best": regret,
                    "improvement_vs_baseline": improvement_vs_baseline,
                    "net_value_vs_baseline_after_token_cost": net_value_vs_baseline,
                    "response_preview": str(result["response_text"]).replace("\n", " ")[:700],
                    "error": error,
                })
                if args.sleep_seconds > 0:
                    time.sleep(args.sleep_seconds)
    total_cost = sum(fnum(r["cost_usd"]) for r in outputs)
    total_tokens = sum(int(r["total_tokens"]) for r in outputs)
    total_latency = sum(fnum(r["latency_seconds"]) for r in outputs)
    successful_calls = len([r for r in outputs if not r["error"]])
    policy_decisions = [d for d in decisions if d.get("selected_policy")]
    exact_best = len([d for d in policy_decisions if d["selected_policy"] == d["best_policy"]])
    avg_regret = sum(fnum(d.get("regret_vs_best")) for d in policy_decisions) / len(policy_decisions) if policy_decisions else 0.0
    summary = {
        "run_id": args.run_id,
        "provider": args.provider,
        "model": args.model,
        "scenarios": args.scenarios,
        "rounds": args.rounds,
        "llm_agent_roles": len(roles),
        "llm_calls": len(outputs),
        "successful_calls": successful_calls,
        "errors": len(outputs) - successful_calls,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 8),
        "avg_cost_per_call_usd": round(total_cost / len(outputs), 8) if outputs else 0.0,
        "avg_latency_seconds_per_call": round(total_latency / successful_calls, 4) if successful_calls else 0.0,
        "policy_decision_count": len(policy_decisions),
        "exact_best_policy_match_count": exact_best,
        "policy_selection_accuracy": round(exact_best / len(policy_decisions), 4) if policy_decisions else 0.0,
        "avg_regret_vs_best": round(avg_regret, 4),
        "best_policy_by_net_benefit": best_policy_name,
        "best_policy_net_benefit": round(best_net_benefit, 2),
        "baseline_policy": args.baseline_policy,
        "baseline_policy_net_benefit": round(baseline_net_benefit, 2),
    }
    return {"outputs": outputs, "decisions": decisions, "summary": summary}


def markdown_table(rows: List[Dict[str, object]]) -> str:
    if not rows:
        return "No rows."
    cols = list(rows[0].keys())
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |")
    return "\n".join(lines)


def write_report(path: Path, summary: Dict[str, object], decisions: List[Dict[str, object]]) -> None:
    conclusion = ""
    if summary["errors"] == 0 and summary["total_cost_usd"] < 0.01:
        conclusion += "The live multi-agent pilot is technically feasible at small scale: all calls succeeded, latency was low, and token cost was negligible. "
    if summary["policy_selection_accuracy"] >= 0.5:
        conclusion += "It also shows early decision-value feasibility because the LLM policy-maker frequently selected the policy with the highest simulated net benefit. "
    else:
        conclusion += "Decision-value feasibility is not yet proven because policy selection did not consistently match the net-benefit optimum. "
    conclusion += "A larger experiment should test more scenarios and compare hybrid/full LLM agents against the rule-based baseline."
    report = f"""# Live Multi-Agent Feasibility Pilot

## 1. Purpose

This pilot extends the previous token-only test into a small multi-agent loop. Four LLM roles interact with the same scenario state: customer agent, risky actor agent, analyst agent, and policy-maker agent. The policy-maker must select a policy, and the selected policy is compared against the best policy by simulated net benefit.

## 2. Summary

{markdown_table([summary])}

## 3. Policy-maker decisions

{markdown_table(decisions)}

## 4. Interpretation

{conclusion}

This answers the supervisor's question more completely than token cost alone:

1. Technical feasibility: number of successful calls, latency, errors/rate-limit.
2. Cost feasibility: token usage and monetary cost.
3. Decision-value feasibility: whether the LLM policy-maker selects policies with high net benefit relative to the baseline and the simulated optimum.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small live multi-agent feasibility pilot.")
    parser.add_argument("--run-id", default=datetime.now().strftime("multi_agent_%Y%m%d_%H%M%S"))
    parser.add_argument("--provider", choices=["groq", "openai"], default="groq")
    parser.add_argument("--model", default="llama-3.1-8b-instant")
    parser.add_argument("--scenarios", default="baseline,stress_fraud")
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--cost-scenario", default="base_cost")
    parser.add_argument("--baseline-policy", default="balanced_threshold")
    parser.add_argument("--max-tokens", type=int, default=260)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--retry-backoff-seconds", type=float, default=3.0)
    args = parser.parse_args()

    result = run(args)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / f"multi_agent_feasibility_{args.run_id}_calls.csv", result["outputs"])
    write_csv(OUT_DIR / f"multi_agent_feasibility_{args.run_id}_decisions.csv", result["decisions"])
    (OUT_DIR / f"multi_agent_feasibility_{args.run_id}_summary.json").write_text(
        json.dumps(result["summary"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(REPORT_DIR / f"multi_agent_feasibility_{args.run_id}.md", result["summary"], result["decisions"])
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
