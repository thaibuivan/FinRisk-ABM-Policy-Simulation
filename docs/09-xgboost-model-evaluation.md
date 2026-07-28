# Ghi chú đánh giá XGBoost risk model

File này ghi lại nhánh model XGBoost mới được huấn luyện trên dữ liệu mô phỏng native của đề án.
Mục tiêu không chỉ là tối đa hóa metric ML, mà còn kiểm tra model có giúp cơ chế ra quyết định tạo net benefit tốt hơn không.

## 1. Model đã dùng

Model: XGBoost classifier (`XGBClassifier`).

Dữ liệu huấn luyện được lấy từ các scenario mô phỏng:

- low_fraud
- baseline
- stress_fraud
- low_capacity
- high_capacity

Dữ liệu đầu vào gồm:

- transaction features: amount, log_amount, hour, merchant category, channel
- risk signals: amount anomaly, velocity, unusual hour, merchant risk, baseline risk
- behavior features: count, total amount, average, median, p95 trong các window 1h, 24h, 3d, 7d, 30d

Split dữ liệu theo thời gian:

- train: phần lịch sử cũ hơn
- validation: 4 ngày trước test
- test: 8 ngày cuối

Cách split theo thời gian phù hợp hơn random split vì bài toán risk/transaction là bài toán dữ liệu tuần tự.

## 2. Kết quả chính

Run được chọn:

`data/model_runs/xgboost_simulation_risk_model_20260723_112944`

Kết quả test:

| Metric | Giá trị |
| --- | ---: |
| ROC-AUC | 0.9264 |
| PR-AUC / Average Precision | 0.3179 |
| Precision top 0.5% | 57.07% |
| Recall top 0.5% | 21.78% |
| Precision top 1% | 40.49% |
| Recall top 1% | 30.91% |
| Precision top 5% | 15.09% |
| Recall top 5% | 57.68% |

## 3. Cách diễn giải

PR-AUC không đạt 0.75 trên bộ simulation mới. Con số khoảng 0.75 nếu có nhiều khả năng đến từ dataset/model cũ hoặc từ train set.
Với dữ liệu test theo thời gian hiện tại, XGBoost đạt PR-AUC khoảng 0.318.

Tuy nhiên, XGBoost vẫn có điểm mạnh:

- ROC-AUC cao hơn logistic baseline.
- Precision ở nhóm top 0.5% và top 1% cao hơn, tức là phù hợp khi analyst chỉ có capacity xử lý một nhóm case rất nhỏ.
- Policy net benefit tốt nhất đạt khoảng 119,920 trong giả định chi phí hiện tại.

Vì vậy, trong đề án nên trình bày XGBoost như một model branch mạnh hơn cho ranking case ưu tiên, không nên khẳng định model đã tối ưu tuyệt đối.

## 4. Kết quả policy/outcome

Policy tốt nhất trong run được chọn:

| Policy | Net benefit | Precision reviewed | Recall reviewed | Reviewed |
| --- | ---: | ---: | ---: | ---: |
| threshold 0.826 | 119,920.71 | 20.96% | 45.44% | 1,045 |
| top 3% daily | 118,629.89 | 19.82% | 46.27% | 1,125 |
| top 5% daily | 115,857.56 | 15.02% | 57.88% | 1,858 |

Ý nghĩa: policy có recall cao nhất chưa chắc tạo lợi ích ròng cao nhất. Đây là điểm phù hợp với hướng Mechanism Design của đề án:
thiết kế cơ chế phải cân bằng fraud loss prevented, false positive cost, analyst cost và capacity constraint.

## 5. Feature importance

Các feature quan trọng nhất theo gain:

- merchant_category_food
- merchant_category_transportation
- merchant_risk_signal
- amount_anomaly_signal
- unusual_hour_signal
- log_amount
- amount
- hour

Diễn giải: model không chỉ học theo số tiền, mà còn học theo merchant category, rủi ro merchant, anomaly và timing signal.

## 6. Lưu ý khi trình bày

Nên nói:

"Em đã chuyển từ proxy score/logistic baseline sang XGBoost branch để tăng khả năng ranking case rủi ro. Trên test split theo thời gian, model đạt ROC-AUC khoảng 0.926 và PR-AUC khoảng 0.318. Dù PR-AUC chưa cao như kỳ vọng ban đầu, precision ở nhóm top 0.5%-1% khá tốt, phù hợp với bối cảnh analyst capacity giới hạn. Vì vậy em đánh giá model không chỉ bằng metric ML, mà còn bằng policy net benefit."

Không nên nói:

"Model chắc chắn đạt PR-AUC 0.75" nếu chưa có kết quả test tương ứng trên đúng bộ dữ liệu mới.


## 7. Phiên bản tối ưu theo PR-AUC và recall

Sau khi xác định PR-AUC và recall là hai metric trung tâm của bài toán fraud detection,
đề án bổ sung script:

`scripts/train_simulation_xgboost_optimized.py`

Script này khác bản XGBoost đầu tiên ở ba điểm:

- Thêm engineered features: amount-to-history ratios, night-hour signal, short-gap signal và interaction giữa amount/merchant/timing/velocity.
- Chạy tuning nhiều cấu hình XGBoost thay vì dùng một bộ tham số cố định.
- Chọn model theo validation objective ưu tiên PR-AUC, recall@5%, recall@10% và precision@1%.

Run được chọn:

`data/model_runs/xgboost_optimized_recall_20260723_114146`

Kết quả test:

