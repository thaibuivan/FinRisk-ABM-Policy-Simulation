"""Train a true two-stage XGBoost fraud decisioning pipeline.

Stage 1:
    High-recall screening model over all transactions.

Stage 2:
    False-positive reduction model trained only on high-risk candidates from
    Stage 1. It uses Stage-1 probability plus behavior/cost features to rerank
    candidates before analyst review.

This is different from v4's expected-value rule. V5 has a second ML model.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from xgboost import XGBClassifier

from train_simulation_xgboost_model import (
    CATEGORICAL_FEATURES,
    CostAssumptions,
    SCENARIO_NAMES,
    load_dataset,
    outcome_metrics_from_review_flags,
    precision_recall_at_k,
    split_by_time,
    split_metrics,
    top_percentile_policy,
)
from train_simulation_xgboost_v4_features_twostage import add_v4_features, v4_numeric_features


STAGE1_CANDIDATE_PCT = 0.10
FINAL_REVIEW_PCTS = [0.005, 0.01, 0.03, 0.05]
SCORE_COLS = [
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


def temporal_train_internal_split(train: pd.DataFrame, holdout_days: int = 8) -> tuple[pd.DataFrame, pd.DataFrame]:
    max_day = train.groupby("run_dir")["day_index"].transform("max")
    s2_mask = train["day_index"] > (max_day - holdout_days)
    s1_train = train.loc[~s2_mask].copy()
    s2_train = train.loc[s2_mask].copy()
    if s1_train["is_fraud"].sum() == 0 or s2_train["is_fraud"].sum() == 0:
        raise RuntimeError("Internal train split has no fraud examples in one side")
    return s1_train, s2_train


def prepare_feature_frames(parts: Iterable[pd.DataFrame], fit_reference: pd.DataFrame):
    prepared = [add_v4_features(part) for part in parts]
    fit_prepared = add_v4_features(fit_reference)
    numeric_features = v4_numeric_features(fit_prepared)
    medians = fit_prepared[numeric_features].replace([np.inf, -np.inf], np.nan).median(numeric_only=True).fillna(0.0)

    num_frames = [
        part[numeric_features].replace([np.inf, -np.inf], np.nan).fillna(medians).reset_index(drop=True)
        for part in prepared
    ]
    cat_all = pd.concat([part[CATEGORICAL_FEATURES] for part in prepared], ignore_index=True).fillna("unknown")
    encoded = pd.get_dummies(cat_all, columns=CATEGORICAL_FEATURES, prefix=CATEGORICAL_FEATURES, dtype=float)

    cat_frames = []
    cursor = 0
    for part in prepared:
        size = len(part)
        cat_frames.append(encoded.iloc[cursor : cursor + size].reset_index(drop=True))
        cursor += size

    matrices = [pd.concat([num, cat], axis=1) for num, cat in zip(num_frames, cat_frames)]
    feature_names = list(matrices[0].columns)
    preprocessing = {
        "numeric_features": numeric_features,
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_medians": {key: float(value) for key, value in medians.items()},
        "feature_names": feature_names,
    }
    return prepared, matrices, preprocessing


def add_stage1_scores(df: pd.DataFrame, stage1_prob: np.ndarray, costs: CostAssumptions) -> pd.DataFrame:
    out = df[SCORE_COLS].copy().reset_index(drop=True)
    out["stage1_probability"] = stage1_prob
    out["stage1_score"] = np.rint(stage1_prob * 100).clip(0, 100).astype(int)
    out["stage1_expected_review_value"] = (
        out["stage1_probability"] * out["amount"] * costs.fraud_recovery_rate
        - (1.0 - out["stage1_probability"])
        * (costs.false_positive_fixed_cost + out["amount"] * costs.false_positive_variable_rate)
        - costs.analyst_cost_per_review
    )
    out["stage1_expected_loss"] = out["stage1_probability"] * out["amount"] * (1.0 - costs.fraud_recovery_rate)
    out["stage1_rank_pct_daily"] = (
        out.groupby(["scenario", "day_index"])["stage1_probability"]
        .rank(method="first", ascending=False, pct=True)
        .astype(float)
    )
    return out


def mark_stage1_candidates(scored: pd.DataFrame, candidate_pct: float) -> pd.DataFrame:
    out = scored.copy()
    out["stage1_candidate"] = False
    for _, group in out.groupby(["scenario", "day_index"], sort=False):
        k = max(1, int(np.ceil(len(group) * candidate_pct)))
        idx = group.sort_values("stage1_probability", ascending=False).head(k).index
        out.loc[idx, "stage1_candidate"] = True
    return out


def candidate_capture(scored: pd.DataFrame, label: str) -> dict[str, float | str]:
    candidates = scored["stage1_candidate"].astype(bool)
    fraud = scored["is_fraud"].astype(bool)
    tp = int((candidates & fraud).sum())
    candidate_count = int(candidates.sum())
    fraud_count = int(fraud.sum())
    return {
        "policy": label,
        "rows": int(len(scored)),
        "candidate_count": candidate_count,
        "fraud_count": fraud_count,
        "candidate_rate": candidate_count / max(1, len(scored)),
        "candidate_precision": tp / max(1, candidate_count),
        "candidate_recall": tp / max(1, fraud_count),
    }


def build_stage2_matrix(
    base_matrix: pd.DataFrame,
    stage1_scored: pd.DataFrame,
    fit_medians: pd.Series | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    base = base_matrix.replace([np.inf, -np.inf], np.nan).reset_index(drop=True)
    extra = stage1_scored[
        [
            "stage1_probability",
            "stage1_score",
            "stage1_expected_review_value",
            "stage1_expected_loss",
            "stage1_rank_pct_daily",
        ]
    ].reset_index(drop=True)
    matrix = pd.concat([base, extra], axis=1)
    if fit_medians is None:
        fit_medians = matrix.median(numeric_only=True).fillna(0.0)
    return matrix.fillna(fit_medians), fit_medians


def train_stage1(x_train, y_train):
    scale_pos_weight = float((len(y_train) - y_train.sum()) / max(1, y_train.sum()))
    model = XGBClassifier(
        n_estimators=550,
        max_depth=4,
        learning_rate=0.022,
        subsample=0.86,
        colsample_bytree=0.86,
        min_child_weight=16,
        reg_lambda=9.0,
        reg_alpha=0.6,
        gamma=0.6,
        max_delta_step=1,
        objective="binary:logistic",
        eval_metric="aucpr",
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
        scale_pos_weight=scale_pos_weight,
    )
    model.fit(x_train, y_train, verbose=False)
    return model, scale_pos_weight


def stage2_objective(row: dict[str, float]) -> float:
    return (
        row["valid_candidate_pr_auc"] * 1.0
        + row["valid_candidate_recall_top_0_50"] * 0.25
        + row["valid_candidate_precision_top_0_25"] * 0.20
        - row["valid_candidate_brier"] * 0.05
    )


def candidate_topk(y: np.ndarray, prob: np.ndarray, pct: float) -> tuple[float, float, int]:
    return precision_recall_at_k(y, prob, max(1, int(len(y) * pct)))


def train_stage2_candidates(x_train, y_train, x_valid, y_valid):
    scale_pos_weight = float((len(y_train) - y_train.sum()) / max(1, y_train.sum()))
    candidates = []
    for max_depth in [2, 3]:
        for min_child_weight in [3, 8, 14]:
            for scale_multiplier in [0.75, 1.0, 1.5]:
                candidates.append(
                    {
                        "n_estimators": 350,
                        "max_depth": max_depth,
                        "learning_rate": 0.03,
                        "subsample": 0.88,
                        "colsample_bytree": 0.88,
                        "min_child_weight": min_child_weight,
                        "reg_lambda": 7.0,
                        "reg_alpha": 0.4,
                        "gamma": 0.4,
                        "scale_pos_weight_multiplier": scale_multiplier,
                    }
                )

    best_model = None
    best_row = None
    rows = []
    for i, params in enumerate(candidates, start=1):
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
            max_delta_step=1,
            objective="binary:logistic",
            eval_metric="aucpr",
            tree_method="hist",
            random_state=84,
            n_jobs=-1,
            scale_pos_weight=scale_pos_weight * params["scale_pos_weight_multiplier"],
        )
        model.fit(x_train, y_train, eval_set=[(x_valid, y_valid)], verbose=False)
        valid_prob = model.predict_proba(x_valid)[:, 1]
        p25, r25, k25 = candidate_topk(y_valid, valid_prob, 0.25)
        p50, r50, k50 = candidate_topk(y_valid, valid_prob, 0.50)
        row = {
            **params,
            "candidate_id": i,
            "valid_candidate_roc_auc": float(roc_auc_score(y_valid, valid_prob)),
            "valid_candidate_pr_auc": float(average_precision_score(y_valid, valid_prob)),
            "valid_candidate_brier": float(brier_score_loss(y_valid, valid_prob)),
            "valid_candidate_precision_top_0_25": p25,
            "valid_candidate_recall_top_0_25": r25,
            "valid_candidate_k_top_0_25": k25,
            "valid_candidate_precision_top_0_50": p50,
            "valid_candidate_recall_top_0_50": r50,
            "valid_candidate_k_top_0_50": k50,
        }
        row["selection_objective"] = stage2_objective(row)
        rows.append(row)
        if best_row is None or row["selection_objective"] > best_row["selection_objective"]:
            best_model = model
            best_row = row
        print(
            f"stage2 {i:02d}/{len(candidates)} pr_auc={row['valid_candidate_pr_auc']:.4f} "
            f"p@25%={p25:.4f} r@50%={r50:.4f} obj={row['selection_objective']:.4f}"
        )
    assert best_model is not None and best_row is not None
    return best_model, scale_pos_weight, best_row, rows


def add_stage2_scores(scored: pd.DataFrame, stage2_prob: np.ndarray | None = None) -> pd.DataFrame:
    out = scored.copy()
    out["stage2_probability"] = np.nan
    if stage2_prob is not None:
        idx = out.index[out["stage1_candidate"].astype(bool)]
        out.loc[idx, "stage2_probability"] = stage2_prob
    out["stage2_score"] = np.rint(out["stage2_probability"].fillna(0) * 100).clip(0, 100).astype(int)
    return out


def two_stage_top_policy(scored: pd.DataFrame, pct: float, costs: CostAssumptions, capacity_per_day: int):
    flags = pd.Series(False, index=scored.index)
    overflow = 0
    for _, group in scored.groupby(["scenario", "day_index"], sort=False):
        k = max(1, int(np.ceil(len(group) * pct)))
        candidates = group[group["stage1_candidate"]].sort_values(
            ["stage2_probability", "stage1_probability"], ascending=False
        )
        selected = candidates.head(k).head(capacity_per_day).index
        overflow += max(0, min(len(candidates), k) - capacity_per_day)
        flags.loc[selected] = True
    return outcome_metrics_from_review_flags(scored, flags.tolist(), f"two_stage_model_top_{pct:.1%}_daily", f"top_{pct:.1%}", costs, overflow)


def two_stage_threshold_policy(scored: pd.DataFrame, threshold: float, costs: CostAssumptions, capacity_per_day: int):
    flags = pd.Series(False, index=scored.index)
    overflow = 0
    for _, group in scored.groupby(["scenario", "day_index"], sort=False):
        candidates = group[group["stage1_candidate"] & (group["stage2_probability"] >= threshold)].sort_values(
            ["stage2_probability", "stage1_probability"], ascending=False
        )
        selected = candidates.head(capacity_per_day).index
        overflow += max(0, len(candidates) - capacity_per_day)
        flags.loc[selected] = True
    return outcome_metrics_from_review_flags(scored, flags.tolist(), f"two_stage_model_threshold_{threshold:.3f}", threshold, costs, overflow)


def stage1_only_scored(scored: pd.DataFrame) -> pd.DataFrame:
    out = scored.rename(columns={"stage1_probability": "xgb_risk_probability"}).copy()
    return out


def scenario_metrics(scored: pd.DataFrame, probability_col: str, label: str) -> pd.DataFrame:
    rows = []
    for scenario, part in scored.groupby("scenario"):
        y = part["is_fraud"].to_numpy(int)
        p = part[probability_col].fillna(0).to_numpy(float)
        rows.append(
            {
                "model": label,
                "scenario": scenario,
                "rows": int(len(part)),
                "fraud_count": int(y.sum()),
                "fraud_rate": float(y.mean()),
                "roc_auc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else np.nan,
                "pr_auc_average_precision": float(average_precision_score(y, p)) if y.sum() else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["model", "scenario"])


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "data" / "model_runs" / f"xgboost_v5_true_twostage_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    costs = CostAssumptions()

    df = load_dataset(project_root)
    train, valid, test = split_by_time(df, valid_days=4, test_days=8)
    s1_train, s2_train = temporal_train_internal_split(train, holdout_days=8)

    prepared, matrices, preprocessing = prepare_feature_frames(
        [s1_train, s2_train, valid, test],
        fit_reference=s1_train,
    )
    s1_prepared, s2_prepared, valid_prepared, test_prepared = prepared
    x_s1, x_s2, x_valid, x_test = [m.to_numpy(np.float32) for m in matrices]
    y_s1 = s1_prepared["is_fraud"].to_numpy(int)
    y_s2 = s2_prepared["is_fraud"].to_numpy(int)
    y_valid = valid_prepared["is_fraud"].to_numpy(int)
    y_test = test_prepared["is_fraud"].to_numpy(int)

    stage1_model, stage1_spw = train_stage1(x_s1, y_s1)
    s2_prob_1 = stage1_model.predict_proba(x_s2)[:, 1]
    valid_prob_1 = stage1_model.predict_proba(x_valid)[:, 1]
    test_prob_1 = stage1_model.predict_proba(x_test)[:, 1]

    s2_scored = mark_stage1_candidates(add_stage1_scores(s2_prepared, s2_prob_1, costs), STAGE1_CANDIDATE_PCT)
    valid_scored = mark_stage1_candidates(add_stage1_scores(valid_prepared, valid_prob_1, costs), STAGE1_CANDIDATE_PCT)
    test_scored = mark_stage1_candidates(add_stage1_scores(test_prepared, test_prob_1, costs), STAGE1_CANDIDATE_PCT)

    x2_s2_all, stage2_medians = build_stage2_matrix(matrices[1], s2_scored)
    x2_valid_all, _ = build_stage2_matrix(matrices[2], valid_scored, stage2_medians)
    x2_test_all, _ = build_stage2_matrix(matrices[3], test_scored, stage2_medians)

    s2_candidate_mask = s2_scored["stage1_candidate"].to_numpy(bool)
    valid_candidate_mask = valid_scored["stage1_candidate"].to_numpy(bool)
    test_candidate_mask = test_scored["stage1_candidate"].to_numpy(bool)
    x2_train = x2_s2_all.loc[s2_candidate_mask].to_numpy(np.float32)
    y2_train = y_s2[s2_candidate_mask]
    x2_valid = x2_valid_all.loc[valid_candidate_mask].to_numpy(np.float32)
    y2_valid = y_valid[valid_candidate_mask]
    x2_test = x2_test_all.loc[test_candidate_mask].to_numpy(np.float32)
    y2_test = y_test[test_candidate_mask]

    stage2_model, stage2_spw, best_stage2_row, stage2_tuning_rows = train_stage2_candidates(
        x2_train,
        y2_train,
        x2_valid,
        y2_valid,
    )
    valid_prob_2 = stage2_model.predict_proba(x2_valid)[:, 1]
    test_prob_2 = stage2_model.predict_proba(x2_test)[:, 1]
    s2_train_prob_2 = stage2_model.predict_proba(x2_train)[:, 1]

    s2_scored = add_stage2_scores(s2_scored, s2_train_prob_2)
    valid_scored = add_stage2_scores(valid_scored, valid_prob_2)
    test_scored = add_stage2_scores(test_scored, test_prob_2)

    stage1_metrics = []
    stage1_metrics.extend(split_metrics("valid_stage1_all", y_valid, valid_prob_1))
    stage1_metrics.extend(split_metrics("test_stage1_all", y_test, test_prob_1))

    stage2_candidate_metrics = [
        {
            "split": "valid_stage2_candidates",
            "rows": int(len(y2_valid)),
            "fraud_count": int(y2_valid.sum()),
            "fraud_rate": float(y2_valid.mean()),
            "roc_auc": float(roc_auc_score(y2_valid, valid_prob_2)),
            "pr_auc_average_precision": float(average_precision_score(y2_valid, valid_prob_2)),
            "brier_score": float(brier_score_loss(y2_valid, valid_prob_2)),
        },
        {
            "split": "test_stage2_candidates",
            "rows": int(len(y2_test)),
            "fraud_count": int(y2_test.sum()),
            "fraud_rate": float(y2_test.mean()),
            "roc_auc": float(roc_auc_score(y2_test, test_prob_2)),
            "pr_auc_average_precision": float(average_precision_score(y2_test, test_prob_2)),
            "brier_score": float(brier_score_loss(y2_test, test_prob_2)),
        },
    ]
    for name, y, p in [
        ("valid_stage2_candidates", y2_valid, valid_prob_2),
        ("test_stage2_candidates", y2_test, test_prob_2),
    ]:
        for pct in [0.25, 0.50, 0.75]:
            precision, recall, k = candidate_topk(y, p, pct)
            stage2_candidate_metrics.append(
                {
                    "split": f"{name}_top_{pct:.0%}",
                    "rows": k,
                    "fraud_count": int(y.sum()),
                    "fraud_rate": float(y.mean()),
                    "precision_at_k": precision,
                    "recall_at_k": recall,
                }
            )

    capture_df = pd.DataFrame(
        [
            candidate_capture(s2_scored, "s2_train_stage1_top_10_daily"),
            candidate_capture(valid_scored, "valid_stage1_top_10_daily"),
            candidate_capture(test_scored, "test_stage1_top_10_daily"),
        ]
    )

    stage1_policy_input = stage1_only_scored(test_scored)
    policy_rows = []
    for pct in FINAL_REVIEW_PCTS:
        policy_rows.append(top_percentile_policy(stage1_policy_input, pct, costs, 100))
        policy_rows[-1]["policy_family"] = "stage1_only_probability"
        policy_rows.append(two_stage_top_policy(test_scored, pct, costs, 100))
        policy_rows[-1]["policy_family"] = "stage1_plus_stage2_model"

    thresholds = sorted(set([0.30, 0.40, 0.50, 0.60, 0.70] + [float(np.quantile(test_prob_2, q)) for q in [0.50, 0.70, 0.80, 0.90]]))
    for threshold in thresholds:
        row = two_stage_threshold_policy(test_scored, threshold, costs, 100)
        row["policy_family"] = "stage1_plus_stage2_model"
        policy_rows.append(row)
    policy_df = pd.DataFrame(policy_rows).sort_values("net_benefit", ascending=False)

    stage2_importance = pd.DataFrame(
        {
            "feature": list(x2_s2_all.columns),
            "importance_gain": stage2_model.feature_importances_,
        }
    ).sort_values("importance_gain", ascending=False)
    stage1_importance = pd.DataFrame(
        {
            "feature": preprocessing["feature_names"],
            "importance_gain": stage1_model.feature_importances_,
        }
    ).sort_values("importance_gain", ascending=False)
    scenario_df = pd.concat(
        [
            scenario_metrics(stage1_policy_input, "xgb_risk_probability", "stage1_probability"),
            scenario_metrics(test_scored[test_scored["stage1_candidate"]].copy(), "stage2_probability", "stage2_candidate_probability"),
        ],
        ignore_index=True,
    )

    pd.DataFrame(stage1_metrics + stage2_candidate_metrics).to_csv(output_dir / "v5_model_metrics.csv", index=False)
    capture_df.to_csv(output_dir / "v5_candidate_capture.csv", index=False)
    pd.DataFrame(stage2_tuning_rows).sort_values("selection_objective", ascending=False).to_csv(output_dir / "v5_stage2_tuning_results.csv", index=False)
    policy_df.to_csv(output_dir / "v5_policy_comparison.csv", index=False)
    scenario_df.to_csv(output_dir / "v5_scenario_metrics.csv", index=False)
    test_scored.to_csv(output_dir / "v5_test_scores.csv", index=False)
    valid_scored.to_csv(output_dir / "v5_valid_scores.csv", index=False)
    stage1_importance.to_csv(output_dir / "v5_stage1_feature_importance.csv", index=False)
    stage2_importance.to_csv(output_dir / "v5_stage2_feature_importance.csv", index=False)
    joblib.dump(stage1_model, output_dir / "v5_stage1_xgb_model.joblib")
    joblib.dump(stage2_model, output_dir / "v5_stage2_xgb_model.joblib")
    (output_dir / "v5_metadata.json").write_text(
        json.dumps(
            {
                "version": "v5_true_twostage",
                "stage1": "high-recall XGBoost screening model trained on earlier training period",
                "stage2": "XGBoost false-positive reduction model trained only on stage1 candidates from later training period",
                "candidate_policy": f"top {STAGE1_CANDIDATE_PCT:.0%} stage1 probability per scenario/day",
                "stage1_train_rows": int(len(s1_prepared)),
                "stage2_train_rows_all": int(len(s2_prepared)),
                "stage2_train_candidates": int(s2_candidate_mask.sum()),
                "valid_candidates": int(valid_candidate_mask.sum()),
                "test_candidates": int(test_candidate_mask.sum()),
                "stage1_scale_pos_weight": stage1_spw,
                "stage2_scale_pos_weight": stage2_spw,
                "best_stage2_row": best_stage2_row,
                "cost_assumptions": asdict(costs),
                "preprocessing": preprocessing,
                "stage2_features": list(x2_s2_all.columns),
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print(f"Output: {output_dir}")
    print("Candidate capture:")
    print(capture_df.to_string(index=False))
    print("Stage 1 and Stage 2 metrics:")
    print(pd.DataFrame(stage1_metrics + stage2_candidate_metrics).to_string(index=False))
    print("Policy comparison:")
    print(policy_df.head(15).to_string(index=False))
    print("Stage 2 feature importance:")
    print(stage2_importance.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
