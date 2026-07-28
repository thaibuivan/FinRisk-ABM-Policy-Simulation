"""Recall-first operating point analysis for V5 two-stage model.

This script answers:
- If fraud operations prioritizes recall, how many cases must be reviewed?
- What precision/workload/net benefit trade-off appears at recall targets?

It does not retrain any model. It reads saved V5 test scores.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd


RUN_DIR = Path(__file__).resolve().parents[1] / "data" / "model_runs" / "xgboost_v5_true_twostage_20260723_160243"
OUT_DIR = RUN_DIR / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RECALL_TARGETS = [0.70, 0.80, 0.85, 0.90, 0.95]


@dataclass(frozen=True)
class CostAssumption:
    name: str
    fraud_recovery_rate: float
    false_positive_fixed_cost: float
    false_positive_variable_rate: float
    analyst_cost_per_review: float


COST_SCENARIOS = [
    CostAssumption("base", 0.60, 5.0, 0.02, 3.0),
    CostAssumption("high_fp_cost", 0.60, 12.0, 0.04, 5.0),
    CostAssumption("high_analyst_cost", 0.60, 5.0, 0.02, 8.0),
    CostAssumption("high_recovery", 0.80, 5.0, 0.02, 3.0),
]


def add_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["stage2_combined_score"] = out["stage2_probability"].fillna(-1e-9)
    out["stage1_ev_score"] = out["stage1_expected_review_value"].fillna(-1e-9)
    out["stage2_ev_score"] = (
        out["stage2_probability"].fillna(0) * out["amount"] * 0.60
        - (1.0 - out["stage2_probability"].fillna(0)) * (5.0 + out["amount"] * 0.02)
        - 3.0
    )
    out.loc[~out["stage1_candidate"].astype(bool), "stage2_ev_score"] = -1e-9
    return out


def payoff(df: pd.DataFrame, reviewed: np.ndarray, costs: CostAssumption) -> dict[str, float]:
    fraud = df["is_fraud"].astype(bool).to_numpy()
    tp = reviewed & fraud
    fp = reviewed & ~fraud
    fraud_loss_prevented = float((df.loc[tp, "amount"] * costs.fraud_recovery_rate).sum())
    false_positive_cost = float((costs.false_positive_fixed_cost + df.loc[fp, "amount"] * costs.false_positive_variable_rate).sum())
    analyst_cost = float(reviewed.sum() * costs.analyst_cost_per_review)
    net_benefit = fraud_loss_prevented - false_positive_cost - analyst_cost
    return {
        "fraud_loss_prevented": fraud_loss_prevented,
        "false_positive_cost": false_positive_cost,
        "analyst_cost": analyst_cost,
        "net_benefit": net_benefit,
    }


def minimal_prefix_for_recall(df: pd.DataFrame, score_col: str, target: float, costs: CostAssumption, label: str) -> dict[str, float | str | int]:
    ranked = df.sort_values(score_col, ascending=False).copy()
    y = ranked["is_fraud"].astype(int).to_numpy()
    total_fraud = int(y.sum())
    cumulative_tp = np.cumsum(y)
    needed_tp = int(np.ceil(target * total_fraud))
    if needed_tp <= 0:
        k = 0
    elif cumulative_tp[-1] < needed_tp:
        k = len(ranked)
    else:
        k = int(np.searchsorted(cumulative_tp, needed_tp, side="left") + 1)

    selected_index = ranked.index[:k]
    reviewed = df.index.isin(selected_index)
    fraud = df["is_fraud"].astype(bool).to_numpy()
    tp = int((reviewed & fraud).sum())
    fp = int((reviewed & ~fraud).sum())
    precision = float(tp / max(1, reviewed.sum()))
    recall = float(tp / max(1, total_fraud))

    out = {
        "cost_scenario": costs.name,
        "policy": label,
        "score_col": score_col,
        "target_recall": target,
        "actual_recall": recall,
        "precision": precision,
        "reviewed": int(reviewed.sum()),
        "review_rate": float(reviewed.mean()),
        "fraud_count": total_fraud,
        "tp": tp,
        "fp": fp,
    }
    out.update(payoff(df, reviewed, costs))
    out.update({f"cost_{k}": v for k, v in asdict(costs).items() if k != "name"})
    return out


def scenario_recall_first(df: pd.DataFrame, score_col: str, target: float, label: str) -> pd.DataFrame:
    rows = []
    for scenario, part in df.groupby("scenario"):
        ranked = part.sort_values(score_col, ascending=False)
        y = ranked["is_fraud"].astype(int).to_numpy()
        total_fraud = int(y.sum())
        needed_tp = int(np.ceil(target * total_fraud))
        if total_fraud == 0:
            k = 0
        elif y.cumsum()[-1] < needed_tp:
            k = len(ranked)
        else:
            k = int(np.searchsorted(y.cumsum(), needed_tp, side="left") + 1)
        tp = int(y[:k].sum())
        rows.append(
            {
                "scenario": scenario,
                "policy": label,
                "target_recall": target,
                "actual_recall": float(tp / max(1, total_fraud)),
                "precision": float(tp / max(1, k)),
                "reviewed": int(k),
                "review_rate": float(k / max(1, len(part))),
                "fraud_count": total_fraud,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    df = add_scores(pd.read_csv(RUN_DIR / "v5_test_scores.csv"))
    score_defs = [
        ("stage1_probability", "stage1_probability"),
        ("two_stage_model", "stage2_combined_score"),
        ("stage1_expected_value", "stage1_ev_score"),
        ("stage2_expected_value", "stage2_ev_score"),
    ]

    rows = []
    for costs in COST_SCENARIOS:
        for target in RECALL_TARGETS:
            for policy_label, score_col in score_defs:
                rows.append(minimal_prefix_for_recall(df, score_col, target, costs, policy_label))
    recall_points = pd.DataFrame(rows)
    recall_points.to_csv(OUT_DIR / "v5_recall_first_operating_points.csv", index=False)

    scenario_rows = []
    for target in [0.80, 0.90]:
        for policy_label, score_col in score_defs:
            scenario_rows.append(scenario_recall_first(df, score_col, target, policy_label))
    scenario_points = pd.concat(scenario_rows, ignore_index=True)
    scenario_points.to_csv(OUT_DIR / "v5_recall_first_by_scenario.csv", index=False)

    base = recall_points[recall_points["cost_scenario"] == "base"].copy()
    print("Recall-first operating points, base cost")
    print(
        base[
            [
                "target_recall",
                "policy",
                "actual_recall",
                "precision",
                "reviewed",
                "review_rate",
                "tp",
                "fp",
                "net_benefit",
            ]
        ].to_string(index=False)
    )

    print("\nBest policy by target recall and cost")
    best = recall_points.sort_values("net_benefit", ascending=False).groupby(["cost_scenario", "target_recall"], as_index=False).head(1)
    print(best[["cost_scenario", "target_recall", "policy", "actual_recall", "precision", "reviewed", "net_benefit"]].sort_values(["cost_scenario", "target_recall"]).to_string(index=False))


if __name__ == "__main__":
    main()
