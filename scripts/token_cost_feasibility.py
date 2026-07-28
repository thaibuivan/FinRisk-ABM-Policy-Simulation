from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "token_cost_feasibility_assumptions.json"
OUT_DIR = ROOT / "data" / "token_cost_feasibility"
REPORT_DIR = ROOT / "reports" / "feasibility"


def token_cost(input_tokens: float, output_tokens: float, input_price: float, output_price: float) -> float:
    return (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price


def estimate_for_scenarios(config: Dict, scenario_count: int) -> List[Dict]:
    design = config["experiment_design"]
    pricing = config["pricing_source"]
    baseline_net_benefit = float(config["baseline_policy_net_benefit_usd"])
    rows: List[Dict] = []

    for arch in config["architectures"]:
        calls = (
            scenario_count
            * design["rounds_per_scenario"]
            * design["replications"]
            * arch["llm_agents"]
            * arch["calls_per_agent_round"]
        )
        input_tokens = calls * arch["avg_input_tokens_per_call"]
        output_tokens = calls * arch["avg_output_tokens_per_call"]
        cost = token_cost(
            input_tokens,
            output_tokens,
            pricing["input_usd_per_1m_tokens"],
            pricing["output_usd_per_1m_tokens"],
        )
        expected_improvement = baseline_net_benefit * arch["expected_policy_improvement_pct"]
        net_value_after_token_cost = expected_improvement - cost
        break_even_improvement_pct = 0.0 if baseline_net_benefit == 0 else cost / baseline_net_benefit

        rows.append({
            "architecture": arch["name"],
            "scenario_count": scenario_count,
            "llm_calls": calls,
            "input_tokens": round(input_tokens, 2),
            "output_tokens": round(output_tokens, 2),
            "total_tokens": round(input_tokens + output_tokens, 2),
            "token_cost_usd": round(cost, 6),
            "expected_policy_improvement_pct": arch["expected_policy_improvement_pct"],
            "expected_policy_improvement_usd": round(expected_improvement, 2),
            "net_value_after_token_cost_usd": round(net_value_after_token_cost, 2),
            "break_even_improvement_pct": round(break_even_improvement_pct, 8),
            "description": arch["description"],
        })
    return rows


def write_csv(rows: List[Dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: List[Dict], cols: List[str]) -> str:
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---" for _ in cols]) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join([header, sep, *body])


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    pilot = config["experiment_design"]["pilot_scenarios"]
    scenario_counts = [pilot] + config["experiment_design"]["scale_scenarios"]

    all_rows: List[Dict] = []
    for n in scenario_counts:
        all_rows.extend(estimate_for_scenarios(config, n))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "token_cost_architecture_comparison.csv"
    write_csv(all_rows, csv_path)

    cols = [
        "architecture",
        "scenario_count",
        "llm_calls",
        "total_tokens",
        "token_cost_usd",
        "expected_policy_improvement_usd",
        "net_value_after_token_cost_usd",
        "break_even_improvement_pct",
    ]

    report = f"""# Token Cost Feasibility for LLM Multi-Agent Simulation

## 1. Mục tiêu

Bản đề án hiện tại là rule-based Agent-Based Simulation, gần như không phát sinh token cost. Nếu mở rộng thành khóa luận theo hướng LLM/hybrid multi-agent simulation, cần kiểm tra liệu chi phí token có hợp lý so với giá trị chính sách mà mô phỏng tạo ra hay không.

Câu hỏi feasibility chính:

> LLM/hybrid multi-agent simulation có tạo ra cải thiện đủ lớn trong policy net benefit để bù token cost và latency hay không?

## 2. Kiến trúc so sánh

1. Rule-based ABM: baseline hiện tại, không dùng LLM.
2. Hybrid LLM ABM: customer/fraud/system chạy bằng rule; analyst và policy maker dùng LLM.
3. Full LLM ABM: nhiều tác nhân dùng LLM để suy luận trong từng vòng mô phỏng.

## 3. Công thức tính

Token cost:

`cost = input_tokens / 1,000,000 * input_price + output_tokens / 1,000,000 * output_price`

Số LLM calls:

`calls = scenarios * rounds_per_scenario * replications * llm_agents * calls_per_agent_round`

Economic feasibility:

`net value = expected policy improvement - token cost`

Trong đó expected policy improvement được tính so với baseline policy net benefit hiện tại: `{config['baseline_policy_net_benefit_usd']}` USD.

## 4. Giả định hiện tại

- Model tham chiếu: `{config['pricing_source']['model']}`
- Input price: `{config['pricing_source']['input_usd_per_1m_tokens']}` USD / 1M tokens
- Output price: `{config['pricing_source']['output_usd_per_1m_tokens']}` USD / 1M tokens
- Nguồn giá: {config['pricing_source']['source_url']}
- Pilot: `{config['experiment_design']['pilot_scenarios']}` scenarios, `{config['experiment_design']['rounds_per_scenario']}` rounds/scenario, `{config['experiment_design']['replications']}` replications

## 5. Kết quả ước lượng

{markdown_table(all_rows, cols)}

## 6. Diễn giải ban đầu

Rule-based ABM vẫn là baseline rẻ nhất và phù hợp để chạy nhiều scenario. Full LLM ABM có chi phí cao hơn vì số agent gọi LLM nhiều hơn, nhưng trong cấu hình nhỏ với model rẻ, token cost vẫn chưa phải nút thắt lớn. Tuy nhiên, full LLM có rủi ro latency và độ ổn định cao hơn.

Hybrid LLM ABM là hướng hợp lý nhất để kiểm tra tiếp vì chỉ dùng LLM ở nơi cần reasoning/ngôn ngữ tự nhiên: analyst và policy maker. Nếu hybrid giúp chọn policy tốt hơn hoặc giải thích trade-off tốt hơn trong khi chi phí token thấp, đây là hướng khả thi cho khóa luận.

## 7. Việc cần làm tiếp để kết luận chắc hơn

1. Chạy empirical pilot bằng API key với khoảng 20-50 LLM calls.
2. Ghi lại usage thực tế: prompt tokens, completion tokens, cost, latency.
3. Thay các giả định token/call trong file config bằng số đo thật.
4. So sánh policy được chọn bởi rule-based baseline và hybrid LLM.
5. Kết luận theo tiêu chí: `policy improvement > token cost` và latency chấp nhận được.

## 8. Kết luận tạm thời

Ở mức ước lượng, hướng hybrid LLM multi-agent simulation có vẻ khả thi hơn full LLM. Tuy nhiên, kết luận cuối cùng cần dựa trên pilot thực nghiệm bằng API/LangSmith để đo token cost và latency thật. Nếu hybrid không cải thiện policy net benefit hoặc insight so với rule-based baseline, LLM chỉ nên dùng ở tầng giải thích/report thay vì đưa vào toàn bộ mô phỏng.
"""

    report_path = REPORT_DIR / "token_cost_feasibility.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Wrote {csv_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
