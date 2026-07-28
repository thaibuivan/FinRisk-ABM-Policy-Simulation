# Token Cost Feasibility for LLM Multi-Agent Simulation

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

Trong đó expected policy improvement được tính so với baseline policy net benefit hiện tại: `24295.57` USD.

## 4. Giả định hiện tại

- Model tham chiếu: `gpt-4o-mini`
- Input price: `0.15` USD / 1M tokens
- Output price: `0.6` USD / 1M tokens
- Nguồn giá: https://developers.openai.com/api/docs/models/gpt-4o-mini
- Pilot: `3` scenarios, `5` rounds/scenario, `3` replications

## 5. Kết quả ước lượng

| architecture | scenario_count | llm_calls | total_tokens | token_cost_usd | expected_policy_improvement_usd | net_value_after_token_cost_usd | break_even_improvement_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rule_based_abm | 3 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0.0 |
| hybrid_llm_abm | 3 | 90 | 144000 | 0.03375 | 728.87 | 728.83 | 1.39e-06 |
| full_llm_abm | 3 | 225 | 416250 | 0.097875 | 1214.78 | 1214.68 | 4.03e-06 |
| rule_based_abm | 100 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0.0 |
| hybrid_llm_abm | 100 | 3000 | 4800000 | 1.125 | 728.87 | 727.74 | 4.63e-05 |
| full_llm_abm | 100 | 7500 | 13875000 | 3.2625 | 1214.78 | 1211.52 | 0.00013428 |
| rule_based_abm | 1000 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0.0 |
| hybrid_llm_abm | 1000 | 30000 | 48000000 | 11.25 | 728.87 | 717.62 | 0.00046305 |
| full_llm_abm | 1000 | 75000 | 138750000 | 32.625 | 1214.78 | 1182.15 | 0.00134284 |

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
