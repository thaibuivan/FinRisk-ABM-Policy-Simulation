"""Build lightweight analysis reports from simulation comparison outputs.

Outputs:
- Markdown summary for the thesis report.
- HTML report with simple CSS bar charts.

No plotting dependency is required; charts are rendered with HTML/CSS bars.
"""

from __future__ import annotations

import argparse
import html
from datetime import datetime
from pathlib import Path

import pandas as pd


METRIC_LABELS = {
    "net_benefit": "Net benefit",
    "recall_flagged": "Recall flagged",
    "recall_reviewed": "Recall reviewed",
    "precision_flagged": "Precision flagged",
    "alerts_sent_to_analyst": "Alerts sent to analyst",
    "analyst_reviewed": "Analyst reviewed",
    "review_overflow": "Review overflow",
    "false_positive_cost": "False positive cost",
    "analyst_cost": "Analyst cost",
    "fraud_loss_prevented": "Fraud loss prevented",
    "fraud_loss_realized": "Fraud loss realized",
}


def latest_csv(folder: Path, prefix: str) -> Path:
    matches = sorted(folder.glob(f"{prefix}*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No CSV matching {prefix}*.csv in {folder}")
    return matches[0]


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def money(value: float) -> str:
    return f"{value:,.2f}"


def md_table(df: pd.DataFrame, columns: list[str]) -> str:
    rows = []
    headers = [METRIC_LABELS.get(col, col) for col in columns]
    rows.append("| " + " | ".join(headers) + " |")
    rows.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for _, row in df.iterrows():
        vals = []
        for col in columns:
            value = row[col]
            if col in {"fraud_rate", "precision_flagged", "recall_flagged", "precision_reviewed", "recall_reviewed", "false_positive_rate"}:
                vals.append(pct(float(value)))
            elif col in {"net_benefit", "fraud_loss_prevented", "fraud_loss_realized", "false_positive_cost", "analyst_cost"}:
                vals.append(money(float(value)))
            else:
                vals.append(str(value))
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join(rows)


def bar_chart_html(df: pd.DataFrame, label_col: str, metric_col: str, title: str, value_kind: str = "number") -> str:
    values = df[metric_col].astype(float)
    max_abs = max(abs(values).max(), 1.0)
    blocks = [f"<section class='chart'><h2>{html.escape(title)}</h2>"]
    for _, row in df.iterrows():
        value = float(row[metric_col])
        width = abs(value) / max_abs * 100
        cls = "bar positive" if value >= 0 else "bar negative"
        if value_kind == "percent":
            shown = pct(value)
        elif value_kind == "money":
            shown = money(value)
        else:
            shown = f"{value:,.0f}"
        blocks.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{html.escape(str(row[label_col]))}</div>"
            "<div class='bar-track'>"
            f"<div class='{cls}' style='width:{width:.2f}%'></div>"
            "</div>"
            f"<div class='bar-value'>{html.escape(shown)}</div>"
            "</div>"
        )
    blocks.append("</section>")
    return "\n".join(blocks)


def build_markdown(scenario: pd.DataFrame, policy100: pd.DataFrame, policy20: pd.DataFrame) -> str:
    scenario_cols = ["scenario", "fraud_rate", "precision_flagged", "recall_flagged", "review_overflow", "net_benefit"]
    policy_cols = ["policy_name", "alerts_sent_to_analyst", "analyst_reviewed", "review_overflow", "precision_flagged", "recall_reviewed", "net_benefit"]

    p100_base = policy100[policy100["cost_scenario"] == "base_cost"].copy()
    p20_base = policy20[policy20["cost_scenario"] == "base_cost"].copy()

    return "\n".join(
        [
            "# Simulation Analysis Report",
            "",
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 1. Scenario comparison",
            "",
            md_table(scenario, scenario_cols),
            "",
            "Main reading: low fraud pressure can make review utility negative, while stress fraud increases net benefit. Analyst capacity constraints reduce net benefit through review overflow.",
            "",
            "## 2. Policy comparison - capacity 100/day",
            "",
            md_table(p100_base, policy_cols),
            "",
            "Main reading: when analyst capacity is sufficient, a more sensitive threshold can increase recall and slightly improve net benefit under the current cost assumptions.",
            "",
            "## 3. Policy comparison - capacity 20/day",
            "",
            md_table(p20_base, policy_cols),
            "",
            "Main reading: when capacity is constrained, the sensitive policy creates too much overflow. Balanced threshold becomes more robust.",
            "",
            "## 4. Caveat",
            "",
            "All values are simulation utilities under explicit assumptions. They should be used for relative comparison, not as real bank profit or production performance claims.",
        ]
    )


