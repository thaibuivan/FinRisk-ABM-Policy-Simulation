"""Generate synthetic transaction-risk simulation data.

This script creates a calibrated, synthetic dataset for the thesis project:
Agent-Based Simulation and Mechanism Design for Transaction Risk Decisioning.

It does not copy rows from public datasets. It uses calibration ideas from the
reference profiles and then simulates customers, transactions, risk scores,
policy decisions, analyst review outcomes, and KPI summaries.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SimulationConfig:
    customers: int
    days: int
    seed: int
    fraud_rate: float
    analyst_capacity_per_day: int
    output_dir: str
    scenario_name: str


CATEGORY_WEIGHTS = {
    "transportation": 0.48,
    "food": 0.16,
    "health": 0.08,
    "fashion": 0.07,
    "grocery": 0.07,
    "electronics": 0.05,
    "travel": 0.03,
    "entertainment": 0.03,
    "digital_wallet": 0.03,
}

FRAUD_CATEGORY_WEIGHTS = {
    "electronics": 0.23,
    "travel": 0.18,
    "digital_wallet": 0.17,
    "health": 0.13,
    "fashion": 0.11,
    "entertainment": 0.08,
    "grocery": 0.05,
    "food": 0.03,
    "transportation": 0.02,
}

CATEGORY_RISK = {
    "transportation": 0.05,
    "food": 0.07,
    "grocery": 0.08,
    "health": 0.18,
    "fashion": 0.22,
    "entertainment": 0.25,
    "electronics": 0.42,
    "travel": 0.48,
    "digital_wallet": 0.35,
}

SEGMENTS = ["low_activity", "regular", "high_activity", "premium"]
SEGMENT_WEIGHTS = [0.30, 0.45, 0.20, 0.05]
SEGMENT_RATE_RANGE = {
    "low_activity": (0.12, 0.45),
    "regular": (0.45, 1.15),
    "high_activity": (1.15, 2.40),
    "premium": (0.55, 1.70),
}
SEGMENT_AMOUNT_MEDIAN_RANGE = {
    "low_activity": (10, 30),
    "regular": (18, 65),
    "high_activity": (12, 55),
    "premium": (80, 240),
}


def choose_weighted(rng: np.random.Generator, weights: dict[str, float], size: int) -> np.ndarray:
    keys = np.array(list(weights.keys()))
    probs = np.array(list(weights.values()), dtype=float)
    probs = probs / probs.sum()
    return rng.choice(keys, size=size, p=probs)


def make_customers(config: SimulationConfig, rng: np.random.Generator) -> pd.DataFrame:
    segments = rng.choice(SEGMENTS, size=config.customers, p=SEGMENT_WEIGHTS)
    rows = []
    for idx, segment in enumerate(segments, start=1):
        rate_low, rate_high = SEGMENT_RATE_RANGE[segment]
        amount_low, amount_high = SEGMENT_AMOUNT_MEDIAN_RANGE[segment]
        rows.append(
            {
                "customer_id": f"CUST_{idx:06d}",
                "card_id": f"CARD_{idx:06d}",
                "segment": segment,
                "base_tx_per_day": round(float(rng.uniform(rate_low, rate_high)), 4),
                "typical_amount_median": round(float(rng.uniform(amount_low, amount_high)), 2),
                "night_activity_preference": round(float(rng.beta(1.5, 8.0)), 4),
                "baseline_risk": round(float(rng.beta(1.2, 14.0)), 4),
            }
        )
    return pd.DataFrame(rows)


def normal_hour(rng: np.random.Generator, night_preference: float) -> int:
    if rng.random() < night_preference:
        return int(rng.choice([0, 1, 2, 3, 4, 22, 23]))
    return int(np.clip(round(rng.normal(14, 4)), 6, 22))


def fraud_hour(rng: np.random.Generator) -> int:
    return int(rng.choice([0, 1, 2, 3, 4, 22, 23, 5, 21], p=[0.12, 0.10, 0.08, 0.07, 0.06, 0.22, 0.22, 0.05, 0.08]))


def make_amount(rng: np.random.Generator, median: float, is_fraud: bool, strategy: str | None) -> float:
    if not is_fraud:
        sigma = 0.85
        amount = rng.lognormal(mean=np.log(max(median, 1.0)), sigma=sigma)
        if rng.random() < 0.025:
            amount *= rng.uniform(3.0, 9.0)
        return round(float(min(max(amount, 1.0), 5000.0)), 2)

    if strategy == "low_amount_probe":
        amount = rng.lognormal(mean=np.log(max(median * 0.7, 1.0)), sigma=0.7)
    elif strategy == "burst_velocity":
        amount = rng.lognormal(mean=np.log(max(median * 1.8, 2.0)), sigma=1.0)
    elif strategy == "merchant_abuse":
        amount = rng.lognormal(mean=np.log(max(median * 4.0, 5.0)), sigma=1.15)
    else:
        amount = rng.lognormal(mean=np.log(max(median * 8.0, 10.0)), sigma=1.25)
    return round(float(min(max(amount, 1.0), 10000.0)), 2)


def make_transactions(config: SimulationConfig, customers: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fraud_strategies = ["high_amount", "low_amount_probe", "burst_velocity", "late_hour", "merchant_abuse", "mixed"]
    strategy_probs = [0.25, 0.18, 0.22, 0.13, 0.14, 0.08]
    rows = []
    tx_no = 1

    for day in range(config.days):
        day_start = start + timedelta(days=day)
        for customer in customers.itertuples(index=False):
            tx_count = int(rng.poisson(customer.base_tx_per_day))
            if rng.random() < 0.025:
                tx_count += int(rng.integers(2, 7))
            for _ in range(tx_count):
                is_fraud = bool(rng.random() < config.fraud_rate)
                strategy = None
                if is_fraud:
                    strategy = str(rng.choice(fraud_strategies, p=strategy_probs))
                    hour = fraud_hour(rng) if strategy in {"late_hour", "mixed", "burst_velocity"} else normal_hour(rng, customer.night_activity_preference)
                    category = str(choose_weighted(rng, FRAUD_CATEGORY_WEIGHTS, 1)[0])
                else:
                    hour = normal_hour(rng, customer.night_activity_preference)
                    category = str(choose_weighted(rng, CATEGORY_WEIGHTS, 1)[0])

                minute = int(rng.integers(0, 60))
                second = int(rng.integers(0, 60))
                happened_at = day_start + timedelta(hours=hour, minutes=minute, seconds=second)
                amount = make_amount(rng, customer.typical_amount_median, is_fraud, strategy)

                rows.append(
                    {
                        "transaction_id": f"TXN_{tx_no:09d}",
                        "customer_id": customer.customer_id,
                        "card_id": customer.card_id,
                        "timestamp": happened_at.isoformat(),
                        "day_index": day,
                        "hour": hour,
                        "amount": amount,
                        "merchant_category": category,
                        "channel": str(rng.choice(["card_present", "ecommerce", "wallet", "transfer"], p=[0.45, 0.30, 0.18, 0.07])),
                        "is_fraud": int(is_fraud),
                        "fraud_strategy": strategy or "none",
                    }
                )
                tx_no += 1

    tx = pd.DataFrame(rows)
    if tx.empty:
        return tx
    tx["timestamp"] = pd.to_datetime(tx["timestamp"], utc=True)
    tx = tx.sort_values(["customer_id", "timestamp", "transaction_id"]).reset_index(drop=True)
    return tx


def percentile_or_nan(values: Iterable[float], q: float) -> float:
    arr = np.array(list(values), dtype=float)
    if arr.size == 0:
        return float("nan")
    return float(np.percentile(arr, q))


def add_behavior_features(transactions: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    customer_lookup = customers.set_index("customer_id")
    feature_rows = []

    for customer_id, group in transactions.groupby("customer_id", sort=False):
        group = group.sort_values("timestamp")
        prior_times: list[pd.Timestamp] = []
        prior_amounts: list[float] = []
        prior_hours: list[int] = []

        baseline = float(customer_lookup.loc[customer_id, "baseline_risk"])
        typical_amount = float(customer_lookup.loc[customer_id, "typical_amount_median"])

        for row in group.itertuples(index=False):
            now = row.timestamp
            amount = float(row.amount)
            windows = {
                "1h": now - pd.Timedelta(hours=1),
                "24h": now - pd.Timedelta(hours=24),
                "3d": now - pd.Timedelta(days=3),
                "7d": now - pd.Timedelta(days=7),
                "30d": now - pd.Timedelta(days=30),
            }
            prior_df = pd.DataFrame({"timestamp": prior_times, "amount": prior_amounts, "hour": prior_hours})

            metrics: dict[str, float] = {}
            for label, start in windows.items():
                if prior_df.empty:
                    window = prior_df
                else:
                    window = prior_df[prior_df["timestamp"] >= start]
                metrics[f"txn_count_{label}"] = float(len(window))
                metrics[f"total_amount_{label}"] = float(window["amount"].sum()) if len(window) else 0.0
                metrics[f"avg_amount_{label}"] = float(window["amount"].mean()) if len(window) else np.nan
                metrics[f"median_amount_{label}"] = float(window["amount"].median()) if len(window) else np.nan
                metrics[f"p95_amount_{label}"] = percentile_or_nan(window["amount"], 95) if len(window) else np.nan

            recent_amounts_7d = prior_df[prior_df["timestamp"] >= windows["7d"]]["amount"] if not prior_df.empty else pd.Series(dtype=float)
            recent_hours_7d = prior_df[prior_df["timestamp"] >= windows["7d"]]["hour"] if not prior_df.empty else pd.Series(dtype=float)
            gap_minutes = np.nan
            if prior_times:
                gap_minutes = (now - prior_times[-1]).total_seconds() / 60.0

            comparison_base = float(recent_amounts_7d.median()) if len(recent_amounts_7d) >= 3 else typical_amount
            amount_anomaly = min(max((amount / max(comparison_base, 1.0) - 1.0) / 8.0, 0.0), 1.0)
            velocity_signal = min((metrics["txn_count_1h"] / 3.0) * 0.6 + (metrics["txn_count_24h"] / 10.0) * 0.4, 1.0)
            unusual_hour = 1.0 if int(row.hour) in {0, 1, 2, 3, 4, 22, 23} else 0.0
            if len(recent_hours_7d) >= 5:
                usual_hours = set(recent_hours_7d.value_counts().head(5).index.astype(int).tolist())
                if int(row.hour) not in usual_hours:
                    unusual_hour = max(unusual_hour, 0.6)

            feature_rows.append(
                {
                    "transaction_id": row.transaction_id,
                    "customer_id": customer_id,
                    "amount_anomaly_signal": round(float(amount_anomaly), 4),
                    "velocity_signal": round(float(velocity_signal), 4),
                    "unusual_hour_signal": round(float(unusual_hour), 4),
                    "merchant_risk_signal": round(float(CATEGORY_RISK.get(row.merchant_category, 0.10)), 4),
                    "baseline_risk": round(baseline, 4),
                    "gap_minutes_since_prev": round(float(gap_minutes), 2) if not np.isnan(gap_minutes) else np.nan,
                    **{k: round(float(v), 4) if not pd.isna(v) else np.nan for k, v in metrics.items()},
                }
            )
            prior_times.append(now)
            prior_amounts.append(amount)
            prior_hours.append(int(row.hour))

    return pd.DataFrame(feature_rows)


def score_transactions(features: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for row in features.itertuples(index=False):
        logit = (
            -3.2
            + 4.0 * row.amount_anomaly_signal
            + 2.2 * row.velocity_signal
            + 1.1 * row.unusual_hour_signal
            + 2.0 * row.merchant_risk_signal
            + 2.5 * row.baseline_risk
            + rng.normal(0, 0.35)
        )
        probability = 1.0 / (1.0 + np.exp(-logit))
        score = int(round(min(max(probability * 100.0, 0.0), 100.0)))
        rows.append(
            {
                "transaction_id": row.transaction_id,
                "risk_probability": round(float(probability), 5),
                "risk_score": score,
                "risk_level": risk_level(score),
                "top_driver_1": top_driver(row),
            }
        )
    return pd.DataFrame(rows)


def top_driver(row: object) -> str:
    values = {
        "amount_anomaly": float(row.amount_anomaly_signal),
        "velocity": float(row.velocity_signal),
        "transaction_timing": float(row.unusual_hour_signal),
        "merchant_category": float(row.merchant_risk_signal),
        "baseline_risk": float(row.baseline_risk),
    }
    return max(values.items(), key=lambda item: item[1])[0]


def risk_level(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def make_policy_decisions(transactions: pd.DataFrame, scores: pd.DataFrame, config: SimulationConfig) -> pd.DataFrame:
    df = transactions[["transaction_id", "day_index", "is_fraud"]].merge(scores, on="transaction_id", how="left")
    df = df.sort_values(["day_index", "risk_score"], ascending=[True, False]).copy()
    decisions = []

    for day, group in df.groupby("day_index", sort=True):
        review_used = 0
        for row in group.itertuples(index=False):
            if row.risk_score >= 90:
                action = "simulated_step_up_or_hold"
                reviewed = 1 if review_used < config.analyst_capacity_per_day else 0
            elif row.risk_score >= 70:
                action = "review_queue"
                reviewed = 1 if review_used < config.analyst_capacity_per_day else 0
            elif row.risk_score >= 50:
                action = "monitor"
                reviewed = 0
            else:
                action = "allow"
                reviewed = 0

            if reviewed:
                review_used += 1

            decisions.append(
                {
                    "transaction_id": row.transaction_id,
                    "day_index": int(day),
                    "policy_action": action,
                    "sent_to_analyst": int(action in {"review_queue", "simulated_step_up_or_hold"}),
                    "analyst_reviewed": int(reviewed),
                    "review_queue_overflow": int(action in {"review_queue", "simulated_step_up_or_hold"} and not reviewed),
                }
            )
    return pd.DataFrame(decisions)


def make_analyst_reviews(transactions: pd.DataFrame, scores: pd.DataFrame, decisions: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    df = transactions[["transaction_id", "is_fraud"]].merge(scores, on="transaction_id").merge(decisions, on="transaction_id")
    rows = []
    for row in df[df["analyst_reviewed"] == 1].itertuples(index=False):
        if int(row.is_fraud) == 1:
            outcome = "confirmed_risk" if rng.random() < 0.88 else "missed_after_review"
        else:
            outcome = "false_positive" if rng.random() < 0.80 else "cleared_with_notes"
        review_minutes = max(2.0, float(rng.normal(9.0 if row.risk_score >= 85 else 6.0, 2.0)))
        rows.append(
            {
                "transaction_id": row.transaction_id,
                "analyst_outcome": outcome,
                "review_minutes": round(review_minutes, 2),
            }
        )
    return pd.DataFrame(rows)


def make_outcomes(transactions: pd.DataFrame, scores: pd.DataFrame, decisions: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
    df = transactions[["transaction_id", "amount", "is_fraud"]].merge(scores, on="transaction_id").merge(decisions, on="transaction_id")
    if reviews.empty:
        df["analyst_outcome"] = "not_reviewed"
        df["review_minutes"] = 0.0
    else:
        df = df.merge(reviews, on="transaction_id", how="left")
        df["analyst_outcome"] = df["analyst_outcome"].fillna("not_reviewed")
        df["review_minutes"] = df["review_minutes"].fillna(0.0)

    prevented_mask = (df["is_fraud"] == 1) & df["policy_action"].isin(["review_queue", "simulated_step_up_or_hold"]) & (df["analyst_reviewed"] == 1)
    missed_mask = (df["is_fraud"] == 1) & ~prevented_mask
    false_positive_mask = (df["is_fraud"] == 0) & df["sent_to_analyst"].eq(1)

    df["fraud_loss_prevented"] = np.where(prevented_mask, df["amount"] * 0.75, 0.0).round(2)
    df["fraud_loss_realized"] = np.where(missed_mask, df["amount"], 0.0).round(2)
    df["false_positive_cost"] = np.where(false_positive_mask, 3.0 + df["amount"] * 0.01, 0.0).round(2)
    df["analyst_cost"] = (df["review_minutes"] * 0.45).round(2)
    df["net_benefit"] = (df["fraud_loss_prevented"] - df["fraud_loss_realized"] - df["false_positive_cost"] - df["analyst_cost"]).round(2)
    return df[
        [
            "transaction_id",
            "is_fraud",
            "risk_score",
            "policy_action",
            "analyst_reviewed",
            "fraud_loss_prevented",
            "fraud_loss_realized",
            "false_positive_cost",
            "analyst_cost",
            "net_benefit",
        ]
    ]


def make_metrics(transactions: pd.DataFrame, scores: pd.DataFrame, decisions: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    df = transactions[["transaction_id", "is_fraud"]].merge(scores, on="transaction_id").merge(decisions, on="transaction_id").merge(outcomes, on=["transaction_id", "is_fraud", "risk_score", "policy_action", "analyst_reviewed"])
    flagged = df["sent_to_analyst"].eq(1)
    fraud = df["is_fraud"].eq(1)
    tp = int((flagged & fraud).sum())
    fp = int((flagged & ~fraud).sum())
    fn = int((~flagged & fraud).sum())
    tn = int((~flagged & ~fraud).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    return pd.DataFrame(
        [
            {
                "transactions": int(len(df)),
                "fraud_count": int(fraud.sum()),
                "fraud_rate": round(float(fraud.mean()) if len(df) else 0.0, 6),
                "alerts_sent_to_analyst": int(flagged.sum()),
                "analyst_reviewed": int(df["analyst_reviewed"].sum()),
                "review_overflow": int(df["review_queue_overflow"].sum()),
                "precision_flagged": round(precision, 4),
                "recall_flagged": round(recall, 4),
                "false_positive_rate": round(fpr, 4),
                "fraud_loss_prevented": round(float(df["fraud_loss_prevented"].sum()), 2),
                "fraud_loss_realized": round(float(df["fraud_loss_realized"].sum()), 2),
                "false_positive_cost": round(float(df["false_positive_cost"].sum()), 2),
                "analyst_cost": round(float(df["analyst_cost"].sum()), 2),
                "net_benefit": round(float(df["net_benefit"].sum()), 2),
            }
        ]
    )


def write_outputs(output_root: Path, config: SimulationConfig, frames: dict[str, pd.DataFrame]) -> Path:
    run_id = f"{config.scenario_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    for name, frame in frames.items():
        frame.to_csv(run_dir / f"{name}.csv", index=False)

    with (run_dir / "config.json").open("w", encoding="utf-8") as f:
        json.dump(asdict(config), f, indent=2, ensure_ascii=False)

    examples = frames["transactions"].merge(frames["risk_scores"], on="transaction_id").merge(frames["policy_decisions"], on="transaction_id")
    examples = examples.sort_values("risk_score", ascending=False).head(20)
    with (run_dir / "case_examples.json").open("w", encoding="utf-8") as f:
        json.dump(examples.to_dict(orient="records"), f, indent=2, ensure_ascii=False, default=str)

    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic transaction-risk simulation data.")
    parser.add_argument("--customers", type=int, default=1000)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed", type=int, default=149)
    parser.add_argument("--fraud-rate", type=float, default=0.01)
    parser.add_argument("--analyst-capacity-per-day", type=int, default=100)
    parser.add_argument("--scenario-name", type=str, default="baseline")
    parser.add_argument("--output-dir", type=str, default="data/simulation_runs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SimulationConfig(
        customers=args.customers,
        days=args.days,
        seed=args.seed,
        fraud_rate=args.fraud_rate,
        analyst_capacity_per_day=args.analyst_capacity_per_day,
        output_dir=args.output_dir,
        scenario_name=args.scenario_name,
    )
    rng = np.random.default_rng(config.seed)

    customers = make_customers(config, rng)
    transactions = make_transactions(config, customers, rng)
    behavior_features = add_behavior_features(transactions, customers)
    risk_scores = score_transactions(behavior_features, rng)
    policy_decisions = make_policy_decisions(transactions, risk_scores, config)
    analyst_reviews = make_analyst_reviews(transactions, risk_scores, policy_decisions, rng)
    outcomes = make_outcomes(transactions, risk_scores, policy_decisions, analyst_reviews)
    simulation_metrics = make_metrics(transactions, risk_scores, policy_decisions, outcomes)

    frames = {
        "customers": customers,
        "transactions": transactions,
        "behavior_features": behavior_features,
        "risk_scores": risk_scores,
        "policy_decisions": policy_decisions,
        "analyst_reviews": analyst_reviews,
        "outcomes": outcomes,
        "simulation_metrics": simulation_metrics,
    }

    run_dir = write_outputs(Path(config.output_dir), config, frames)
    safe_run_dir = str(run_dir).encode("ascii", errors="backslashreplace").decode("ascii")
    print(f"Simulation run written to: {safe_run_dir}")
    print(simulation_metrics.to_string(index=False))


if __name__ == "__main__":
    main()

