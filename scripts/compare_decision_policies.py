"""Compare transaction-risk decision policies on an existing simulation run.

This script separates the thesis question into two layers:
1. Data/model simulation: already produced by generate_simulation_data.py.
2. Mechanism/policy evaluation: recompute decisions, costs, and utility under
   different decision mechanisms and cost assumptions.

The outputs are for research simulation only. They are not real bank profit or
production fraud-detection performance claims.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class CostAssumptions:
    fraud_recovery_rate: float
    false_positive_fixed_cost: float
    false_positive_variable_rate: float
    analyst_cost_per_minute: float
    review_minutes_high_risk: float
    review_minutes_medium_risk: float


@dataclass(frozen=True)
class PolicySpec:
    name: str
    description: str
    review_threshold: int
    hold_threshold: int
    mode: str


POLICIES = [
    PolicySpec(
        name="balanced_threshold",
        description="Baseline threshold: review score >=70, simulated hold/step-up score >=90.",
        review_threshold=70,
        hold_threshold=90,
        mode="threshold",
    ),
    PolicySpec(
        name="sensitive_threshold",
        description="Lower threshold: review score >=50, designed to improve recall but may increase false positives.",
        review_threshold=50,
        hold_threshold=85,
        mode="threshold",
    ),
    PolicySpec(
        name="strict_threshold",
        description="Higher threshold: review score >=85, designed to reduce workload and false positives.",
        review_threshold=85,
        hold_threshold=95,
        mode="threshold",
    ),
    PolicySpec(
        name="capacity_aware",
        description="Capacity-aware queue: candidates score >=50 are ranked by risk score; only daily capacity is reviewed.",
        review_threshold=50,
        hold_threshold=90,
        mode="capacity_aware",
    ),
    PolicySpec(
        name="cost_sensitive",
        description="Cost-sensitive queue: review only when expected review utility is positive, then rank by expected utility.",
        review_threshold=0,
        hold_threshold=90,
        mode="cost_sensitive",
    ),
]


def safe_text(value: object) -> str:
    return str(value).encode("ascii", errors="backslashreplace").decode("ascii")


def load_cost_scenarios(path: Path) -> dict[str, CostAssumptions]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    base = raw["base"]
    scenarios = {}
    for name, overrides in raw.get("sensitivity_scenarios", {}).items():
        merged = {**base, **overrides}
        scenarios[name] = CostAssumptions(**merged)
    if "base_cost" not in scenarios:
        scenarios["base_cost"] = CostAssumptions(**base)
    return scenarios


def latest_run_dir(runs_dir: Path, scenario_name: str) -> Path:
    matches = sorted(runs_dir.glob(f"{scenario_name}_*"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No run directory found for scenario {scenario_name} in {runs_dir}")
    return matches[0]


def load_simulation_run(run_dir: Path) -> pd.DataFrame:
    transactions = pd.read_csv(run_dir / "transactions.csv")
    scores = pd.read_csv(run_dir / "risk_scores.csv")
    df = transactions[["transaction_id", "day_index", "amount", "is_fraud"]].merge(scores, on="transaction_id", how="inner")
    df["risk_probability"] = df["risk_probability"].astype(float)
    df["risk_score"] = df["risk_score"].astype(int)
    df["amount"] = df["amount"].astype(float)
    df["is_fraud"] = df["is_fraud"].astype(int)
    df["day_index"] = df["day_index"].astype(int)
    return df


def review_minutes_for_score(score: int, costs: CostAssumptions) -> float:
    return costs.review_minutes_high_risk if score >= 85 else costs.review_minutes_medium_risk


def expected_review_value(row: object, costs: CostAssumptions) -> float:
    probability = float(row.risk_probability)
    amount = float(row.amount)
    expected_prevented = probability * amount * costs.fraud_recovery_rate
    expected_false_positive = (1.0 - probability) * (costs.false_positive_fixed_cost + amount * costs.false_positive_variable_rate)
    expected_review_cost = review_minutes_for_score(int(row.risk_score), costs) * costs.analyst_cost_per_minute
    return expected_prevented - expected_false_positive - expected_review_cost


def apply_policy(df: pd.DataFrame, policy: PolicySpec, costs: CostAssumptions, analyst_capacity_per_day: int) -> pd.DataFrame:
    rows = []
    data = df.copy()
    data["expected_review_value"] = data.apply(lambda row: expected_review_value(row, costs), axis=1)

    for day, group in data.groupby("day_index", sort=True):
        group = group.copy()
        if policy.mode == "threshold":
            group["policy_candidate"] = group["risk_score"] >= policy.review_threshold
            group = group.sort_values("risk_score", ascending=False)
        elif policy.mode == "capacity_aware":
            group["policy_candidate"] = group["risk_score"] >= policy.review_threshold
            group = group.sort_values("risk_score", ascending=False)
        elif policy.mode == "cost_sensitive":
            group["policy_candidate"] = group["expected_review_value"] > 0
            group = group.sort_values("expected_review_value", ascending=False)
        else:
            raise ValueError(f"Unknown policy mode: {policy.mode}")

        review_used = 0
        for row in group.itertuples(index=False):
            candidate = bool(row.policy_candidate)
            reviewed = int(candidate and review_used < analyst_capacity_per_day)
            if reviewed:
                review_used += 1

            if not candidate:
                action = "allow" if int(row.risk_score) < 50 else "monitor"
            elif int(row.risk_score) >= policy.hold_threshold:
                action = "simulated_step_up_or_hold"
            else:
                action = "review_queue"

            rows.append(
                {
                    "transaction_id": row.transaction_id,
                    "day_index": int(day),
                    "policy_name": policy.name,
                    "policy_action": action,
                    "sent_to_analyst": int(candidate),
                    "analyst_reviewed": reviewed,
                    "review_queue_overflow": int(candidate and not reviewed),
                    "expected_review_value": round(float(row.expected_review_value), 4),
                }
            )
    return pd.DataFrame(rows)


def evaluate_policy(base_df: pd.DataFrame, decisions: pd.DataFrame, costs: CostAssumptions, policy: PolicySpec, cost_scenario: str) -> dict[str, object]:
    df = base_df.merge(decisions, on="transaction_id", how="inner")
    flagged = df["sent_to_analyst"].eq(1)
    reviewed = df["analyst_reviewed"].eq(1)
    fraud = df["is_fraud"].eq(1)

    flagged_tp = int((flagged & fraud).sum())
    flagged_fp = int((flagged & ~fraud).sum())
    flagged_fn = int((~flagged & fraud).sum())
    reviewed_tp = int((reviewed & fraud).sum())
    reviewed_fp = int((reviewed & ~fraud).sum())
    reviewed_fn = int((~reviewed & fraud).sum())

    precision_flagged = flagged_tp / (flagged_tp + flagged_fp) if (flagged_tp + flagged_fp) else 0.0
    recall_flagged = flagged_tp / (flagged_tp + flagged_fn) if (flagged_tp + flagged_fn) else 0.0
    precision_reviewed = reviewed_tp / (reviewed_tp + reviewed_fp) if (reviewed_tp + reviewed_fp) else 0.0
    recall_reviewed = reviewed_tp / (reviewed_tp + reviewed_fn) if (reviewed_tp + reviewed_fn) else 0.0

    prevented_mask = fraud & reviewed
    missed_mask = fraud & ~prevented_mask
    false_positive_mask = (~fraud) & flagged

    review_minutes = df["risk_score"].map(lambda score: review_minutes_for_score(int(score), costs))
    review_minutes = review_minutes.where(reviewed, 0.0)

    fraud_loss_prevented = (df.loc[prevented_mask, "amount"] * costs.fraud_recovery_rate).sum()
    fraud_loss_realized = df.loc[missed_mask, "amount"].sum()
    false_positive_cost = (costs.false_positive_fixed_cost + df.loc[false_positive_mask, "amount"] * costs.false_positive_variable_rate).sum()
    analyst_cost = (review_minutes * costs.analyst_cost_per_minute).sum()
    net_benefit = fraud_loss_prevented - fraud_loss_realized - false_positive_cost - analyst_cost

    return {
        "policy_name": policy.name,
        "policy_description": policy.description,
        "cost_scenario": cost_scenario,
        "transactions": int(len(df)),
        "fraud_count": int(fraud.sum()),
        "fraud_rate": round(float(fraud.mean()) if len(df) else 0.0, 6),
        "alerts_sent_to_analyst": int(flagged.sum()),
        "analyst_reviewed": int(reviewed.sum()),
        "review_overflow": int(df["review_queue_overflow"].sum()),
        "precision_flagged": round(float(precision_flagged), 4),
        "recall_flagged": round(float(recall_flagged), 4),
        "precision_reviewed": round(float(precision_reviewed), 4),
        "recall_reviewed": round(float(recall_reviewed), 4),
        "fraud_loss_prevented": round(float(fraud_loss_prevented), 2),
        "fraud_loss_realized": round(float(fraud_loss_realized), 2),
        "false_positive_cost": round(float(false_positive_cost), 2),
        "analyst_cost": round(float(analyst_cost), 2),
        "net_benefit": round(float(net_benefit), 2),
        "fraud_recovery_rate": costs.fraud_recovery_rate,
        "false_positive_fixed_cost": costs.false_positive_fixed_cost,
        "false_positive_variable_rate": costs.false_positive_variable_rate,
        "analyst_cost_per_minute": costs.analyst_cost_per_minute,
    }


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    text_df = df.copy()
    for col in text_df.columns:
        text_df[col] = text_df[col].map(lambda value: "" if pd.isna(value) else str(value))
    headers = list(text_df.columns)
    rows = text_df.values.tolist()
    widths = []
    for idx, header in enumerate(headers):
        values = [str(row[idx]) for row in rows]
        widths.append(max([len(str(header)), *[len(value) for value in values]]))

    def fmt_row(values: list[object]) -> str:
        return "| " + " | ".join(str(value).ljust(widths[idx]) for idx, value in enumerate(values)) + " |"

    lines = [fmt_row(headers), "| " + " | ".join("-" * width for width in widths) + " |"]
    for row in rows:
        lines.append(fmt_row(row))
    return "\n".join(lines)


def write_markdown_summary(comparison: pd.DataFrame, output_path: Path, run_dir: Path, analyst_capacity: int) -> None:
    base = comparison[comparison["cost_scenario"] == "base_cost"].copy()
    cols = [
        "policy_name",
        "alerts_sent_to_analyst",
        "analyst_reviewed",
        "review_overflow",
        "precision_flagged",
        "recall_flagged",
        "precision_reviewed",
        "recall_reviewed",
        "false_positive_cost",
        "analyst_cost",
        "net_benefit",
    ]
    markdown = [
        "# Policy Comparison Summary",
        "",
        f"Input simulation run: `{run_dir}`",
        f"Analyst capacity per day: `{analyst_capacity}`",
        "",
        "## Base Cost Scenario",
        "",
        dataframe_to_markdown(base[cols]),
        "",
        "## Interpretation",
        "",
        "- `sensitive_threshold` tends to increase recall but can create more false positives and analyst workload.",
        "- `strict_threshold` reduces workload and false positive cost but may miss more fraud.",
        "- `capacity_aware` makes the capacity constraint explicit by ranking candidates before review.",
        "- `cost_sensitive` uses expected utility, so it is closest to the mechanism-design framing of the thesis.",
        "",
        "## Important caveat",
        "",
        "Net benefit is a simulated utility under explicit assumptions, not real profit. Use it to compare policies under the same assumptions, not as a production financial claim.",
    ]
    output_path.write_text("\n".join(markdown), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare decision policies on an existing simulation run.")
    parser.add_argument("--run-dir", type=str, default=None, help="Existing simulation run directory. Defaults to latest baseline run.")
    parser.add_argument("--scenario-name", type=str, default="baseline")
    parser.add_argument("--runs-dir", type=str, default="data/simulation_runs")
    parser.add_argument("--cost-config", type=str, default="config/cost_assumptions.json")
    parser.add_argument("--output-dir", type=str, default="data/policy_comparisons")
    parser.add_argument("--analyst-capacity-per-day", type=int, default=100)
    parser.add_argument("--project-root", type=str, default=str(Path(__file__).resolve().parents[1]))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    run_dir = Path(args.run_dir).resolve() if args.run_dir else latest_run_dir(project_root / args.runs_dir, args.scenario_name)
    output_dir = (project_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cost_scenarios = load_cost_scenarios(project_root / args.cost_config)
    base_df = load_simulation_run(run_dir)

    rows = []
    decision_outputs = []
    for cost_name, costs in cost_scenarios.items():
        for policy in POLICIES:
            decisions = apply_policy(base_df, policy, costs, args.analyst_capacity_per_day)
            rows.append(evaluate_policy(base_df, decisions, costs, policy, cost_name))
            if cost_name == "base_cost":
                decision_outputs.append(decisions)

    comparison = pd.DataFrame(rows)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"policy_comparison_{timestamp}.csv"
    md_path = output_dir / f"policy_comparison_{timestamp}.md"
    decisions_path = output_dir / f"policy_decisions_base_cost_{timestamp}.csv"

    comparison.to_csv(csv_path, index=False)
    if decision_outputs:
        pd.concat(decision_outputs, ignore_index=True).to_csv(decisions_path, index=False)
    write_markdown_summary(comparison, md_path, run_dir, args.analyst_capacity_per_day)

    print("Policy comparison written to:")
    print(safe_text(csv_path))
    print(safe_text(md_path))
    print(safe_text(decisions_path))
    cols = ["policy_name", "cost_scenario", "alerts_sent_to_analyst", "analyst_reviewed", "review_overflow", "precision_flagged", "recall_reviewed", "net_benefit"]
    print(comparison[comparison["cost_scenario"] == "base_cost"][cols].to_string(index=False))


if __name__ == "__main__":
    main()

