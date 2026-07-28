"""Train an XGBoost v4 model with richer behavior features and two-stage review policy.

V4 adds two improvements over the optimized v3 branch:

1. Feature layer:
   - customer sequence features based only on prior transactions
   - category/channel switching signals
   - recent category/channel diversity
   - recent amount p99/max ratios
   - recent high-risk-category and wallet shares

2. Decision layer:
   - stage 1 ranks fraud probability
   - stage 2 ranks expected review value under cost/capacity assumptions

This keeps the thesis aligned with both fraud detection metrics and mechanism
design: a good model should not only classify, it should allocate analyst
attention under capacity constraints.
"""

from __future__ import annotations

import json
import math
from collections import Counter, deque
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
    outcome_metrics_from_review_flags,
    precision_recall_at_k,
    probability_threshold_policy,
    split_by_time,
    split_metrics,
    threshold_report,
    top_percentile_policy,
)
from train_simulation_xgboost_optimized import add_optimized_features, optimized_numeric_features


RATIO_WINDOWS = ["24h", "3d", "7d", "30d"]
SEQUENCE_WINDOWS = [5, 10, 20]
HIGH_RISK_CATEGORIES = {"electronics", "travel", "digital_wallet", "health"}


def entropy(values: list[str]) -> float:
    if not values:
        return 0.0
    total = len(values)
    counts = Counter(values)
    return float(-sum((count / total) * math.log(count / total + 1e-12) for count in counts.values()))


