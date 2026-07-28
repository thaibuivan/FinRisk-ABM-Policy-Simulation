# 12. XGBoost v5: true two-stage model để giảm false positive

## 1. Mục tiêu

Phiên bản v4 đã có hai tầng decisioning, nhưng tầng 2 mới là một rule expected value, chưa phải một model ML riêng. Phiên bản v5 triển khai đúng hướng two-stage fraud detection:

- Stage 1: model screening bắt rộng giao dịch nghi ngờ, ưu tiên recall.
- Stage 2: model false-positive reduction/ranker chỉ chạy trên candidate từ Stage 1.

Ý tưởng giống hơn với hệ thống fraud thực tế: không dùng một model duy nhất cho toàn bộ giao dịch, mà dùng model đầu để tạo alert candidate, sau đó dùng model thứ hai để lọc và ưu tiên các case đáng review nhất.

## 2. Script và output

Script:

`scripts/train_simulation_xgboost_v5_true_twostage.py`

Run đúng:

`data/model_runs/xgboost_v5_true_twostage_20260723_160243`

## 3. Thiết kế tránh leakage

Để tránh Stage 2 học trên xác suất Stage 1 được dự đoán ngay trên dữ liệu Stage 1 vừa fit, training được chia theo thời gian:

- Stage 1 train trên phần train sớm.
- Stage 1 tạo candidate cho phần train muộn.
- Stage 2 train trên candidate của phần train muộn.
- Validation và test vẫn là các giai đoạn thời gian sau đó.

Cách này bảo thủ hơn so với train Stage 1 trên toàn bộ train rồi dùng in-sample probability để train Stage 2.

## 4. Candidate generation

Stage 1 chọn top 10% giao dịch rủi ro cao nhất theo từng scenario/ngày.

| Split | Rows | Candidates | Fraud count | Candidate precision | Candidate recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Stage2 train | 18,772 | 1,891 | 253 | 12.06% | 90.12% |
| Validation | 9,018 | 910 | 114 | 11.76% | 93.86% |
| Test | 18,545 | 1,875 | 223 | 10.45% | 87.89% |

Diễn giải:

- Stage 1 đã giảm khối lượng từ toàn bộ giao dịch xuống khoảng 10%.
- Trong test, candidate set vẫn giữ được khoảng 87.89% fraud.
- Đây là trade-off hợp lý: giảm rất nhiều workload trước khi đưa vào Stage 2, nhưng vẫn giữ phần lớn fraud để model 2 lọc tiếp.

## 5. Stage 1 metrics

Stage 1 trên toàn bộ test:

| Metric | Giá trị |
| --- | ---: |
| ROC-AUC | 0.9741 |
| PR-AUC / Average Precision | 0.6450 |
| Brier score | 0.0134 |
| Precision top 1% | 69.19% |
| Recall top 1% | 57.40% |
| Precision top 5% | 20.06% |
| Recall top 5% | 83.41% |
| Precision top 10% | 10.95% |
| Recall top 10% | 91.03% |

Stage 1 thấp hơn nhẹ so với v4 vì nó chỉ train trên phần train sớm để tạo xác suất out-of-time cho Stage 2. Đây là đánh đổi chấp nhận được để giảm leakage.

## 6. Stage 2 metrics trên candidate

Stage 2 chỉ được đánh giá trên candidate do Stage 1 đưa ra.

| Split | Rows | Fraud count | Fraud rate | ROC-AUC | PR-AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validation candidates | 910 | 107 | 11.76% | 0.9080 | 0.7627 |
| Test candidates | 1,875 | 196 | 10.45% | 0.9123 | 0.7475 |

Top-k trên test candidates:

| Candidate budget | Precision | Recall trong candidate |
| --- | ---: | ---: |
| Top 25% candidates | 35.47% | 84.69% |
| Top 50% candidates | 19.64% | 93.88% |
| Top 75% candidates | 13.73% | 98.47% |

Điểm quan trọng:

- Stage 2 PR-AUC trên candidate đạt 0.7475, cao hơn PR-AUC toàn bộ test vì candidate set đã giàu fraud hơn.
- Đây chính là mục tiêu của two-stage modeling: model 2 không cần giải lại bài toán toàn bộ dataset, mà tập trung giảm false positive trong vùng đã bị nghi ngờ.

