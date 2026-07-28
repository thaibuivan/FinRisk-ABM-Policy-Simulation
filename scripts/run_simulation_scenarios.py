"""Run multiple transaction-risk simulation scenarios and compare KPIs.

This script is intentionally thin: it reuses generate_simulation_data.py for each
scenario, then collects simulation_metrics.csv into one comparison table.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Scenario:
    name: str
    customers: int
    days: int
    seed: int
    fraud_rate: float
    analyst_capacity_per_day: int
    description: str


DEFAULT_SCENARIOS = [
    Scenario(
        name="low_fraud",
        customers=1000,
        days=30,
        seed=20260721,
        fraud_rate=0.0015,
        analyst_capacity_per_day=100,
        description="Low fraud environment calibrated near very rare fraud datasets.",
    ),
    Scenario(
        name="baseline",
        customers=1000,
        days=30,
        seed=20260722,
        fraud_rate=0.01,
        analyst_capacity_per_day=100,
        description="Reference environment for policy comparison.",
    ),
    Scenario(
        name="stress_fraud",
        customers=1000,
        days=30,
        seed=20260723,
        fraud_rate=0.03,
        analyst_capacity_per_day=100,
        description="Stress scenario with elevated fraud pressure.",
    ),
    Scenario(
        name="low_capacity",
        customers=1000,
        days=30,
        seed=20260722,
        fraud_rate=0.01,
        analyst_capacity_per_day=20,
        description="Same generated environment as baseline but analyst capacity is strongly constrained.",
    ),
    Scenario(
        name="high_capacity",
        customers=1000,
        days=30,
        seed=20260722,
        fraud_rate=0.01,
        analyst_capacity_per_day=200,
        description="Same generated environment as baseline with higher analyst capacity.",
    ),
]


def safe_text(value: object) -> str:
    return str(value).encode("ascii", errors="backslashreplace").decode("ascii")


def run_one_scenario(project_root: Path, scenario: Scenario, output_dir: Path) -> Path:
    generator = project_root / "scripts" / "generate_simulation_data.py"
    cmd = [
        sys.executable,
        str(generator),
        "--customers",
        str(scenario.customers),
        "--days",
        str(scenario.days),
        "--seed",
        str(scenario.seed),
        "--fraud-rate",
        str(scenario.fraud_rate),
        "--analyst-capacity-per-day",
        str(scenario.analyst_capacity_per_day),
        "--scenario-name",
        scenario.name,
        "--output-dir",
        str(output_dir),
    ]

    before = set(output_dir.glob(f"{scenario.name}_*")) if output_dir.exists() else set()
    print(f"Running scenario: {scenario.name}")
    subprocess.run(cmd, cwd=project_root, check=True)
    after = set(output_dir.glob(f"{scenario.name}_*"))
    created = sorted(after - before, key=lambda path: path.stat().st_mtime, reverse=True)
    if created:
        return created[0]
    matches = sorted(after, key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise RuntimeError(f"Could not find output directory for scenario {scenario.name}")
    return matches[0]


def collect_metrics(run_dirs: list[tuple[Scenario, Path]]) -> pd.DataFrame:
    rows = []
    for scenario, run_dir in run_dirs:
        metric_path = run_dir / "simulation_metrics.csv"
        if not metric_path.exists():
            raise FileNotFoundError(metric_path)
        metrics = pd.read_csv(metric_path).iloc[0].to_dict()
        metrics.update(
            {
                "scenario": scenario.name,
                "description": scenario.description,
                "customers": scenario.customers,
                "days": scenario.days,
                "configured_fraud_rate": scenario.fraud_rate,
                "analyst_capacity_per_day": scenario.analyst_capacity_per_day,
                "run_dir": str(run_dir),
            }
        )
        rows.append(metrics)

    df = pd.DataFrame(rows)
    ordered = [
        "scenario",
        "description",
        "customers",
        "days",
        "configured_fraud_rate",
        "analyst_capacity_per_day",
        "transactions",
        "fraud_count",
        "fraud_rate",
        "alerts_sent_to_analyst",
        "analyst_reviewed",
        "review_overflow",
        "precision_flagged",
        "recall_flagged",
        "false_positive_rate",
        "fraud_loss_prevented",
        "fraud_loss_realized",
        "false_positive_cost",
        "analyst_cost",
        "net_benefit",
        "run_dir",
    ]
    return df[ordered]


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


def latest_run_dir(output_dir: Path, scenario_name: str) -> Path:
    matches = sorted(output_dir.glob(f"{scenario_name}_*"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No run directory found for scenario {scenario_name} in {output_dir}")
    return matches[0]
def write_markdown_summary(comparison: pd.DataFrame, output_path: Path) -> None:
    cols = [
        "scenario",
        "fraud_rate",
        "alerts_sent_to_analyst",
        "precision_flagged",
        "recall_flagged",
        "review_overflow",
        "fraud_loss_prevented",
        "fraud_loss_realized",
        "false_positive_cost",
        "analyst_cost",
        "net_benefit",
    ]
    table = comparison[cols].copy()
    markdown = [
        "# Scenario Comparison Summary",
        "",
        "This table compares simulated policy outcomes across fraud pressure and analyst capacity scenarios.",
        "",
        dataframe_to_markdown(table),
        "",
        "## How to read this table",
        "",
        "- `precision_flagged`: among transactions sent to analyst, how many are truly simulated fraud.",
        "- `recall_flagged`: among all simulated fraud transactions, how many are sent to analyst.",
        "- `review_overflow`: transactions that should be reviewed but exceed daily analyst capacity.",
        "- `net_benefit`: fraud loss prevented minus realized fraud loss, false positive cost, and analyst cost.",
        "",
        "The goal is not only to maximize model recall, but to find a decision mechanism that balances risk reduction, analyst workload, and customer friction.",
    ]
    output_path.write_text("\n".join(markdown), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run simulation scenarios and compare their KPIs.")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output-dir", default="data/simulation_runs")
    parser.add_argument("--comparison-dir", default="data/scenario_comparisons")
    parser.add_argument("--collect-existing", action="store_true", help="Collect latest existing scenario runs without running simulations again.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    output_dir = (project_root / args.output_dir).resolve()
    comparison_dir = (project_root / args.comparison_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_dir.mkdir(parents=True, exist_ok=True)

    run_dirs = []
    for scenario in DEFAULT_SCENARIOS:
        if args.collect_existing:
            run_dir = latest_run_dir(output_dir, scenario.name)
        else:
            run_dir = run_one_scenario(project_root, scenario, output_dir)
        run_dirs.append((scenario, run_dir))

    comparison = collect_metrics(run_dirs)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = comparison_dir / f"scenario_comparison_{timestamp}.csv"
    md_path = comparison_dir / f"scenario_comparison_{timestamp}.md"
    comparison.to_csv(csv_path, index=False)
    write_markdown_summary(comparison, md_path)

    print("Scenario comparison written to:")
    print(safe_text(csv_path))
    print(safe_text(md_path))
    print(comparison[["scenario", "fraud_rate", "precision_flagged", "recall_flagged", "review_overflow", "net_benefit"]].to_string(index=False))


if __name__ == "__main__":
    main()





