"""Analyze whether the true two-stage model is really better than Stage 1 only.

This script does not train a new model. It evaluates the saved V5 test scores
under matched review budgets and multiple cost assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score


RUN_DIR = Path(__file__).resolve().parents[1] / "data" / "model_runs" / "xgboost_v5_true_twostage_20260723_160243"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "model_runs" / "xgboost_v5_true_twostage_20260723_160243" / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class CostAssumption:
    name: str
    fraud_recovery_rate: float
    false_positive_fixed_cost: float
    false_positive_variable_rate: float
    analyst_cost_per_review: float
    overflow_penalty_per_case: float = 5.0


COST_SCENARIOS = [
    CostAssumption("base", 0.60, 5.0, 0.02, 3.0),
    CostAssumption("low_fp_cost", 0.60, 2.0, 0.01, 2.0),
    CostAssumption("high_fp_cost", 0.60, 12.0, 0.04, 5.0),
    CostAssumption("low_recovery", 0.40, 5.0, 0.02, 3.0),
    CostAssumption("high_recovery", 0.80, 5.0, 0.02, 3.0),
    CostAssumption("high_analyst_cost", 0.60, 5.0, 0.02, 8.0),
]


REVIEW_BUDGETS = [100, 200, 300, 400, 500, 700, 944, 1200, 1875]


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


def metric_at_budget(df: pd.DataFrame, score_col: str, budget: int, costs: CostAssumption, label: str) -> dict[str, float | str]:
    ranked = df.sort_values(score_col, ascending=False)
    selected = ranked.head(min(budget, len(ranked))).copy()
    reviewed = df.index.isin(selected.index)
    fraud = df["is_fraud"].astype(bool).to_numpy()
    reviewed_arr = reviewed
    tp = reviewed_arr & fraud
    fp = reviewed_arr & ~fraud
    precision = float(tp.sum() / max(1, reviewed_arr.sum()))
    recall = float(tp.sum() / max(1, fraud.sum()))
    fraud_loss_prevented = float((df.loc[tp, "amount"] * costs.fraud_recovery_rate).sum())
    fraud_loss_realized = float((df.loc[fraud & ~reviewed_arr, "amount"] * (1.0 - costs.fraud_recovery_rate)).sum())
    false_positive_cost = float((costs.false_positive_fixed_cost + df.loc[fp, "amount"] * costs.false_positive_variable_rate).sum())
    analyst_cost = float(reviewed_arr.sum() * costs.analyst_cost_per_review)
    net_benefit = fraud_loss_prevented - false_positive_cost - analyst_cost
    return {
        "cost_scenario": costs.name,
        "policy": label,
        "score_col": score_col,
        "review_budget": int(budget),
        "reviewed": int(reviewed_arr.sum()),
        "fraud_count": int(fraud.sum()),
        "tp": int(tp.sum()),
        "fp": int(fp.sum()),
        "precision": precision,
        "recall": recall,
        "false_positive_rate_in_review": float(fp.sum() / max(1, reviewed_arr.sum())),
        "fraud_loss_prevented": fraud_loss_prevented,
        "fraud_loss_realized": fraud_loss_realized,
        "false_positive_cost": false_positive_cost,
        "analyst_cost": analyst_cost,
        "net_benefit": net_benefit,
        **{f"cost_{key}": value for key, value in asdict(costs).items() if key != "name"},
    }


def full_ranking_metrics(df: pd.DataFrame) -> pd.DataFrame:
    y = df["is_fraud"].to_numpy(int)
    rows = []
    for label, score_col in [
        ("stage1_only", "stage1_probability"),
        ("two_stage_combined", "stage2_combined_score"),
        ("stage1_expected_value", "stage1_ev_score"),
        ("stage2_expected_value", "stage2_ev_score"),
    ]:
        score = df[score_col].fillna(-1e-9).to_numpy(float)
        rows.append(
            {
                "ranking": label,
                "score_col": score_col,
                "roc_auc": float(roc_auc_score(y, score)),
                "pr_auc": float(average_precision_score(y, score)),
            }
        )
    return pd.DataFrame(rows)


def candidate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    y = df["is_fraud"].astype(bool)
    candidate = df["stage1_candidate"].astype(bool)
    candidate_fraud = y & candidate
    return pd.DataFrame(
        [
            {
                "candidate_rate": float(candidate.mean()),
                "candidate_count": int(candidate.sum()),
                "fraud_count": int(y.sum()),
                "fraud_in_candidates": int(candidate_fraud.sum()),
                "candidate_precision": float(candidate_fraud.sum() / max(1, candidate.sum())),
                "candidate_recall": float(candidate_fraud.sum() / max(1, y.sum())),
            }
        ]
    )


def dominance_summary(comparison: pd.DataFrame) -> pd.DataFrame:
    base = comparison[comparison["cost_scenario"] == "base"].copy()
    rows = []
    for budget in REVIEW_BUDGETS:
        part = base[base["review_budget"] == budget]
        s1 = part[part["policy"] == "stage1_probability"].iloc[0]
        s2 = part[part["policy"] == "two_stage_model"].iloc[0]
        rows.append(
            {
                "review_budget": budget,
                "precision_delta_s2_minus_s1": float(s2["precision"] - s1["precision"]),
                "recall_delta_s2_minus_s1": float(s2["recall"] - s1["recall"]),
                "fp_reduction_s2_vs_s1": int(s1["fp"] - s2["fp"]),
                "net_benefit_delta_s2_minus_s1": float(s2["net_benefit"] - s1["net_benefit"]),
                "s1_precision": float(s1["precision"]),
                "s1_recall": float(s1["recall"]),
                "s2_precision": float(s2["precision"]),
                "s2_recall": float(s2["recall"]),
                "s1_net_benefit": float(s1["net_benefit"]),
                "s2_net_benefit": float(s2["net_benefit"]),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    df = add_scores(pd.read_csv(RUN_DIR / "v5_test_scores.csv"))
    rankings = full_ranking_metrics(df)
    candidates = candidate_metrics(df)

    rows = []
    score_defs = [
        ("stage1_probability", "stage1_probability"),
        ("two_stage_model", "stage2_combined_score"),
        ("stage1_expected_value", "stage1_ev_score"),
        ("stage2_expected_value", "stage2_ev_score"),
    ]
    for costs in COST_SCENARIOS:
        for budget in REVIEW_BUDGETS:
            for policy_label, score_col in score_defs:
                rows.append(metric_at_budget(df, score_col, budget, costs, policy_label))
    comparison = pd.DataFrame(rows)
    dominance = dominance_summary(comparison)

    rankings.to_csv(OUT_DIR / "v5_full_ranking_metrics.csv", index=False)
    candidates.to_csv(OUT_DIR / "v5_candidate_capture_summary.csv", index=False)
    comparison.to_csv(OUT_DIR / "v5_budget_cost_sensitivity.csv", index=False)
    dominance.to_csv(OUT_DIR / "v5_stage1_vs_twostage_base_budget_summary.csv", index=False)

    print("Full ranking metrics")
    print(rankings.to_string(index=False))
    print("\nCandidate metrics")
    print(candidates.to_string(index=False))
    print("\nBase cost: Stage1 vs two-stage by matched review budget")
    print(dominance.to_string(index=False))
    print("\nBest policy per cost/budget")
    best = comparison.sort_values("net_benefit", ascending=False).groupby(["cost_scenario", "review_budget"], as_index=False).head(1)
    print(best[["cost_scenario", "review_budget", "policy", "precision", "recall", "net_benefit"]].sort_values(["cost_scenario", "review_budget"]).to_string(index=False))


if __name__ == "__main__":
    main()
