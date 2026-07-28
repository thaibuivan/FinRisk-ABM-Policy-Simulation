"""Tune an XGBoost model for PR-AUC and recall on simulation-native fraud data.

This script is intentionally focused on fraud-detection metrics:

- PR-AUC / average precision
- recall at top-k review budget
- precision at top-k as a workload sanity check

Net benefit is still reported, but it is not the primary model-selection metric.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from xgboost import XGBClassifier

from train_simulation_xgboost_model import (
    CATEGORICAL_FEATURES,
    CostAssumptions,
    NUMERIC_FEATURES,
    SCENARIO_NAMES,
    load_dataset,
    probability_threshold_policy,
    precision_recall_at_k,
    split_by_time,
    split_metrics,
    threshold_report,
    top_percentile_policy,
)


RATIO_WINDOWS = ["24h", "3d", "7d", "30d"]
EPS = 1e-6


def add_optimized_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["is_night_hour"] = out["hour"].isin([22, 23, 0, 1, 2, 3, 4, 5]).astype(float)
    out["log_gap_minutes"] = np.log1p(out["gap_minutes_since_prev"].clip(lower=0))
    out["short_gap_signal"] = (out["gap_minutes_since_prev"] <= 10).astype(float)

    for window in RATIO_WINDOWS:
        for base in ["avg", "median", "p95"]:
            col = f"{base}_amount_{window}"
            if col in out.columns:
                out[f"amount_to_{base}_{window}"] = out["amount"] / (out[col].fillna(0).clip(lower=0) + 1.0)
                out[f"log_amount_to_{base}_{window}"] = np.log1p(out[f"amount_to_{base}_{window}"].clip(lower=0))
        count_col = f"txn_count_{window}"
        total_col = f"total_amount_{window}"
        if count_col in out.columns:
            out[f"log_txn_count_{window}"] = np.log1p(out[count_col].fillna(0).clip(lower=0))
        if total_col in out.columns:
            out[f"log_total_amount_{window}"] = np.log1p(out[total_col].fillna(0).clip(lower=0))

    out["amount_x_merchant_risk"] = out["amount_anomaly_signal"] * out["merchant_risk_signal"]
    out["amount_x_velocity"] = out["amount_anomaly_signal"] * out["velocity_signal"]
    out["night_x_velocity"] = out["is_night_hour"] * out["velocity_signal"]
    out["night_x_amount"] = out["is_night_hour"] * out["amount_anomaly_signal"]
    out["merchant_x_unusual_hour"] = out["merchant_risk_signal"] * out["unusual_hour_signal"]
    return out


def optimized_numeric_features(df: pd.DataFrame) -> list[str]:
    engineered = [
        "is_night_hour",
        "log_gap_minutes",
        "short_gap_signal",
        "amount_x_merchant_risk",
        "amount_x_velocity",
        "night_x_velocity",
        "night_x_amount",
        "merchant_x_unusual_hour",
    ]
    for window in RATIO_WINDOWS:
        engineered.extend(
            [
                f"amount_to_avg_{window}",
                f"log_amount_to_avg_{window}",
                f"amount_to_median_{window}",
                f"log_amount_to_median_{window}",
                f"amount_to_p95_{window}",
                f"log_amount_to_p95_{window}",
                f"log_txn_count_{window}",
                f"log_total_amount_{window}",
            ]
        )
    return [col for col in NUMERIC_FEATURES + engineered if col in df.columns]


def make_optimized_matrix(train: pd.DataFrame, valid: pd.DataFrame, test: pd.DataFrame):
    train = add_optimized_features(train)
    valid = add_optimized_features(valid)
    test = add_optimized_features(test)
    numeric_features = optimized_numeric_features(train)

    medians = train[numeric_features].replace([np.inf, -np.inf], np.nan).median(numeric_only=True).fillna(0.0)
    parts_num = []
    for part in [train, valid, test]:
        parts_num.append(part[numeric_features].replace([np.inf, -np.inf], np.nan).fillna(medians).reset_index(drop=True))

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
        "numeric_features": numeric_features,
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_medians": {k: float(v) for k, v in medians.items()},
        "feature_names": feature_names,
        "engineered_feature_note": "amount/behavior ratios, short-gap signal, night-hour signal, and risk-signal interactions",
    }
    return (
        x_train.to_numpy(np.float32),
        x_valid.to_numpy(np.float32),
        x_test.to_numpy(np.float32),
        feature_names,
        metadata,
    )


def topk_summary(y: np.ndarray, prob: np.ndarray) -> dict[str, float]:
    rows: dict[str, float] = {}
    labels = [
        (0.005, "0_005"),
        (0.01, "0_01"),
        (0.03, "0_03"),
        (0.05, "0_05"),
        (0.10, "0_10"),
    ]
    for pct, label in labels:
        precision, recall, k = precision_recall_at_k(y, prob, int(len(y) * pct))
        rows[f"precision_top_{label}"] = precision
        rows[f"recall_top_{label}"] = recall
        rows[f"k_top_{label}"] = k
    return rows


def objective(row: dict[str, float]) -> float:
    # PR-AUC is primary; recall@5% matters because fraud loss is costly;
    # precision@1% prevents choosing a model that floods analysts with poor top alerts.
    return (
        row["valid_pr_auc"] * 1.00
        + row["valid_recall_top_0_05"] * 0.45
        + row["valid_recall_top_0_10"] * 0.20
        + row["valid_precision_top_0_01"] * 0.15
    )


def train_candidate(params: dict, x_train, y_train, x_valid, y_valid, scale_pos_weight: float):
    model = XGBClassifier(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        learning_rate=params["learning_rate"],
        subsample=params["subsample"],
        colsample_bytree=params["colsample_bytree"],
        min_child_weight=params["min_child_weight"],
        reg_lambda=params["reg_lambda"],
        reg_alpha=params["reg_alpha"],
        gamma=params["gamma"],
        max_delta_step=params["max_delta_step"],
        objective="binary:logistic",
        eval_metric="aucpr",
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
        scale_pos_weight=scale_pos_weight * params["scale_pos_weight_multiplier"],
    )
    model.fit(x_train, y_train, eval_set=[(x_valid, y_valid)], verbose=False)
    valid_prob = model.predict_proba(x_valid)[:, 1]
    row = {
        **params,
        "valid_roc_auc": float(roc_auc_score(y_valid, valid_prob)),
        "valid_pr_auc": float(average_precision_score(y_valid, valid_prob)),
        "valid_brier": float(brier_score_loss(y_valid, valid_prob)),
        "valid_mean_probability": float(valid_prob.mean()),
        **{f"valid_{k}": v for k, v in topk_summary(y_valid, valid_prob).items()},
    }
    row["selection_objective"] = objective(row)
    return model, valid_prob, row


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "data" / "model_runs" / f"xgboost_optimized_recall_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(project_root)
    train, valid, test = split_by_time(df, valid_days=4, test_days=8)
    x_train, x_valid, x_test, feature_names, preprocessing = make_optimized_matrix(train, valid, test)
    y_train = train["is_fraud"].to_numpy(int)
    y_valid = valid["is_fraud"].to_numpy(int)
    y_test = test["is_fraud"].to_numpy(int)
    scale_pos_weight = float((len(y_train) - y_train.sum()) / max(1, y_train.sum()))

    candidates = []
    for max_depth in [2, 3]:
        for min_child_weight in [5, 12]:
            for scale_multiplier in [1.0, 1.5, 2.0]:
                candidates.append(
                    {
                        "n_estimators": 500,
                        "max_depth": max_depth,
                        "learning_rate": 0.025,
                        "subsample": 0.85,
                        "colsample_bytree": 0.85,
                        "min_child_weight": min_child_weight,
                        "reg_lambda": 8.0,
                        "reg_alpha": 0.5,
                        "gamma": 0.5,
                        "max_delta_step": 1,
                        "scale_pos_weight_multiplier": scale_multiplier,
                    }
                )
    candidates.extend(
        [
            {
                "n_estimators": 700,
                "max_depth": 2,
                "learning_rate": 0.015,
                "subsample": 0.80,
                "colsample_bytree": 0.85,
                "min_child_weight": 8,
                "reg_lambda": 10.0,
                "reg_alpha": 0.8,
                "gamma": 0.8,
                "max_delta_step": 1,
                "scale_pos_weight_multiplier": 1.5,
            },
            {
                "n_estimators": 350,
                "max_depth": 3,
                "learning_rate": 0.035,
                "subsample": 0.90,
                "colsample_bytree": 0.90,
                "min_child_weight": 10,
                "reg_lambda": 8.0,
                "reg_alpha": 0.5,
                "gamma": 0.5,
                "max_delta_step": 1,
                "scale_pos_weight_multiplier": 2.0,
            },
        ]
    )

    best_model = None
    best_row = None
    tuning_rows = []
    for i, params in enumerate(candidates, start=1):
        model, _, row = train_candidate(params, x_train, y_train, x_valid, y_valid, scale_pos_weight)
        row["candidate_id"] = i
        tuning_rows.append(row)
        if best_row is None or row["selection_objective"] > best_row["selection_objective"]:
            best_model = model
            best_row = row
        print(
            f"{i:02d}/{len(candidates)} valid_pr_auc={row['valid_pr_auc']:.4f} "
            f"recall@5%={row['valid_recall_top_0_05']:.4f} "
            f"precision@1%={row['valid_precision_top_0_01']:.4f} "
            f"objective={row['selection_objective']:.4f}"
        )

    assert best_model is not None and best_row is not None
    train_prob = best_model.predict_proba(x_train)[:, 1]
    valid_prob = best_model.predict_proba(x_valid)[:, 1]
    test_prob = best_model.predict_proba(x_test)[:, 1]

    metrics = []
    metrics.extend(split_metrics("train", y_train, train_prob))
    metrics.extend(split_metrics("valid", y_valid, valid_prob))
    metrics.extend(split_metrics("test", y_test, test_prob))

    threshold_df = threshold_report(y_valid, valid_prob)
    threshold_candidates = sorted(
        set([0.01, 0.03, 0.05, 0.10, 0.20] + threshold_df.get("threshold_probability", pd.Series(dtype=float)).dropna().astype(float).tolist())
    )

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
        top_percentile_policy(test_scored, 0.005, costs, 100),
        top_percentile_policy(test_scored, 0.01, costs, 100),
        top_percentile_policy(test_scored, 0.03, costs, 100),
        top_percentile_policy(test_scored, 0.05, costs, 100),
        top_percentile_policy(test_scored, 0.10, costs, 100),
    ]
    policy_rows.extend(probability_threshold_policy(test_scored, threshold, costs, 100) for threshold in threshold_candidates)
    policy_df = pd.DataFrame(policy_rows).sort_values("recall_reviewed", ascending=False)

    importance = pd.DataFrame(
        {
            "feature": feature_names,
            "importance_gain": best_model.feature_importances_,
        }
    ).sort_values("importance_gain", ascending=False)

    pd.DataFrame(tuning_rows).sort_values("selection_objective", ascending=False).to_csv(output_dir / "xgb_tuning_results.csv", index=False)
    pd.DataFrame(metrics).to_csv(output_dir / "xgb_optimized_model_metrics.csv", index=False)
    threshold_df.to_csv(output_dir / "xgb_optimized_threshold_report.csv", index=False)
    policy_df.to_csv(output_dir / "xgb_optimized_policy_comparison.csv", index=False)
    all_scores.to_csv(output_dir / "xgb_optimized_model_scores.csv", index=False)
    importance.to_csv(output_dir / "xgb_optimized_feature_importance.csv", index=False)
    joblib.dump(best_model, output_dir / "xgb_optimized_simulation_model.joblib")
    (output_dir / "xgb_optimized_metadata.json").write_text(
        json.dumps(
            {
                "model_type": "XGBClassifier",
                "selection_metric": "validation PR-AUC + recall@5% + recall@10% + precision@1%",
                "scenario_names": SCENARIO_NAMES,
                "train_rows": int(len(train)),
                "valid_rows": int(len(valid)),
                "test_rows": int(len(test)),
                "train_fraud_count": int(y_train.sum()),
                "valid_fraud_count": int(y_valid.sum()),
                "test_fraud_count": int(y_test.sum()),
                "base_scale_pos_weight": scale_pos_weight,
                "best_validation_row": best_row,
                "best_params": best_model.get_params(),
                "cost_assumptions": asdict(costs),
                "preprocessing": preprocessing,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    metric_df = pd.DataFrame(metrics)
    print(f"Output: {output_dir}")
    print("Best validation candidate:")
    print(pd.DataFrame([best_row]).to_string(index=False))
    print("Test metrics:")
    print(metric_df.query("split in ['test', 'test_top_0.5%', 'test_top_1.0%', 'test_top_3.0%', 'test_top_5.0%', 'test_top_10.0%']").to_string(index=False))
    print("Policy by recall:")
    print(policy_df.head(8).to_string(index=False))
    print("Feature importance:")
    print(importance.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
