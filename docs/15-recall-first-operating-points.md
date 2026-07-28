# 15. Recall-first operating points cho bài toán fraud detection

## 1. Vì sao cần phân tích recall-first?

Trong fraud detection, bỏ sót giao dịch gian lận thường nghiêm trọng hơn việc review nhầm một giao dịch bình thường. Vì vậy, ngoài precision và PR-AUC, đề án cần trả lời câu hỏi vận hành quan trọng hơn:

> Nếu tổ chức muốn đạt recall 80%, 90% hoặc 95%, hệ thống phải gửi bao nhiêu case cho analyst review và precision/net benefit sẽ thay đổi ra sao?

Phân tích này giúp tránh hiểu nhầm rằng mục tiêu duy nhất là chọn top 300 case. Top-k/review budget chỉ là proxy cho analyst capacity. Khi tổ chức có năng lực xử lý lớn hơn, có thể chọn operating point theo hướng recall-first.

## 2. Cách tính

Phân tích sử dụng file test score đã lưu từ model V5:

`data/model_runs/xgboost_v5_true_twostage_20260723_160243/v5_test_scores.csv`

Với mỗi policy/ranking score, hệ thống:

1. Sắp xếp giao dịch theo điểm rủi ro giảm dần.
2. Chọn số lượng case nhỏ nhất sao cho đạt target recall.
3. Tính lại precision, số case reviewed, review rate, false positive và net benefit.

Các target recall được kiểm tra:

- 70%
- 80%
- 85%
- 90%
- 95%

## 3. Kết quả base cost

| Target recall | Policy | Actual recall | Precision | Reviewed | Review rate | TP | FP | Net benefit |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 70% | Stage 1 probability | 70.40% | 41.76% | 376 | 2.03% | 157 | 219 | 70935.79 |
| 70% | Two-stage model | 70.40% | 47.72% | 329 | 1.77% | 157 | 172 | 70099.07 |
| 80% | Stage 1 probability | 80.27% | 26.28% | 681 | 3.67% | 179 | 502 | 69337.99 |
| 80% | Two-stage model | 80.27% | 20.53% | 872 | 4.70% | 179 | 693 | 66795.02 |
| 85% | Stage 1 probability | 85.20% | 15.30% | 1242 | 6.70% | 190 | 1052 | 63862.69 |
| 85% | Two-stage model | 85.20% | 15.19% | 1251 | 6.75% | 190 | 1061 | 63697.82 |
| 90% | Stage 1 probability | 90.13% | 12.32% | 1632 | 8.80% | 201 | 1431 | 60479.25 |
| 90% | Two-stage model | 90.13% | 2.77% | 7254 | 39.12% | 201 | 7053 | 9258.11 |
| 95% | Stage 1 probability | 95.07% | 5.84% | 3628 | 19.56% | 212 | 3416 | 41395.73 |
| 95% | Two-stage model | 95.07% | 1.66% | 12768 | 68.85% | 212 | 12556 | -40219.26 |

## 4. Diễn giải chính

Khi chuyển sang mục tiêu recall-first, Stage 1 probability là baseline mạnh nhất.

Lý do:

- Stage 1 xếp hạng toàn bộ test set nên có thể tăng threshold review để bắt thêm fraud.
- Two-stage bị giới hạn bởi candidate gate. Nếu fraud không nằm trong candidate ban đầu, Stage 2 không thể ưu tiên lại case đó.
- Ở target recall 90% và 95%, two-stage phải review rất nhiều case mới đạt cùng recall, làm precision và net benefit giảm mạnh.

Điều này không có nghĩa model hai tầng vô dụng. Nó cho thấy model hai tầng nên được dùng đúng vai trò:

- ưu tiên case khi analyst capacity thấp hoặc trung bình,
- giảm false positive trong nhóm cần escalation,
- hỗ trợ cost-aware ranking,
- không thay thế hoàn toàn recall-first Stage 1.

## 5. Kết luận vận hành

Nếu tổ chức ưu tiên giảm false negative, nên dùng Stage 1 theo hướng recall-first:

- chọn threshold để đạt recall mục tiêu,
- chấp nhận precision thấp hơn,
- dùng analyst capacity và AI explanation để xử lý nhiều alert hơn.

Nếu tổ chức bị giới hạn capacity hoặc false positive cost cao, có thể dùng two-stage/cost-aware policy để ưu tiên các case có expected value cao.

Cách trình bày nên dùng trong đề án:

> Stage 1 phù hợp cho lớp phát hiện rộng nhằm tối đa recall. Stage 2 phù hợp cho lớp ưu tiên và ra quyết định dưới ràng buộc capacity/cost. Cơ chế tối ưu không cố định mà phụ thuộc vào mục tiêu vận hành: recall-first, cost-control hay workload-control.

## 6. File kết quả

Kết quả chi tiết được lưu tại:

`data/model_runs/xgboost_v5_true_twostage_20260723_160243/analysis/`

Các file mới:

- `v5_recall_first_operating_points.csv`
- `v5_recall_first_by_scenario.csv`