## 7. Policy comparison

So sánh policy trên test:

| Policy | Reviewed | Precision | Recall | Net benefit |
| --- | ---: | ---: | ---: | ---: |
| Two-stage threshold 0.300 | 434 | 37.56% | 73.09% | 70,409.96 |
| Two-stage threshold 0.600 | 283 | 54.42% | 69.06% | 70,159.34 |
| Two-stage threshold 0.500 | 338 | 46.45% | 70.40% | 69,961.87 |
| Two-stage threshold 0.400 | 363 | 43.53% | 70.85% | 69,798.00 |
| Stage1 only top 5% daily | 944 | 19.28% | 81.61% | 66,563.30 |
| Stage1 only top 3% daily | 585 | 26.67% | 69.96% | 64,487.38 |

Diễn giải:

- Stage1 only top 5% bắt được recall cao hơn, nhưng review 944 case với precision chỉ 19.28%.
- Two-stage threshold 0.300 review 434 case, precision tăng lên 37.56%, recall vẫn giữ 73.09%, và net benefit cao hơn.
- Two-stage threshold 0.600 review chỉ 283 case, precision đạt 54.42%, recall 69.06%, net benefit vẫn rất cao.

Điểm cải thiện chính của model 2 không phải là làm PR-AUC toàn bộ dataset tăng mạnh, mà là:

- giảm false positive trong nhóm review,
- tăng precision của analyst queue,
- giảm workload,
- tăng net benefit.

## 8. Feature quan trọng của Stage 2

Top feature của Stage 2:

| Feature | Ý nghĩa |
| --- | --- |
| stage1_expected_review_value | Giá trị review kỳ vọng từ Stage 1 |
| stage1_score | Điểm rủi ro Stage 1 |
| merchant_x_unusual_hour | Merchant rủi ro trong giờ bất thường |
| stage1_probability | Xác suất fraud từ Stage 1 |
| log_amount_to_median_30d | Amount so với median 30 ngày |
| amount_to_median_30d | Tỷ lệ amount so với median 30 ngày |
| stage1_expected_loss | Expected loss từ Stage 1 |
| is_night_hour | Giao dịch trong giờ đêm |
| recent_card_present_share_20 | Tỷ lệ card-present trong 20 giao dịch gần đây |
| recent_amount_max_20 | Max amount trong 20 giao dịch gần đây |

Điều này cho thấy Stage 2 thực sự sử dụng cả output của Stage 1 và các biến hành vi/bối cảnh để lọc candidate.

## 9. Cách trình bày

Câu trả lời gợi ý:

"Sau v4, em triển khai thêm một true two-stage model. Stage 1 là XGBoost screening model, chọn top 10% giao dịch rủi ro cao theo từng ngày để giữ recall cao. Trong test, candidate set giữ được khoảng 87.9% fraud nhưng chỉ còn khoảng 10% tổng giao dịch. Stage 2 là một XGBoost model thứ hai, chỉ train trên candidate để giảm false positive và rerank alert. Trên test candidates, Stage 2 đạt PR-AUC khoảng 0.7475. Khi đưa vào policy, two-stage threshold 0.3 review 434 case với precision 37.6% và net benefit khoảng 70.4k, cao hơn stage1-only top 5% dù review ít hơn nhiều. Vì vậy cải thiện chính của tầng 2 không phải chỉ là PR-AUC toàn bộ dataset, mà là giảm false positive, giảm workload và tăng hiệu quả phân bổ analyst review."

## 10. Kết luận

V5 là phiên bản phù hợp nhất nếu muốn trình bày đề án theo hướng model hai tầng:

- Stage 1 tối ưu screening và recall.
- Stage 2 tối ưu lọc false positive trong vùng nghi ngờ.
- Kết quả được đánh giá bằng candidate recall, candidate PR-AUC, final precision, recall, workload và net benefit.
- Cách thiết kế này liên kết trực tiếp với Mechanism Design vì bài toán cuối cùng là phân bổ năng lực review hữu hạn, không chỉ dự báo nhãn fraud.