| Metric | Giá trị |
| --- | ---: |
| ROC-AUC | 0.9251 |
| PR-AUC / Average Precision | 0.3229 |
| Precision top 0.5% | 58.15% |
| Recall top 0.5% | 22.20% |
| Precision top 1% | 41.58% |
| Recall top 1% | 31.74% |
| Precision top 5% | 15.26% |
| Recall top 5% | 58.30% |
| Precision top 10% | 9.61% |
| Recall top 10% | 73.44% |

So với XGBoost ban đầu, phiên bản optimized cải thiện PR-AUC từ khoảng 0.3179 lên 0.3229,
precision top 1% từ khoảng 40.49% lên 41.58%, và recall top 10% từ khoảng 69.21% lên 73.44%.

Điểm quan trọng khi trình bày:

- Với fraud detection, PR-AUC và recall là metric chính vì fraud là lớp hiếm và bỏ sót fraud có chi phí cao.
- Tuy nhiên recall phải được đọc cùng review capacity. Nếu threshold quá thấp, recall cao nhưng overflow rất lớn.
- Vì vậy đề án dùng thêm recall@top-k để phản ánh tình huống analyst chỉ có thể review một tỷ lệ case nhất định.
- Net benefit không thay thế PR-AUC/recall; nó là metric nghiệp vụ bổ sung để kiểm tra policy có khả thi trong vận hành không.

Câu trình bày gợi ý:

"Sau khi xem lại bài toán fraud detection, em ưu tiên PR-AUC và recall thay vì chỉ nhìn ROC-AUC hoặc net benefit.
Em bổ sung XGBoost optimized branch với feature ratio theo lịch sử giao dịch và tuning theo validation PR-AUC/recall.
Trên test split theo thời gian, model đạt PR-AUC khoảng 0.323; recall top 5% khoảng 58.3% và recall top 10% khoảng 73.4%.
Điều này cho thấy nếu analyst review nhóm case rủi ro cao nhất, hệ thống có thể bắt được phần lớn fraud trong giới hạn workload hợp lý hơn so với review toàn bộ."


## 8. V2 simulation và kết quả model cải thiện

Sau khi phân tích kết quả ban đầu, vấn đề chính không chỉ nằm ở model mà còn ở cơ chế sinh dữ liệu.
Trong bản simulation đầu tiên, nhãn fraud được bốc gần như trực tiếp theo `fraud_rate`, sau đó mới gán strategy,
amount, merchant và timing pattern. Cách này tạo ra một phần nhiễu lớn: nhiều fraud không có pattern đủ rõ để model học,
trong khi một số giao dịch thường lại có outlier giống fraud. Vì vậy PR-AUC bị giới hạn.

Đề án bổ sung simulator v2:

`scripts/generate_simulation_data_v2.py`

Các thay đổi chính:

- Fraud propensity phụ thuộc thêm vào `baseline_risk` của customer.
- Giảm tỷ lệ normal outlier có số tiền quá giống fraud.
- Giảm tỷ trọng `low_amount_probe`, vì nhóm này cố tình giống giao dịch thường và làm bài toán khó hơn.
- Làm các strategy như high amount, burst velocity, merchant abuse có tín hiệu rõ hơn nhưng vẫn giữ overlap với giao dịch thường.
- Giữ nguyên cách đánh giá bằng split theo thời gian và không dùng `fraud_strategy` làm feature để tránh leakage.

Kết quả diagnostic của risk score mô phỏng trên test:

| Phiên bản dữ liệu | Risk score PR-AUC test |
| --- | ---: |
| Simulation v1 | 0.1602 |
| Simulation v2 | 0.2888 |

Điều này cho thấy v2 có cấu trúc tín hiệu hợp lý hơn cho bài toán fraud detection.

Sau đó train lại XGBoost optimized trên simulation v2:

Run:

`data/model_runs/xgboost_optimized_recall_20260723_122805`

Kết quả test:

| Metric | Giá trị |
| --- | ---: |
| ROC-AUC | 0.9498 |
| PR-AUC / Average Precision | 0.4573 |
| Precision top 0.5% | 61.96% |
| Recall top 0.5% | 29.69% |
| Precision top 1% | 46.49% |
| Recall top 1% | 44.79% |
| Precision top 3% | 22.80% |
| Recall top 3% | 66.15% |
| Precision top 5% | 15.30% |
| Recall top 5% | 73.96% |
| Precision top 10% | 8.46% |
| Recall top 10% | 81.77% |

Diễn giải:

- PR-AUC tăng rõ so với bản trước, từ khoảng 0.323 lên 0.457.
- Recall@top-k cải thiện đáng kể, phù hợp với mục tiêu fraud detection là giảm bỏ sót fraud.
- Precision top 1% đạt khoảng 46.5%, nghĩa là trong nhóm case ưu tiên rất cao, gần một nửa là fraud mô phỏng.
- Nếu analyst review top 5% case rủi ro nhất, model bắt được khoảng 74% fraud trong test set.

Điểm cần trình bày cẩn thận:

Kết quả cải thiện không phải do dùng `fraud_strategy` hay label leakage. Cải thiện đến từ việc thiết kế lại cơ chế mô phỏng:
fraud không còn là nhãn gần như ngẫu nhiên, mà liên hệ hợp lý hơn với customer risk state, amount anomaly, merchant risk và timing behavior.
Đây chính là tư duy mà đề án muốn nhấn mạnh: phải xác định cơ chế tạo sinh và KPI trước, rồi mới đánh giá model.
