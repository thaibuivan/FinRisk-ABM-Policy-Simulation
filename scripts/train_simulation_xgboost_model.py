"""Train an XGBoost risk model on the thesis simulation data.

This is the stronger model branch for the FinRisk thesis project. It does not
reuse old RiskGuard model weights; it trains a new model on simulation-native
transactions and behavior features, then evaluates both ML metrics and
policy/outcome metrics.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_curve, roc_auc_score
from xgboost import XGBClassifier


SCENARIO_NAMES = ["low_fraud", "baseline", "stress_fraud", "low_capacity", "high_capacity"]

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
    matches = sorted(runs_dir.glob(f"{scenario_name}_*"), key=lambda path: path.stat().st_mtime, reverse=True)
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


def load_dataset(project_root: Path) -> pd.DataFrame:
    runs_dir = project_root / "data" / "simulation_runs"
    frames = [load_run(latest_run_dir(runs_dir, scenario), scenario) for scenario in SCENARIO_NAMES]
    return pd.concat(frames, ignore_index=True)


def split_by_time(df: pd.DataFrame, valid_days: int, test_days: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    max_day = df.groupby("run_dir")["day_index"].transform("max")
    test_mask = df["day_index"] > (max_day - test_days)
    valid_mask = (df["day_index"] > (max_day - test_days - valid_days)) & ~test_mask
    train = df.loc[~valid_mask & ~test_mask].copy()
    valid = df.loc[valid_mask].copy()
    test = df.loc[test_mask].copy()
    for name, part in [("train", train), ("valid", valid), ("test", test)]:
        if part["is_fraud"].sum() == 0:
            raise RuntimeError(f"{name} split has no fraud examples")
    return train, valid, test


def make_matrix(train: pd.DataFrame, valid: pd.DataFrame, test: pd.DataFrame):
    medians = train[NUMERIC_FEATURES].replace([np.inf, -np.inf], np.nan).median(numeric_only=True).fillna(0.0)
    parts_num = []
    for part in [train, valid, test]:
        parts_num.append(part[NUMERIC_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(medians).reset_index(drop=True))

    cat_all = pd.concat([train[CATEGORICAL_FEATURES], valid[CATEGORICAL_FEATURES], test[CATEGORICAL_FEATURES]], ignore_index=True).fillna("unknown")
    encoded = pd.get_dummies(cat_all, columns=CATEGORICAL_FEATURES, prefix=CATEGORICAL_FEATURES, dtype=float)
    n_train, n_valid = len(train), len(valid)
    train_cat = encoded.iloc[:n_train].reset_index(drop=True)
    valid_cat = encoded.iloc[n_train : n_train + n_valid].reset_index(drop=True)
    test_cat = encoded.iloc[n_train + n_valid :].reset_index(drop=True)

    x_train = pd.concat([parts_num[0], train_cat], axis=1)
    x_valid = pd.concat([parts_num[1], valid_cat], axis=1)
    x_test = pd.concat([parts_num[2], test_cat], axis=1)
    feature_names = list(x_train.columns)
    metadata = {
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_medians": {k: float(v) for k, v in medians.items()},
        "feature_names": feature_names,
    }
    return (
        x_train.to_numpy(np.float32),
        x_valid.to_numpy(np.float32),
        x_test.to_numpy(np.float32),
        feature_names,
        metadata,
    )


def precision_recall_at_k(y: np.ndarray, score: np.ndarray, k: int) -> tuple[float, float, int]:
    k = max(1, min(int(k), len(y)))
    idx = np.argsort(-score)[:k]
    tp = float(y[idx].sum())
    return tp / k, tp / max(1.0, float(y.sum())), k


def split_metrics(name: str, y: np.ndarray, prob: np.ndarray) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = [
        {
            "split": name,
            "rows": int(len(y)),
            "fraud_count": int(y.sum()),
            "fraud_rate": float(y.mean()),
            "roc_auc": float(roc_auc_score(y, prob)),
            "pr_auc_average_precision": float(average_precision_score(y, prob)),
            "brier_score": float(brier_score_loss(y, prob)),
            "mean_probability": float(prob.mean()),
        }
    ]
    for pct in [0.005, 0.01, 0.03, 0.05, 0.10]:
        precision, recall, k = precision_recall_at_k(y, prob, int(len(y) * pct))
        rows.append(
            {
                "split": f"{name}_top_{pct:.1%}",
                "rows": k,
                "fraud_count": int(y.sum()),
                "fraud_rate": float(y.mean()),
                "precision_at_k": precision,
                "recall_at_k": recall,
            }
        )
    return rows


def threshold_report(y: np.ndarray, prob: np.ndarray) -> pd.DataFrame:
    precision, recall, thresholds = precision_recall_curve(y, prob)
    rows = []
    for min_precision in [0.05, 0.10, 0.20, 0.30, 0.40, 0.50]:
        valid = np.where(precision[:-1] >= min_precision)[0]
        if len(valid) == 0:
            continue
        idx = valid[np.argmax(recall[:-1][valid])]
        rows.append(
            {
                "criterion": f"max_recall_at_precision_{min_precision:.2f}",
                "threshold_probability": float(thresholds[idx]),
                "precision": float(precision[idx]),
                "recall": float(recall[idx]),
            }
        )
    return pd.DataFrame(rows)


def outcome_metrics_from_review_flags(scored: pd.DataFrame, reviewed_flags: list[bool], policy_name: str, policy_value: str | int | float, costs: CostAssumptions, overflow_total: int):
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
        "policy_value": policy_value,
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


def probability_threshold_policy(scored: pd.DataFrame, threshold: float, costs: CostAssumptions, capacity_per_day: int):
    flags = pd.Series(False, index=scored.index)
    overflow = 0
    for _, group in scored.groupby(["scenario", "day_index"], sort=False):
        candidates = group[group["xgb_risk_probability"] >= threshold].sort_values("xgb_risk_probability", ascending=False)
        selected = candidates.head(capacity_per_day).index
        overflow += max(0, len(candidates) - capacity_per_day)
        flags.loc[selected] = True
    return outcome_metrics_from_review_flags(scored, flags.tolist(), f"xgb_threshold_{threshold:.3f}", threshold, costs, overflow)


def top_percentile_policy(scored: pd.DataFrame, pct: float, costs: CostAssumptions, capacity_per_day: int):
    flags = pd.Series(False, index=scored.index)
    overflow = 0
    for _, group in scored.groupby(["scenario", "day_index"], sort=False):
        k = max(1, int(np.ceil(len(group) * pct)))
        candidates = group.sort_values("xgb_risk_probability", ascending=False).head(k)
        selected = candidates.head(capacity_per_day).index
        overflow += max(0, len(candidates) - capacity_per_day)
        flags.loc[selected] = True
    return outcome_metrics_from_review_flags(scored, flags.tolist(), f"xgb_top_{pct:.1%}_daily", f"top_{pct:.1%}", costs, overflow)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--valid-days", type=int, default=4)
    parser.add_argument("--test-days", type=int, default=8)
    parser.add_argument("--capacity-per-day", type=int, default=100)
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    args = parser.parse_args()

    project_root = args.project_root
    output_dir = project_root / "data" / "model_runs" / f"xgboost_simulation_risk_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(project_root)
    train, valid, test = split_by_time(df, args.valid_days, args.test_days)
    x_train, x_valid, x_test, feature_names, preprocessing = make_matrix(train, valid, test)
    y_train = train["is_fraud"].to_numpy(int)
    y_valid = valid["is_fraud"].to_numpy(int)
    y_test = test["is_fraud"].to_numpy(int)
    scale_pos_weight = float((len(y_train) - y_train.sum()) / max(1, y_train.sum()))

    model = XGBClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
        subsample=0.90,
        colsample_bytree=0.90,
        min_child_weight=5,
        reg_lambda=5.0,
        reg_alpha=0.2,
        objective="binary:logistic",
        eval_metric="aucpr",
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
        scale_pos_weight=scale_pos_weight,
    )
    model.fit(x_train, y_train, eval_set=[(x_valid, y_valid)], verbose=False)

    train_prob = model.predict_proba(x_train)[:, 1]
    valid_prob = model.predict_proba(x_valid)[:, 1]
    test_prob = model.predict_proba(x_test)[:, 1]

    metrics = []
    metrics.extend(split_metrics("train", y_train, train_prob))
    metrics.extend(split_metrics("valid", y_valid, valid_prob))
    metrics.extend(split_metrics("test", y_test, test_prob))

    threshold_df = threshold_report(y_valid, valid_prob)
    threshold_candidates = sorted(set([0.01, 0.03, 0.05, 0.10, 0.20] + threshold_df.get("threshold_probability", pd.Series(dtype=float)).dropna().astype(float).tolist()))

    score_cols = ["transaction_id", "customer_id", "card_id", "scenario", "day_index", "timestamp", "amount", "hour", "merchant_category", "channel", "is_fraud"]
    scored_parts = []
    for split_name, part, prob in [
        ("train", train, train_prob),
        ("valid", valid, valid_prob),
        ("test", test, test_prob),
    ]:
        out = part[score_cols].copy()
        out["split"] = split_name
        out["xgb_risk_probability"] = prob
        out["xgb_risk_score"] = np.rint(prob * 100).clip(0, 100).astype(int)
        scored_parts.append(out)
    all_scores = pd.concat(scored_parts, ignore_index=True)

    test_scored = all_scores[all_scores["split"] == "test"].copy()
    costs = CostAssumptions()
    policy_rows = [
        top_percentile_policy(test_scored, 0.005, costs, args.capacity_per_day),
        top_percentile_policy(test_scored, 0.01, costs, args.capacity_per_day),
        top_percentile_policy(test_scored, 0.03, costs, args.capacity_per_day),
        top_percentile_policy(test_scored, 0.05, costs, args.capacity_per_day),
    ]
    policy_rows.extend(
        probability_threshold_policy(test_scored, threshold, costs, args.capacity_per_day)
        for threshold in threshold_candidates
    )
    policy_df = pd.DataFrame(policy_rows).sort_values("net_benefit", ascending=False)

    importance = pd.DataFrame(
        {
            "feature": feature_names,
            "importance_gain": model.feature_importances_,
        }
    ).sort_values("importance_gain", ascending=False)

    pd.DataFrame(metrics).to_csv(output_dir / "xgb_model_metrics.csv", index=False)
    threshold_df.to_csv(output_dir / "xgb_validation_threshold_report.csv", index=False)
    policy_df.to_csv(output_dir / "xgb_policy_comparison.csv", index=False)
    all_scores.to_csv(output_dir / "xgb_model_scores.csv", index=False)
    importance.to_csv(output_dir / "xgb_feature_importance.csv", index=False)
    joblib.dump(model, output_dir / "xgb_simulation_model.joblib")
    (output_dir / "xgb_model_metadata.json").write_text(
        json.dumps(
            {
                "model_type": "XGBClassifier",
                "scenario_names": SCENARIO_NAMES,
                "train_rows": int(len(train)),
                "valid_rows": int(len(valid)),
                "test_rows": int(len(test)),
                "train_fraud_count": int(y_train.sum()),
                "valid_fraud_count": int(y_valid.sum()),
                "test_fraud_count": int(y_test.sum()),
                "scale_pos_weight": scale_pos_weight,
                "cost_assumptions": asdict(costs),
                "preprocessing": preprocessing,
                "params": model.get_params(),
                "output_files": [
                    "xgb_model_metrics.csv",
                    "xgb_validation_threshold_report.csv",
                    "xgb_policy_comparison.csv",
                    "xgb_model_scores.csv",
                    "xgb_feature_importance.csv",
                    "xgb_simulation_model.joblib",
                    "xgb_model_metadata.json",
                ],
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print(f"Output: {output_dir}")
    print(pd.DataFrame(metrics).query("split in ['test', 'test_top_0.5%', 'test_top_1.0%', 'test_top_3.0%', 'test_top_5.0%']").to_string(index=False))
    print(policy_df.head(8).to_string(index=False))
    print(importance.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