def add_sequence_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add prior-history behavior features without using current/future labels."""
    out = df.copy().reset_index(drop=True)
    out["__original_order"] = np.arange(len(out))
    out["timestamp_dt"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    out = out.sort_values(["scenario", "customer_id", "timestamp_dt", "transaction_id"]).reset_index(drop=True)

    feature_rows: list[dict[str, float]] = []
    for _, group in out.groupby(["scenario", "customer_id"], sort=False):
        recent_categories: deque[str] = deque(maxlen=max(SEQUENCE_WINDOWS))
        recent_channels: deque[str] = deque(maxlen=max(SEQUENCE_WINDOWS))
        recent_amounts: deque[float] = deque(maxlen=max(SEQUENCE_WINDOWS))

        prev_category = None
        prev_channel = None
        for _, row in group.iterrows():
            category = str(row.get("merchant_category", "unknown"))
            channel = str(row.get("channel", "unknown"))
            amount = float(row.get("amount", 0.0) or 0.0)

            recent_categories_list = list(recent_categories)
            recent_channels_list = list(recent_channels)
            recent_amounts_array = np.array(list(recent_amounts), dtype=float)

            features: dict[str, float] = {
                "category_switch_from_prev": float(prev_category is not None and category != prev_category),
                "channel_switch_from_prev": float(prev_channel is not None and channel != prev_channel),
                "has_prior_txn": float(prev_category is not None),
            }

            for window in SEQUENCE_WINDOWS:
                cats = recent_categories_list[-window:]
                chans = recent_channels_list[-window:]
                amts = recent_amounts_array[-window:] if len(recent_amounts_array) else np.array([], dtype=float)
                high_risk_count = sum(1 for item in cats if item in HIGH_RISK_CATEGORIES)
                wallet_count = sum(1 for item in chans if item == "wallet")
                card_present_count = sum(1 for item in chans if item == "card_present")

                p99 = float(np.percentile(amts, 99)) if len(amts) else 0.0
                max_amt = float(amts.max()) if len(amts) else 0.0
                avg_amt = float(amts.mean()) if len(amts) else 0.0

                features[f"recent_category_unique_{window}"] = float(len(set(cats))) if cats else 0.0
                features[f"recent_channel_unique_{window}"] = float(len(set(chans))) if chans else 0.0
                features[f"recent_category_entropy_{window}"] = entropy(cats)
                features[f"recent_high_risk_category_share_{window}"] = high_risk_count / max(1, len(cats))
                features[f"recent_wallet_share_{window}"] = wallet_count / max(1, len(chans))
                features[f"recent_card_present_share_{window}"] = card_present_count / max(1, len(chans))
                features[f"recent_amount_p99_{window}"] = p99
                features[f"recent_amount_max_{window}"] = max_amt
                features[f"amount_to_recent_p99_{window}"] = amount / (p99 + 1.0)
                features[f"log_amount_to_recent_p99_{window}"] = math.log1p(max(0.0, features[f"amount_to_recent_p99_{window}"]))
                features[f"amount_to_recent_max_{window}"] = amount / (max_amt + 1.0)
                features[f"amount_to_recent_avg_{window}"] = amount / (avg_amt + 1.0)

            feature_rows.append(features)
            recent_categories.append(category)
            recent_channels.append(channel)
            recent_amounts.append(amount)
            prev_category = category
            prev_channel = channel

    features_df = pd.DataFrame(feature_rows)
    out = pd.concat([out.reset_index(drop=True), features_df.reset_index(drop=True)], axis=1)
    out = out.sort_values("__original_order").reset_index(drop=True)
    return out.drop(columns=["timestamp_dt", "__original_order"], errors="ignore")


def add_v4_features(df: pd.DataFrame) -> pd.DataFrame:
    out = add_optimized_features(add_sequence_features(df))
    out["merchant_entropy_x_amount"] = out["recent_category_entropy_20"] * out["amount_anomaly_signal"]
    out["category_switch_x_merchant_risk"] = out["category_switch_from_prev"] * out["merchant_risk_signal"]
    out["channel_switch_x_velocity"] = out["channel_switch_from_prev"] * out["velocity_signal"]
    out["high_risk_share_x_amount"] = out["recent_high_risk_category_share_20"] * out["amount_anomaly_signal"]
    out["wallet_share_x_velocity"] = out["recent_wallet_share_20"] * out["velocity_signal"]
    return out


def v4_numeric_features(df: pd.DataFrame) -> list[str]:
    sequence = [
        "category_switch_from_prev",
        "channel_switch_from_prev",
        "has_prior_txn",
        "merchant_entropy_x_amount",
        "category_switch_x_merchant_risk",
        "channel_switch_x_velocity",
        "high_risk_share_x_amount",
        "wallet_share_x_velocity",
    ]
    for window in SEQUENCE_WINDOWS:
        sequence.extend(
            [
                f"recent_category_unique_{window}",
                f"recent_channel_unique_{window}",
                f"recent_category_entropy_{window}",
                f"recent_high_risk_category_share_{window}",
                f"recent_wallet_share_{window}",
                f"recent_card_present_share_{window}",
                f"recent_amount_p99_{window}",
                f"recent_amount_max_{window}",
                f"amount_to_recent_p99_{window}",
                f"log_amount_to_recent_p99_{window}",
                f"amount_to_recent_max_{window}",
                f"amount_to_recent_avg_{window}",
            ]
        )
    return [col for col in optimized_numeric_features(df) + sequence if col in df.columns]


def make_v4_matrix(train: pd.DataFrame, valid: pd.DataFrame, test: pd.DataFrame):
    train = add_v4_features(train)
    valid = add_v4_features(valid)
    test = add_v4_features(test)
    numeric_features = v4_numeric_features(train)

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
        "engineered_feature_note": "v4 sequence behavior features plus v3 amount/merchant/timing/velocity interactions",
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
    labels = [(0.005, "0_005"), (0.01, "0_01"), (0.03, "0_03"), (0.05, "0_05"), (0.10, "0_10")]
    for pct, label in labels:
        precision, recall, k = precision_recall_at_k(y, prob, int(len(y) * pct))
        rows[f"precision_top_{label}"] = precision
        rows[f"recall_top_{label}"] = recall
        rows[f"k_top_{label}"] = k
    return rows


def objective(row: dict[str, float]) -> float:
    return (
        row["valid_pr_auc"] * 1.15
        + row["valid_recall_top_0_05"] * 0.40
        + row["valid_recall_top_0_10"] * 0.20
        + row["valid_precision_top_0_01"] * 0.15
        - row["valid_brier"] * 0.10
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
    return model, row


def split_metric_rows(name: str, y: np.ndarray, prob: np.ndarray) -> list[dict[str, float | str]]:
    return split_metrics(name, y, prob)


def expected_value_policy(scored: pd.DataFrame, min_expected_value: float, costs: CostAssumptions, capacity_per_day: int):
    flags = pd.Series(False, index=scored.index)
    overflow = 0
    for _, group in scored.groupby(["scenario", "day_index"], sort=False):
        candidates = group[group["stage2_expected_review_value"] >= min_expected_value].sort_values(
            ["stage2_expected_review_value", "xgb_risk_probability"], ascending=False
        )
        selected = candidates.head(capacity_per_day).index
        overflow += max(0, len(candidates) - capacity_per_day)
        flags.loc[selected] = True
    return outcome_metrics_from_review_flags(scored, flags.tolist(), f"stage2_ev_threshold_{min_expected_value:.0f}", min_expected_value, costs, overflow)


def top_expected_value_policy(scored: pd.DataFrame, pct: float, costs: CostAssumptions, capacity_per_day: int):
    flags = pd.Series(False, index=scored.index)
    overflow = 0
    for _, group in scored.groupby(["scenario", "day_index"], sort=False):
        k = max(1, int(np.ceil(len(group) * pct)))
        candidates = group.sort_values(["stage2_expected_review_value", "xgb_risk_probability"], ascending=False).head(k)
        selected = candidates.head(capacity_per_day).index
        overflow += max(0, len(candidates) - capacity_per_day)
        flags.loc[selected] = True
    return outcome_metrics_from_review_flags(scored, flags.tolist(), f"stage2_ev_top_{pct:.1%}_daily", f"top_{pct:.1%}", costs, overflow)


def scenario_metrics(test_scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scenario, part in test_scored.groupby("scenario"):
        y = part["is_fraud"].to_numpy(int)
        p = part["xgb_risk_probability"].to_numpy(float)
        rows.append(
            {
                "scenario": scenario,
                "rows": int(len(part)),
                "fraud_count": int(y.sum()),
                "fraud_rate": float(y.mean()),
                "roc_auc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else np.nan,
                "pr_auc_average_precision": float(average_precision_score(y, p)) if y.sum() else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values("scenario")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "data" / "model_runs" / f"xgboost_v4_features_twostage_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(project_root)
    train, valid, test = split_by_time(df, valid_days=4, test_days=8)
    x_train, x_valid, x_test, feature_names, preprocessing = make_v4_matrix(train, valid, test)
    y_train = train["is_fraud"].to_numpy(int)
    y_valid = valid["is_fraud"].to_numpy(int)
    y_test = test["is_fraud"].to_numpy(int)
    scale_pos_weight = float((len(y_train) - y_train.sum()) / max(1, y_train.sum()))

    candidates = []
    for max_depth in [2, 3, 4]:
        for min_child_weight in [5, 10, 16]:
            for scale_multiplier in [1.0, 1.5]:
                candidates.append(
                    {
                        "n_estimators": 550,
                        "max_depth": max_depth,
                        "learning_rate": 0.022,
                        "subsample": 0.86,
                        "colsample_bytree": 0.86,
                        "min_child_weight": min_child_weight,
                        "reg_lambda": 9.0,
                        "reg_alpha": 0.6,
                        "gamma": 0.6,
                        "max_delta_step": 1,
                        "scale_pos_weight_multiplier": scale_multiplier,
                    }
                )
    candidates.extend(
        [
            {
                "n_estimators": 750,
                "max_depth": 2,
                "learning_rate": 0.014,
                "subsample": 0.82,
                "colsample_bytree": 0.88,
                "min_child_weight": 8,
                "reg_lambda": 12.0,
                "reg_alpha": 0.8,
                "gamma": 0.9,
                "max_delta_step": 1,
                "scale_pos_weight_multiplier": 1.5,
            },
            {
                "n_estimators": 420,
                "max_depth": 3,
                "learning_rate": 0.032,
                "subsample": 0.90,
                "colsample_bytree": 0.90,
                "min_child_weight": 8,
                "reg_lambda": 7.0,
                "reg_alpha": 0.4,
                "gamma": 0.4,
                "max_delta_step": 1,
                "scale_pos_weight_multiplier": 2.0,
            },
        ]
    )

    best_model = None
    best_row = None
    tuning_rows = []
    for i, params in enumerate(candidates, start=1):
        model, row = train_candidate(params, x_train, y_train, x_valid, y_valid, scale_pos_weight)
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
    metrics.extend(split_metric_rows("train", y_train, train_prob))
    metrics.extend(split_metric_rows("valid", y_valid, valid_prob))
    metrics.extend(split_metric_rows("test", y_test, test_prob))

    threshold_df = threshold_report(y_valid, valid_prob)
    threshold_candidates = sorted(
        set([0.01, 0.03, 0.05, 0.10, 0.20] + threshold_df.get("threshold_probability", pd.Series(dtype=float)).dropna().astype(float).tolist())
    )

    score_cols = ["transaction_id", "customer_id", "card_id", "scenario", "day_index", "timestamp", "amount", "hour", "merchant_category", "channel", "is_fraud"]
    scored_parts = []
    costs = CostAssumptions()
    for split_name, part, prob in [("train", train, train_prob), ("valid", valid, valid_prob), ("test", test, test_prob)]:
        out = part[score_cols].copy()
        out["split"] = split_name
        out["xgb_risk_probability"] = prob
        out["xgb_risk_score"] = np.rint(prob * 100).clip(0, 100).astype(int)
        expected_recovery = out["xgb_risk_probability"] * out["amount"] * costs.fraud_recovery_rate
        false_positive_drag = (1.0 - out["xgb_risk_probability"]) * (costs.false_positive_fixed_cost + out["amount"] * costs.false_positive_variable_rate)
        out["stage2_expected_review_value"] = expected_recovery - false_positive_drag - costs.analyst_cost_per_review
        out["stage2_expected_loss"] = out["xgb_risk_probability"] * out["amount"] * (1.0 - costs.fraud_recovery_rate)
        scored_parts.append(out)
    all_scores = pd.concat(scored_parts, ignore_index=True)
    test_scored = all_scores[all_scores["split"] == "test"].copy()

    policy_rows = [
        top_percentile_policy(test_scored, 0.005, costs, 100),
        top_percentile_policy(test_scored, 0.01, costs, 100),
        top_percentile_policy(test_scored, 0.03, costs, 100),
        top_percentile_policy(test_scored, 0.05, costs, 100),
        top_percentile_policy(test_scored, 0.10, costs, 100),
    ]
    policy_rows.extend(probability_threshold_policy(test_scored, threshold, costs, 100) for threshold in threshold_candidates)

    ev_thresholds = sorted(set([0.0, 5.0, 10.0, 25.0, 50.0] + [float(test_scored["stage2_expected_review_value"].quantile(q)) for q in [0.90, 0.95, 0.97, 0.99]]))
    policy_rows.extend(expected_value_policy(test_scored, threshold, costs, 100) for threshold in ev_thresholds)
    policy_rows.extend(top_expected_value_policy(test_scored, pct, costs, 100) for pct in [0.005, 0.01, 0.03, 0.05, 0.10])
    policy_df = pd.DataFrame(policy_rows).sort_values("net_benefit", ascending=False)

    importance = pd.DataFrame({"feature": feature_names, "importance_gain": best_model.feature_importances_}).sort_values("importance_gain", ascending=False)
    scenario_df = scenario_metrics(test_scored)

    pd.DataFrame(tuning_rows).sort_values("selection_objective", ascending=False).to_csv(output_dir / "xgb_v4_tuning_results.csv", index=False)
    pd.DataFrame(metrics).to_csv(output_dir / "xgb_v4_model_metrics.csv", index=False)
    threshold_df.to_csv(output_dir / "xgb_v4_threshold_report.csv", index=False)
    scenario_df.to_csv(output_dir / "xgb_v4_scenario_metrics.csv", index=False)
    policy_df.to_csv(output_dir / "xgb_v4_policy_comparison.csv", index=False)
    all_scores.to_csv(output_dir / "xgb_v4_model_scores.csv", index=False)
    importance.to_csv(output_dir / "xgb_v4_feature_importance.csv", index=False)
    joblib.dump(best_model, output_dir / "xgb_v4_simulation_model.joblib")
    (output_dir / "xgb_v4_metadata.json").write_text(
        json.dumps(
            {
                "model_type": "XGBClassifier",
                "version": "v4_features_twostage",
                "selection_metric": "validation PR-AUC + recall@5% + recall@10% + precision@1% - brier",
                "stage2_policy": "expected review value = p(fraud)*amount*recovery - p(nonfraud)*false_positive_cost - analyst_cost",
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
    print("Scenario metrics:")
    print(scenario_df.to_string(index=False))
    print("Top policies by net benefit:")
    print(policy_df.head(12).to_string(index=False))
    print("Feature importance:")
    print(importance.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
