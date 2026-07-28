"""Train a simulation-native transaction risk model.

This script intentionally does not reuse old model weights from RiskGuard AI.
It reuses only the pipeline idea: build behavior features, train a risk model,
export risk scores, then evaluate decision policies under analyst capacity.

The model is a small logistic regression implemented with numpy so the thesis
prototype does not need extra dependencies beyond pandas/numpy.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


SCENARIO_NAMES = [
    "low_fraud",
    "baseline",
    "stress_fraud",
    "low_capacity",
    "high_capacity",
]

NUMERIC_FEATURES = [
    "amount",
    "log_amount",
    "hour",
    "amount_anomaly_signal",
    "velocity_signal",
    "unusual_hour_signal",
    "merchant_risk_signal",
    "baseline_risk",
    "gap_minutes_since_prev",
    "txn_count_1h",
    "total_amount_1h",
    "avg_amount_1h",
    "median_amount_1h",
    "p95_amount_1h",
    "txn_count_24h",
    "total_amount_24h",
    "avg_amount_24h",
    "median_amount_24h",
    "p95_amount_24h",
    "txn_count_3d",
    "total_amount_3d",
    "avg_amount_3d",
    "median_amount_3d",
    "p95_amount_3d",
    "txn_count_7d",
    "total_amount_7d",
    "avg_amount_7d",
    "median_amount_7d",
    "p95_amount_7d",
    "txn_count_30d",
    "total_amount_30d",
    "avg_amount_30d",
    "median_amount_30d",
    "p95_amount_30d",
]

CATEGORICAL_FEATURES = ["merchant_category", "channel"]


@dataclass(frozen=True)
class CostAssumptions:
    fraud_recovery_rate: float = 0.60
    false_positive_fixed_cost: float = 5.0
    false_positive_variable_rate: float = 0.02
    analyst_cost_per_review: float = 3.0
    overflow_penalty_per_case: float = 5.0


def latest_run_dir(runs_dir: Path, scenario_name: str) -> Path:
    matches = sorted(
        runs_dir.glob(f"{scenario_name}_*"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise FileNotFoundError(f"No run directory found for scenario {scenario_name}")
    return matches[0]


def load_run(run_dir: Path, scenario_name: str) -> pd.DataFrame:
    transactions = pd.read_csv(run_dir / "transactions.csv")
    behavior = pd.read_csv(run_dir / "behavior_features.csv")
    df = transactions.merge(behavior.drop(columns=["customer_id"], errors="ignore"), on="transaction_id", how="left")
    df["scenario"] = scenario_name
    df["run_dir"] = str(run_dir)
    df["is_fraud"] = df["is_fraud"].astype(int)
    df["amount"] = df["amount"].astype(float)
    df["log_amount"] = np.log1p(df["amount"].clip(lower=0))
    return df


def load_dataset(project_root: Path, scenario_names: list[str]) -> pd.DataFrame:
    runs_dir = project_root / "data" / "simulation_runs"
    frames = []
    for scenario in scenario_names:
        frames.append(load_run(latest_run_dir(runs_dir, scenario), scenario))
    return pd.concat(frames, ignore_index=True)


def split_train_test(df: pd.DataFrame, test_days: int = 8) -> tuple[pd.DataFrame, pd.DataFrame]:
    max_day_by_run = df.groupby("run_dir")["day_index"].transform("max")
    test_mask = df["day_index"] > (max_day_by_run - test_days)
    train = df.loc[~test_mask].copy()
    test = df.loc[test_mask].copy()
    if train["is_fraud"].sum() == 0 or test["is_fraud"].sum() == 0:
        raise RuntimeError("Train/test split has no positive fraud examples.")
    return train, test


def make_design_matrix(
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, list[str], dict[str, list[float]]]:
    train_num = train[NUMERIC_FEATURES].replace([np.inf, -np.inf], np.nan)
    test_num = test[NUMERIC_FEATURES].replace([np.inf, -np.inf], np.nan)
    medians = train_num.median(numeric_only=True).fillna(0.0)
    train_num = train_num.fillna(medians)
    test_num = test_num.fillna(medians)

    means = train_num.mean()
    stds = train_num.std(ddof=0).replace(0, 1.0).fillna(1.0)
    train_num = (train_num - means) / stds
    test_num = (test_num - means) / stds

    combined_cat = pd.concat(
        [train[CATEGORICAL_FEATURES], test[CATEGORICAL_FEATURES]],
        axis=0,
        ignore_index=True,
    ).fillna("unknown")
    encoded = pd.get_dummies(combined_cat, columns=CATEGORICAL_FEATURES, prefix=CATEGORICAL_FEATURES, dtype=float)
    train_cat = encoded.iloc[: len(train)].reset_index(drop=True)
    test_cat = encoded.iloc[len(train) :].reset_index(drop=True)

    train_x = pd.concat([train_num.reset_index(drop=True), train_cat], axis=1)
    test_x = pd.concat([test_num.reset_index(drop=True), test_cat], axis=1)
    feature_names = list(train_x.columns)
    metadata = {
        "numeric_medians": medians.astype(float).tolist(),
        "numeric_means": means.astype(float).tolist(),
        "numeric_stds": stds.astype(float).tolist(),
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "feature_names": feature_names,
    }
    return train_x.to_numpy(float), test_x.to_numpy(float), feature_names, metadata


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


def train_logistic_regression(
    x: np.ndarray,
    y: np.ndarray,
    *,
    epochs: int,
    learning_rate: float,
    l2: float,
) -> tuple[np.ndarray, float, float, list[dict[str, float]]]:
    n_features = x.shape[1]
    weights = np.zeros(n_features, dtype=float)
    bias = 0.0
    pos = max(1.0, float(y.sum()))
    neg = max(1.0, float(len(y) - y.sum()))
    pos_weight = min(50.0, neg / pos)
    sample_weight = np.where(y == 1, pos_weight, 1.0)
    weight_sum = sample_weight.sum()
    history: list[dict[str, float]] = []

    for epoch in range(1, epochs + 1):
        pred = sigmoid(x @ weights + bias)
        error = (pred - y) * sample_weight
        grad_w = (x.T @ error) / weight_sum + l2 * weights
        grad_b = float(error.sum() / weight_sum)
        weights -= learning_rate * grad_w
        bias -= learning_rate * grad_b
        if epoch == 1 or epoch % 50 == 0 or epoch == epochs:
            loss = -np.average(
                y * np.log(pred + 1e-12) + (1 - y) * np.log(1 - pred + 1e-12),
                weights=sample_weight,
            ) + 0.5 * l2 * float(np.sum(weights * weights))
            history.append({"epoch": epoch, "weighted_log_loss": float(loss)})
    return weights, bias, float(pos_weight), history


def roc_auc_score_np(y: np.ndarray, score: np.ndarray) -> float:
    order = np.argsort(score)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(score) + 1)
    pos = y == 1
    n_pos = float(pos.sum())
    n_neg = float(len(y) - pos.sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def average_precision_np(y: np.ndarray, score: np.ndarray) -> float:
    order = np.argsort(-score)
    y_sorted = y[order]
    total_pos = y_sorted.sum()
    if total_pos == 0:
        return float("nan")
    cum_tp = np.cumsum(y_sorted)
    precision = cum_tp / (np.arange(len(y_sorted)) + 1)
    return float((precision * y_sorted).sum() / total_pos)


def precision_recall_at_k(y: np.ndarray, score: np.ndarray, k: int) -> tuple[float, float, int]:
    k = max(1, min(int(k), len(y)))
    order = np.argsort(-score)[:k]
    tp = float(y[order].sum())
    precision = tp / k
    recall = tp / max(1.0, float(y.sum()))
    return float(precision), float(recall), k


def threshold_metrics(y: np.ndarray, score: np.ndarray, threshold: int) -> dict[str, float]:
    pred = score >= threshold
    alerts = int(pred.sum())
    tp = int(((pred) & (y == 1)).sum())
    fp = int(((pred) & (y == 0)).sum())
    precision = tp / alerts if alerts else 0.0
    recall = tp / int(y.sum()) if int(y.sum()) else 0.0
    return {
        "threshold": threshold,
        "alerts": alerts,
        "true_positives": tp,
        "false_positives": fp,
        "precision": precision,
        "recall": recall,
    }


def outcome_metrics_from_review_flags(
    scored: pd.DataFrame,
    reviewed_flags: list[bool],
    policy_name: str,
    threshold: int | str,
    costs: CostAssumptions,
    overflow_total: int,
) -> dict[str, float | str]:
    df = scored.copy()
    df["reviewed"] = reviewed_flags
    reviewed = df["reviewed"]
    fraud = df["is_fraud"] == 1
    fp = reviewed & ~fraud
    tp = reviewed & fraud

    fraud_loss_prevented = float((df.loc[tp, "amount"] * costs.fraud_recovery_rate).sum())
    fraud_loss_realized = float((df.loc[fraud & ~reviewed, "amount"] * (1.0 - costs.fraud_recovery_rate)).sum())
    false_positive_cost = float((costs.false_positive_fixed_cost + df.loc[fp, "amount"] * costs.false_positive_variable_rate).sum())
    analyst_cost = float(reviewed.sum() * costs.analyst_cost_per_review)
    overflow_penalty = float(overflow_total * costs.overflow_penalty_per_case)
    net_benefit = fraud_loss_prevented - false_positive_cost - analyst_cost - overflow_penalty
    reviewed_count = int(reviewed.sum())
    tp_count = int(tp.sum())
    return {
        "policy_name": policy_name,
        "threshold": threshold,
        "alerts": int(reviewed_count + overflow_total),
        "analyst_reviewed": reviewed_count,
        "review_overflow": int(overflow_total),
        "precision_reviewed": tp_count / reviewed_count if reviewed_count else 0.0,
        "recall_reviewed": tp_count / int(fraud.sum()) if int(fraud.sum()) else 0.0,
        "fraud_loss_prevented": fraud_loss_prevented,
        "fraud_loss_realized": fraud_loss_realized,
        "false_positive_cost": false_positive_cost,
        "analyst_cost": analyst_cost,
        "overflow_penalty": overflow_penalty,
        "net_benefit": net_benefit,
    }


def policy_metrics(
    scored: pd.DataFrame,
    policy_name: str,
    threshold: int,
    costs: CostAssumptions,
    analyst_capacity_per_day: int,
) -> dict[str, float | str]:
    reviewed_flags = pd.Series(False, index=scored.index)
    overflow_total = 0
    for _, group in scored.groupby(["scenario", "day_index"], sort=False):
        candidates = group[group["ml_risk_score"] >= threshold].sort_values("ml_risk_score", ascending=False)
        reviewed_index = candidates.head(analyst_capacity_per_day).index
        overflow_total += max(0, len(candidates) - analyst_capacity_per_day)
        reviewed_flags.loc[reviewed_index] = True

    return outcome_metrics_from_review_flags(scored, reviewed_flags.tolist(), policy_name, threshold, costs, overflow_total)


def top_percentile_policy_metrics(
    scored: pd.DataFrame,
    policy_name: str,
    top_percentile: float,
    costs: CostAssumptions,
    analyst_capacity_per_day: int,
) -> dict[str, float | str]:
    reviewed_flags = pd.Series(False, index=scored.index)
    overflow_total = 0
    for _, group in scored.groupby(["scenario", "day_index"], sort=False):
        daily_k = max(1, int(np.ceil(len(group) * top_percentile)))
        candidates = group.sort_values("ml_risk_score", ascending=False).head(daily_k)
        reviewed_index = candidates.head(analyst_capacity_per_day).index
        overflow_total += max(0, len(candidates) - analyst_capacity_per_day)
        reviewed_flags.loc[reviewed_index] = True
    return outcome_metrics_from_review_flags(
        scored,
        reviewed_flags.tolist(),
        policy_name,
        f"top_{int(top_percentile * 100)}pct",
        costs,
        overflow_total,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--l2", type=float, default=0.001)
    parser.add_argument("--test-days", type=int, default=8)
    parser.add_argument("--capacity-per-day", type=int, default=100)
    args = parser.parse_args()

    project_root = args.project_root
    output_dir = project_root / "data" / "model_runs" / f"simulation_risk_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(project_root, SCENARIO_NAMES)
    train_df, test_df = split_train_test(dataset, test_days=args.test_days)
    train_x, test_x, feature_names, metadata = make_design_matrix(train_df, test_df)
    y_train = train_df["is_fraud"].to_numpy(int)
    y_test = test_df["is_fraud"].to_numpy(int)

    weights, bias, pos_weight, history = train_logistic_regression(
        train_x,
        y_train,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
    )

    train_logit = train_x @ weights + bias
    test_logit = test_x @ weights + bias
    train_priority = sigmoid(train_logit)
    test_priority = sigmoid(test_logit)
    # Class weighting improves ranking but makes raw probabilities too high.
    # Correct the intercept back by the log class weight for a rough prior calibration.
    train_prob = sigmoid(train_logit - np.log(pos_weight))
    test_prob = sigmoid(test_logit - np.log(pos_weight))
    train_score = np.rint(train_priority * 100).clip(0, 100).astype(int)
    test_score = np.rint(test_priority * 100).clip(0, 100).astype(int)

    metrics_rows = []
    for split_name, y, prob, score in [
        ("train", y_train, train_prob, train_score),
        ("test", y_test, test_prob, test_score),
    ]:
        metrics_rows.append(
            {
                "split": split_name,
                "rows": int(len(y)),
                "fraud_count": int(y.sum()),
                "fraud_rate": float(y.mean()),
                "roc_auc": roc_auc_score_np(y, prob),
                "pr_auc_average_precision": average_precision_np(y, prob),
                "mean_probability": float(prob.mean()),
            }
        )
        for pct in [0.01, 0.05, 0.10]:
            precision, recall, k = precision_recall_at_k(y, prob, int(len(y) * pct))
            metrics_rows.append(
                {
                    "split": f"{split_name}_top_{int(pct * 100)}pct",
                    "rows": k,
                    "fraud_count": int(y.sum()),
                    "fraud_rate": float(y.mean()),
                    "roc_auc": np.nan,
                    "pr_auc_average_precision": np.nan,
                    "mean_probability": np.nan,
                    "precision_at_k": precision,
                    "recall_at_k": recall,
                }
            )
        for threshold in [50, 70, 85]:
            row = threshold_metrics(y, score, threshold)
            row["split"] = f"{split_name}_threshold_{threshold}"
            metrics_rows.append(row)

    coefficients = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": weights,
            "abs_coefficient": np.abs(weights),
        }
    ).sort_values("abs_coefficient", ascending=False)

    score_cols = [
        "transaction_id",
        "customer_id",
        "card_id",
        "scenario",
        "day_index",
        "timestamp",
        "amount",
        "hour",
        "merchant_category",
        "channel",
        "is_fraud",
    ]
    train_scores = train_df[score_cols].copy()
    train_scores["split"] = "train"
    train_scores["ml_risk_probability"] = train_prob
    train_scores["ml_priority_probability"] = train_priority
    train_scores["ml_risk_score"] = train_score
    test_scores = test_df[score_cols].copy()
    test_scores["split"] = "test"
    test_scores["ml_risk_probability"] = test_prob
    test_scores["ml_priority_probability"] = test_priority
    test_scores["ml_risk_score"] = test_score
    all_scores = pd.concat([train_scores, test_scores], ignore_index=True)

    costs = CostAssumptions()
    test_policy_input = all_scores[all_scores["split"] == "test"].copy()
    policy_rows = [
        top_percentile_policy_metrics(test_policy_input, "ml_top_1pct_daily", 0.01, costs, args.capacity_per_day),
        top_percentile_policy_metrics(test_policy_input, "ml_top_5pct_daily", 0.05, costs, args.capacity_per_day),
        top_percentile_policy_metrics(test_policy_input, "ml_top_10pct_daily", 0.10, costs, args.capacity_per_day),
        policy_metrics(test_policy_input, "ml_threshold_50", 50, costs, args.capacity_per_day),
        policy_metrics(test_policy_input, "ml_threshold_70", 70, costs, args.capacity_per_day),
        policy_metrics(test_policy_input, "ml_threshold_85", 85, costs, args.capacity_per_day),
    ]
    threshold_sweep = [
        policy_metrics(test_policy_input, f"ml_threshold_{threshold}", threshold, costs, args.capacity_per_day)
        for threshold in range(5, 100, 5)
    ]
    best_threshold = max(threshold_sweep, key=lambda row: float(row["net_benefit"]))

    pd.DataFrame(metrics_rows).to_csv(output_dir / "model_metrics.csv", index=False)
    coefficients.to_csv(output_dir / "model_coefficients.csv", index=False)
    all_scores.to_csv(output_dir / "model_scores.csv", index=False)
    pd.DataFrame(policy_rows).to_csv(output_dir / "model_policy_comparison.csv", index=False)
    pd.DataFrame(threshold_sweep).to_csv(output_dir / "model_threshold_sweep.csv", index=False)
    pd.DataFrame(history).to_csv(output_dir / "training_history.csv", index=False)
    (output_dir / "model_metadata.json").write_text(
        json.dumps(
            {
                "model_type": "numpy_logistic_regression",
                "scenario_names": SCENARIO_NAMES,
                "train_rows": int(len(train_df)),
                "test_rows": int(len(test_df)),
                "train_fraud_count": int(y_train.sum()),
                "test_fraud_count": int(y_test.sum()),
                "test_days": args.test_days,
                "epochs": args.epochs,
                "learning_rate": args.learning_rate,
                "l2": args.l2,
                "bias": bias,
                "class_weight_positive": pos_weight,
                "probability_calibration": "intercept corrected by subtracting log(class_weight_positive)",
                "score_note": "ml_risk_score is a 0-100 priority score based on weighted model ranking; ml_risk_probability is prior-adjusted.",
                "best_threshold_by_net_benefit": best_threshold,
                "cost_assumptions": asdict(costs),
                "preprocessing": metadata,
                "output_files": [
                    "model_metrics.csv",
                    "model_coefficients.csv",
                    "model_scores.csv",
                    "model_policy_comparison.csv",
                    "model_threshold_sweep.csv",
                    "training_history.csv",
                    "model_metadata.json",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = pd.DataFrame(metrics_rows)
    test_summary = summary[summary["split"].isin(["test", "test_top_1pct", "test_top_5pct", "test_top_10pct"])]
    print(f"Output: {output_dir}")
    print(test_summary.to_string(index=False))
    print(pd.DataFrame(policy_rows).to_string(index=False))
    print("Best threshold by net benefit:")
    print(pd.DataFrame([best_threshold]).to_string(index=False))


if __name__ == "__main__":
    main()