def build_html(scenario: pd.DataFrame, policy100: pd.DataFrame, policy20: pd.DataFrame) -> str:
    p100_base = policy100[policy100["cost_scenario"] == "base_cost"].copy()
    p20_base = policy20[policy20["cost_scenario"] == "base_cost"].copy()

    style = """
    body { font-family: Arial, sans-serif; margin: 32px; color: #172033; background: #f7f9fc; }
    h1 { margin-bottom: 4px; }
    .subtitle { color: #667085; margin-bottom: 28px; }
    section { background: white; border: 1px solid #d9e1ec; border-radius: 8px; padding: 18px; margin: 18px 0; }
    h2 { margin: 0 0 14px; font-size: 18px; }
    .bar-row { display: grid; grid-template-columns: 190px 1fr 120px; gap: 12px; align-items: center; margin: 10px 0; }
    .bar-label { font-size: 14px; color: #344054; }
    .bar-track { height: 20px; background: #edf2f7; border-radius: 4px; overflow: hidden; }
    .bar { height: 100%; border-radius: 4px; }
    .positive { background: #2563eb; }
    .negative { background: #dc2626; }
    .bar-value { text-align: right; font-family: Consolas, monospace; font-size: 13px; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }
    th, td { border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: right; }
    th:first-child, td:first-child { text-align: left; }
    th { color: #475467; background: #f9fafb; }
    .note { color: #475467; line-height: 1.5; }
    """

    sections = [
        "<!doctype html><html><head><meta charset='utf-8'><title>Simulation Analysis Report</title>",
        f"<style>{style}</style></head><body>",
        "<h1>Simulation Analysis Report</h1>",
        f"<div class='subtitle'>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>",
        bar_chart_html(scenario, "scenario", "net_benefit", "Scenario net benefit", "money"),
        bar_chart_html(scenario, "scenario", "review_overflow", "Scenario review overflow", "number"),
        bar_chart_html(p100_base, "policy_name", "net_benefit", "Policy net benefit - capacity 100/day", "money"),
        bar_chart_html(p20_base, "policy_name", "net_benefit", "Policy net benefit - capacity 20/day", "money"),
        bar_chart_html(p100_base, "policy_name", "recall_reviewed", "Policy recall reviewed - capacity 100/day", "percent"),
        bar_chart_html(p20_base, "policy_name", "review_overflow", "Policy review overflow - capacity 20/day", "number"),
        "<section><h2>Interpretation</h2><p class='note'>The same risk score can produce different business outcomes depending on the decision policy and analyst capacity. Under sufficient capacity, sensitive threshold improves recall and utility. Under constrained capacity, balanced threshold is more robust because it creates less overflow.</p></section>",
        "</body></html>",
    ]
    return "\n".join(sections)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build analysis reports from simulation outputs.")
    parser.add_argument("--project-root", type=str, default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output-dir", type=str, default="reports/analysis")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.project_root).resolve()
    scenario_path = latest_csv(root / "data" / "scenario_comparisons", "scenario_comparison_")
    policy_paths = sorted((root / "data" / "policy_comparisons").glob("policy_comparison_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    if len(policy_paths) < 2:
        raise FileNotFoundError("Need at least two policy comparison CSV files for capacity 100 and 20.")

    policy20_path = policy_paths[0]
    policy100_path = policy_paths[1]

    scenario = pd.read_csv(scenario_path)
    policy20 = pd.read_csv(policy20_path)
    policy100 = pd.read_csv(policy100_path)

    out_dir = (root / args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = out_dir / f"simulation_analysis_report_{ts}.md"
    html_path = out_dir / f"simulation_analysis_report_{ts}.html"

    md_path.write_text(build_markdown(scenario, policy100, policy20), encoding="utf-8")
    html_path.write_text(build_html(scenario, policy100, policy20), encoding="utf-8")

    print("Analysis report written to:")
    print(str(md_path).encode("ascii", errors="backslashreplace").decode("ascii"))
    print(str(html_path).encode("ascii", errors="backslashreplace").decode("ascii"))


if __name__ == "__main__":
    main()
