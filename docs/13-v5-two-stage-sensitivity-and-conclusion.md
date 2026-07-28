# 13. Kết luận kiểm tra lại: model hai tầng có thực sự tốt hơn không?

## 1. Câu trả lời ngắn

Model hai tầng không tốt hơn tuyệt đối trong mọi metric.

Kết luận đúng hơn là:

- Nếu mục tiêu là tối đa recall và analyst có thể review nhiều case, Stage 1 probability ranking vẫn rất mạnh.
- Nếu mục tiêu là giảm false positive, giảm workload và ưu tiên case có chất lượng cao khi review budget thấp hoặc trung bình, model hai tầng có lợi thế.
- Vì vậy model hai tầng phù hợp nhất trong bối cảnh analyst capacity bị giới hạn, không phải trong bối cảnh review càng nhiều càng tốt.

Đây là kết luận hợp với hướng Mechanism Design: cơ chế tốt phụ thuộc vào KPI và ràng buộc vận hành.

## 2. Ranking metric toàn bộ test set

| Ranking | ROC-AUC | PR-AUC |
| --- | ---: | ---: |
| Stage 1 only | 0.9741 | 0.6450 |
| Two-stage combined | 0.9269 | 0.6585 |
| Stage 1 expected value | 0.9335 | 0.6134 |
| Stage 2 expected value | 0.8162 | 0.5719 |

Diễn giải:

- Two-stage combined có PR-AUC cao hơn nhẹ: 0.6585 so với 0.6450.
- Nhưng ROC-AUC giảm vì các non-candidate bị đẩy xuống điểm rất thấp, làm ranking toàn cục kém mượt hơn.
- Vì vậy không nên nói two-stage làm model tốt hơn toàn diện. Nó cải thiện nhẹ PR-AUC nhưng có đánh đổi.

## 3. Candidate capture của Stage 1

Stage 1 chọn top 10% giao dịch rủi ro cao theo từng ngày/scenario.

| Candidate rate | Candidate count | Fraud count | Fraud in candidates | Candidate precision | Candidate recall |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10.11% | 1875 | 223 | 196 | 10.45% | 87.89% |

Diễn giải:

- Stage 1 bắt được khoảng 87.89% fraud trong nhóm candidate.
- Khoảng 12.11% fraud nằm ngoài candidate, nên Stage 2 không thể cứu các case đó.
- Đây là lý do khi review budget rất cao, Stage 1 full ranking có thể tốt hơn two-stage.

## 4. So sánh tại cùng review budget

| Review budget | Stage 1 precision | Stage 1 recall | Two-stage precision | Two-stage recall | Net benefit delta |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 93.00% | 41.70% | 93.00% | 41.70% | +350.09 |
| 200 | 66.50% | 59.64% | 66.50% | 59.64% | +2677.27 |
| 300 | 49.33% | 66.37% | 52.00% | 69.96% | +2774.68 |
| 400 | 39.75% | 71.30% | 40.50% | 72.65% | -105.89 |
| 500 | 34.00% | 76.23% | 33.60% | 75.34% | -684.95 |
| 700 | 25.71% | 80.72% | 24.71% | 77.58% | -933.08 |
| 944 | 19.70% | 83.41% | 19.49% | 82.51% | -208.72 |
| 1200 | 15.67% | 84.30% | 15.75% | 84.75% | -50.05 |
| 1875 | 10.83% | 91.03% | 10.45% | 87.89% | -329.90 |

Diễn giải:

- Ở budget 300, two-stage tốt hơn rõ nhất: precision tăng từ 49.33% lên 52.00%, recall tăng từ 66.37% lên 69.96%, net benefit tăng khoảng 2774.68 đơn vị payoff mô phỏng.
- Ở budget 500 trở lên, Stage 1 thường giữ recall và net benefit tốt hơn.
- Do đó two-stage phù hợp khi analyst capacity thấp hoặc trung bình, còn Stage 1 phù hợp khi cần mở rộng coverage.

## 5. Best policy theo cost/capacity

Kết quả sensitivity cho thấy:

- Khi review budget thấp hoặc trung bình, các policy dựa trên expected value hoặc two-stage thường có lợi thế.
- Khi review budget cao, Stage 1 probability ranking thường thắng vì nó không bị giới hạn bởi candidate gate.
- Khi false positive cost hoặc analyst cost cao, two-stage/expected-value policy hợp lý hơn vì giảm số case review kém giá trị.

## 6. Kết luận nên dùng trong đề án

Không nên trình bày rằng model hai tầng luôn tốt hơn model một tầng.

Cách trình bày đúng và thuyết phục hơn:

> Model hai tầng được dùng như một cơ chế ưu tiên case dưới ràng buộc năng lực analyst. Nó không thay thế hoàn toàn Stage 1, mà giúp chọn các case đáng review hơn trong điều kiện review budget có giới hạn. Khi capacity cao và mục tiêu là recall tối đa, Stage 1 ranking vẫn nên được giữ làm baseline mạnh.

Hướng này làm đề án tốt hơn vì không chỉ hỏi model nào có metric cao hơn, mà hỏi cơ chế nào phù hợp với mục tiêu vận hành:

- giảm fraud loss,
- giảm false positive cost,
- kiểm soát analyst workload,
- giảm customer friction,
- và tối ưu net benefit.

## 7. File kết quả liên quan

Các file sensitivity đã được lưu trong:

`data/model_runs/xgboost_v5_true_twostage_20260723_160243/analysis/`

Bao gồm:

- `v5_full_ranking_metrics.csv`
- `v5_candidate_capture_summary.csv`
- `v5_budget_cost_sensitivity.csv`
- `v5_stage1_vs_twostage_base_budget_summary.csv`
