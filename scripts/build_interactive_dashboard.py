"""Build a static interactive dashboard prototype for the thesis project.

The dashboard is a single self-contained HTML file. It embeds the latest
scenario and policy comparison outputs, then uses vanilla JavaScript to support
simple interactions without a backend.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


def latest_csv(folder: Path, prefix: str) -> Path:
    matches = sorted(folder.glob(f"{prefix}*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No CSV matching {prefix}*.csv in {folder}")
    return matches[0]


def load_policy_files(folder: Path) -> tuple[Path, Path]:
    paths = sorted(folder.glob("policy_comparison_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    sufficient = None
    constrained = None
    for path in paths:
        df = pd.read_csv(path)
        base = df[(df["cost_scenario"] == "base_cost") & (df["policy_name"] == "balanced_threshold")]
        overflow = float(base["review_overflow"].max()) if not base.empty else 0.0
        if overflow > 0 and constrained is None:
            constrained = path
        if overflow == 0 and sufficient is None:
            sufficient = path
        if constrained and sufficient:
            break
    if not sufficient or not constrained:
        raise FileNotFoundError("Could not infer both sufficient-capacity and constrained-capacity policy files.")
    return sufficient, constrained


def records(df: pd.DataFrame) -> list[dict[str, object]]:
    return json.loads(df.to_json(orient="records", force_ascii=False))


def build_html(scenario: pd.DataFrame, policy_sufficient: pd.DataFrame, policy_constrained: pd.DataFrame, sources: dict[str, str]) -> str:
    payload = {
        "scenario": records(scenario),
        "policies": {
            "capacity_100": records(policy_sufficient),
            "capacity_20": records(policy_constrained),
        },
        "sources": sources,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Risk Decision Simulation Dashboard</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --panel: #ffffff;
      --ink: #111827;
      --muted: #64748b;
      --line: #d9e2ef;
      --blue: #2563eb;
      --green: #059669;
      --red: #dc2626;
      --amber: #d97706;
      --slate: #334155;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, sans-serif; color: var(--ink); background: var(--bg); }}
    header {{ padding: 28px 36px 18px; background: var(--panel); border-bottom: 1px solid var(--line); }}
    h1 {{ margin: 0; font-size: 28px; letter-spacing: 0; }}
    .subtitle {{ color: var(--muted); margin-top: 8px; line-height: 1.5; max-width: 980px; }}
    main {{ padding: 24px 36px 40px; max-width: 1420px; margin: 0 auto; }}
    .controls {{ display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 14px; margin-bottom: 18px; }}
    label {{ display: block; font-size: 12px; color: var(--muted); text-transform: uppercase; margin-bottom: 6px; font-weight: 700; }}
    select {{ width: 100%; padding: 10px 12px; border: 1px solid var(--line); background: white; border-radius: 6px; font-size: 15px; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 14px; margin-bottom: 18px; }}
    .card, .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }}
    .card {{ padding: 16px; min-height: 104px; }}
    .card-title {{ color: var(--muted); font-size: 12px; text-transform: uppercase; font-weight: 700; }}
    .card-value {{ font-size: 24px; font-weight: 700; margin-top: 10px; }}
    .card-note {{ color: var(--muted); font-size: 13px; margin-top: 8px; }}
    .grid {{ display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 18px; align-items: start; }}
    .panel {{ padding: 18px; margin-bottom: 18px; }}
    .panel h2 {{ margin: 0 0 14px; font-size: 18px; }}
    .bar-row {{ display: grid; grid-template-columns: 190px 1fr 112px; gap: 12px; align-items: center; margin: 11px 0; }}
    .bar-label {{ font-size: 14px; color: var(--slate); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .track {{ height: 20px; background: #eef2f7; border-radius: 4px; overflow: hidden; }}
    .bar {{ height: 100%; border-radius: 4px; min-width: 2px; }}
    .bar.positive {{ background: var(--blue); }}
    .bar.negative {{ background: var(--red); }}
    .bar.secondary {{ background: var(--green); }}
    .bar-value {{ text-align: right; font-family: Consolas, monospace; font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 9px 8px; border-bottom: 1px solid #e5e7eb; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ color: var(--muted); background: #f8fafc; font-size: 12px; text-transform: uppercase; }}
    tr.best {{ background: #ecfdf5; }}
    .insight {{ line-height: 1.55; color: #263449; }}
    .tag {{ display: inline-block; border: 1px solid var(--line); border-radius: 999px; padding: 4px 8px; margin: 4px 4px 0 0; font-size: 12px; background: #f8fafc; color: var(--slate); }}
    .scatter {{ width: 100%; min-height: 280px; border: 1px solid #e5e7eb; border-radius: 6px; background: #fbfdff; }}
    .footnote {{ color: var(--muted); font-size: 13px; line-height: 1.5; }}
    @media (max-width: 900px) {{
      main, header {{ padding-left: 18px; padding-right: 18px; }}
      .controls, .cards, .grid {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 1fr; gap: 5px; }}
      .bar-value {{ text-align: left; }}
    }}
  </style>
</head>
<body>
<header>
  <h1>Risk Decision Simulation Dashboard</h1>
  <div class="subtitle">Prototype tương tác tĩnh cho đề án: so sánh scenario, policy và cost assumptions trong bài toán ra quyết định rủi ro giao dịch. Dữ liệu được sinh từ simulation pipeline, không phải dữ liệu vận hành thực tế.</div>
</header>
<main>
  <section class="controls">
    <div>
      <label for="capacitySelect">Analyst capacity</label>
      <select id="capacitySelect">
        <option value="capacity_100">100 reviews/day</option>
        <option value="capacity_20">20 reviews/day</option>
      </select>
    </div>
    <div>
      <label for="costSelect">Cost scenario</label>
      <select id="costSelect"></select>
    </div>
    <div>
      <label for="policySelect">Selected policy</label>
      <select id="policySelect"></select>
    </div>
  </section>

  <section class="cards">
    <div class="card"><div class="card-title">Best policy</div><div id="bestPolicy" class="card-value">-</div><div class="card-note">Theo net benefit trong lựa chọn hiện tại</div></div>
    <div class="card"><div class="card-title">Best net benefit</div><div id="bestBenefit" class="card-value">-</div><div class="card-note">Simulated utility</div></div>
    <div class="card"><div class="card-title">Selected recall</div><div id="selectedRecall" class="card-value">-</div><div class="card-note">Recall trên reviewed cases</div></div>
    <div class="card"><div class="card-title">Selected overflow</div><div id="selectedOverflow" class="card-value">-</div><div class="card-note">Case vượt capacity</div></div>
  </section>

  <div class="grid">
    <div>
      <section class="panel"><h2>Policy net benefit</h2><div id="policyBenefitBars"></div></section>
      <section class="panel"><h2>Recall vs Net benefit</h2><div id="scatterPlot" class="scatter"></div></section>
      <section class="panel"><h2>Policy comparison table</h2><div id="policyTable"></div></section>
    </div>
    <div>
      <section class="panel"><h2>Scenario net benefit</h2><div id="scenarioBars"></div></section>
      <section class="panel"><h2>Selected policy insight</h2><div id="insightPanel" class="insight"></div></section>
      <section class="panel"><h2>Prototype notes</h2><p class="footnote">Dashboard này không cần backend vì dữ liệu đã được sinh trước từ simulation pipeline và nhúng vào HTML. Net benefit là simulated utility under assumptions, dùng để so sánh tương đối giữa policy/scenario.</p><div id="sourceTags"></div></section>
    </div>
  </div>
</main>
<script id="payload" type="application/json">{payload_json}</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
const capacitySelect = document.getElementById('capacitySelect');
const costSelect = document.getElementById('costSelect');
const policySelect = document.getElementById('policySelect');
const money = v => Number(v).toLocaleString(undefined, {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
const pct = v => (Number(v) * 100).toFixed(2) + '%';

function rows() {{
  return DATA.policies[capacitySelect.value].filter(r => r.cost_scenario === costSelect.value);
}}
function selectedRow() {{
  return rows().find(r => r.policy_name === policySelect.value) || rows()[0];
}}
function unique(values) {{ return [...new Set(values)]; }}
function initControls() {{
  const all = DATA.policies.capacity_100;
  unique(all.map(r => r.cost_scenario)).forEach(v => costSelect.add(new Option(v, v)));
  unique(all.map(r => r.policy_name)).forEach(v => policySelect.add(new Option(v, v)));
}}
function barRows(items, labelKey, metricKey, valueKind='money', secondary=false) {{
  const maxAbs = Math.max(...items.map(x => Math.abs(Number(x[metricKey]))), 1);
  return items.map(item => {{
    const value = Number(item[metricKey]);
    const width = Math.abs(value) / maxAbs * 100;
    const cls = value < 0 ? 'negative' : (secondary ? 'secondary' : 'positive');
    const shown = valueKind === 'percent' ? pct(value) : valueKind === 'number' ? value.toLocaleString() : money(value);
    return `<div class="bar-row"><div class="bar-label" title="${{item[labelKey]}}">${{item[labelKey]}}</div><div class="track"><div class="bar ${{cls}}" style="width:${{width}}%"></div></div><div class="bar-value">${{shown}}</div></div>`;
  }}).join('');
}}
function renderScenarioBars() {{
  document.getElementById('scenarioBars').innerHTML = barRows(DATA.scenario, 'scenario', 'net_benefit');
}}
function renderPolicyBars(currentRows) {{
  document.getElementById('policyBenefitBars').innerHTML = barRows(currentRows, 'policy_name', 'net_benefit');
}}
function renderCards(currentRows) {{
  const best = [...currentRows].sort((a,b) => Number(b.net_benefit) - Number(a.net_benefit))[0];
  const sel = selectedRow();
  document.getElementById('bestPolicy').textContent = best.policy_name;
  document.getElementById('bestBenefit').textContent = money(best.net_benefit);
  document.getElementById('selectedRecall').textContent = pct(sel.recall_reviewed);
  document.getElementById('selectedOverflow').textContent = Number(sel.review_overflow).toLocaleString();
}}
function renderTable(currentRows) {{
  const best = [...currentRows].sort((a,b) => Number(b.net_benefit) - Number(a.net_benefit))[0];
  const html = `<table><thead><tr><th>Policy</th><th>Alerts</th><th>Reviewed</th><th>Overflow</th><th>Precision</th><th>Recall</th><th>Net benefit</th></tr></thead><tbody>` +
    currentRows.map(r => `<tr class="${{r.policy_name === best.policy_name ? 'best' : ''}}"><td>${{r.policy_name}}</td><td>${{Number(r.alerts_sent_to_analyst).toLocaleString()}}</td><td>${{Number(r.analyst_reviewed).toLocaleString()}}</td><td>${{Number(r.review_overflow).toLocaleString()}}</td><td>${{pct(r.precision_flagged)}}</td><td>${{pct(r.recall_reviewed)}}</td><td>${{money(r.net_benefit)}}</td></tr>`).join('') +
    `</tbody></table>`;
  document.getElementById('policyTable').innerHTML = html;
}}
function renderScatter(currentRows) {{
  const width = 680, height = 280, pad = 36;
  const maxBenefit = Math.max(...currentRows.map(r => Number(r.net_benefit)), 1);
  const minBenefit = Math.min(...currentRows.map(r => Number(r.net_benefit)), 0);
  const maxRecall = Math.max(...currentRows.map(r => Number(r.recall_reviewed)), 0.01);
  const points = currentRows.map(r => {{
    const x = pad + (Number(r.recall_reviewed) / maxRecall) * (width - pad * 2);
    const y = height - pad - ((Number(r.net_benefit) - minBenefit) / (maxBenefit - minBenefit || 1)) * (height - pad * 2);
    const color = r.policy_name === policySelect.value ? '#dc2626' : '#2563eb';
    return `<g><circle cx="${{x}}" cy="${{y}}" r="7" fill="${{color}}"></circle><text x="${{x+10}}" y="${{y+4}}" font-size="11" fill="#334155">${{r.policy_name}}</text></g>`;
  }}).join('');
  document.getElementById('scatterPlot').innerHTML = `<svg viewBox="0 0 ${{width}} ${{height}}" width="100%" height="280"><line x1="${{pad}}" y1="${{height-pad}}" x2="${{width-pad}}" y2="${{height-pad}}" stroke="#94a3b8"/><line x1="${{pad}}" y1="${{pad}}" x2="${{pad}}" y2="${{height-pad}}" stroke="#94a3b8"/><text x="${{width/2-45}}" y="${{height-8}}" font-size="12" fill="#64748b">Recall reviewed</text><text x="8" y="18" font-size="12" fill="#64748b">Net benefit</text>${{points}}</svg>`;
}}
function renderInsight() {{
  const sel = selectedRow();
  const capacity = capacitySelect.value === 'capacity_100' ? '100 reviews/ngày' : '20 reviews/ngày';
  let lines = [];
  lines.push(`<p>Policy đang chọn: <strong>${{sel.policy_name}}</strong> trong bối cảnh capacity <strong>${{capacity}}</strong> và cost scenario <strong>${{costSelect.value}}</strong>.</p>`);
  lines.push(`<p>Policy này gửi <strong>${{Number(sel.alerts_sent_to_analyst).toLocaleString()}}</strong> alerts, review được <strong>${{Number(sel.analyst_reviewed).toLocaleString()}}</strong>, overflow <strong>${{Number(sel.review_overflow).toLocaleString()}}</strong>, net benefit <strong>${{money(sel.net_benefit)}}</strong>.</p>`);
  if (Number(sel.review_overflow) > 0) lines.push('<p>Điểm cần chú ý: overflow cao cho thấy policy tạo nhu cầu review vượt quá năng lực analyst. Trong đề án, đây là bằng chứng cho ràng buộc vận hành.</p>');
  if (sel.policy_name.includes('sensitive')) lines.push('<p>Policy nhạy thường tăng recall nhưng đổi lại tạo nhiều workload và false positives hơn.</p>');
  if (sel.policy_name.includes('strict')) lines.push('<p>Policy nghiêm giúp giảm workload nhưng có thể bỏ sót nhiều fraud hơn, làm giảm utility.</p>');
  if (sel.policy_name.includes('cost_sensitive')) lines.push('<p>Policy theo expected utility gần với mechanism design nhất, nhưng hiện cần calibration thêm vì tạo nhiều candidate.</p>');
  document.getElementById('insightPanel').innerHTML = lines.join('');
}}
function renderSources() {{
  document.getElementById('sourceTags').innerHTML = Object.entries(DATA.sources).map(([k,v]) => `<span class="tag">${{k}}: ${{v}}</span>`).join('');
}}
function render() {{
  const currentRows = rows();
  if (!currentRows.find(r => r.policy_name === policySelect.value)) policySelect.value = currentRows[0].policy_name;
  renderScenarioBars();
  renderPolicyBars(currentRows);
  renderCards(currentRows);
  renderTable(currentRows);
  renderScatter(currentRows);
  renderInsight();
  renderSources();
}}
initControls();
render();
[capacitySelect, costSelect, policySelect].forEach(el => el.addEventListener('change', render));
</script>
</body>
</html>"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build static interactive dashboard prototype.")
    parser.add_argument("--project-root", type=str, default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output-dir", type=str, default="reports/prototype")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.project_root).resolve()
    scenario_path = latest_csv(root / "data" / "scenario_comparisons", "scenario_comparison_")
    policy_sufficient_path, policy_constrained_path = load_policy_files(root / "data" / "policy_comparisons")

    scenario = pd.read_csv(scenario_path)
    policy_sufficient = pd.read_csv(policy_sufficient_path)
    policy_constrained = pd.read_csv(policy_constrained_path)
    sources = {
        "scenario": scenario_path.name,
        "capacity_100": policy_sufficient_path.name,
        "capacity_20": policy_constrained_path.name,
    }

    out_dir = (root / args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"risk_decision_dashboard_{timestamp}.html"
    out_path.write_text(build_html(scenario, policy_sufficient, policy_constrained, sources), encoding="utf-8")

    print("Interactive dashboard written to:")
    print(str(out_path).encode("ascii", errors="backslashreplace").decode("ascii"))


if __name__ == "__main__":
    main()

