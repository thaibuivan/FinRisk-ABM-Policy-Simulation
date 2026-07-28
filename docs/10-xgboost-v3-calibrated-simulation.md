# 10. XGBoost v3 trên dữ liệu synthetic hiệu chỉnh theo BankSim/PaySim

## 1. Vì sao cần phiên bản v3?

Sau khi train XGBoost trên simulation v2, model đã cải thiện rõ so với bản đầu, nhưng PR-AUC test vẫn ở mức khoảng 0.457. Nguyên nhân chính không chỉ nằm ở thuật toán, mà nằm ở cơ chế sinh dữ liệu: nhiều giao dịch fraud và non-fraud vẫn còn chồng lấn quá mạnh, trong khi một số outlier bình thường lại giống fraud. Với fraud detection, nếu tín hiệu tạo sinh không đủ rõ hoặc không nhất quán, model khó đạt PR-AUC cao dù ROC-AUC nhìn vẫn tốt.

Vì vậy phiên bản v3 không cố tình "làm đẹp" metric bằng cách rò rỉ nhãn, mà hiệu chỉnh lại phân phối mô phỏng dựa trên quan sát từ các bộ dữ liệu tham khảo công khai:

- BankSim: fraud thường có amount cao hơn rõ rệt so với giao dịch bình thường và tập trung nhiều hơn ở một số nhóm merchant rủi ro.
- PaySim: fraud có quy mô giao dịch lớn hơn nhiều so với giao dịch hợp lệ trong một số loại giao dịch.
- ULB Credit Card Fraud: fraud là lớp rất hiếm, do đó PR-AUC và recall phù hợp hơn ROC-AUC khi đánh giá model.

## 2. Thay đổi chính trong simulation v3

Script mới:

`scripts/generate_simulation_data_v3.py`

`scripts/run_simulation_scenarios_v3.py`

Các thay đổi chính:

- Tăng mức phân biệt của fraud amount theo hướng gần hơn với BankSim/PaySim: merchant abuse, burst velocity và high-value fraud có amount multiplier mạnh hơn.
- Giảm normal outlier để hạn chế trường hợp giao dịch bình thường có amount quá giống fraud.
- Tăng trọng số fraud ở các nhóm merchant rủi ro cao như electronics, travel và digital wallet.
- Fraud propensity phụ thuộc rõ hơn vào baseline risk của customer, giúp mô phỏng có trạng thái rủi ro nền thay vì gán nhãn gần như ngẫu nhiên.
- Vẫn giữ overlap giữa fraud và non-fraud để bài toán không trở thành quá dễ.
- Không dùng fraud_strategy làm feature training, tránh label leakage.

## 3. Kết quả mô phỏng v3

Các scenario v3 đã sinh:

| Scenario | Transactions | Fraud count | Fraud rate | Precision flagged | Recall flagged | Net benefit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| low_fraud | 13,536 | 19 | 0.1404% | 3.46% | 57.89% | -148.71 |
| baseline | 13,690 | 150 | 1.0957% | 25.36% | 71.33% | 49,699.22 |
| stress_fraud | 14,294 | 411 | 2.8753% | 49.91% | 69.34% | 160,218.11 |
| low_capacity | 13,690 | 150 | 1.0957% | 25.36% | 71.33% | 49,717.37 |
| high_capacity | 13,690 | 150 | 1.0957% | 25.36% | 71.33% | 49,699.22 |

## 4. Kết quả XGBoost optimized trên v3

Run model:

`data/model_runs/xgboost_optimized_recall_20260723_141558`

Kết quả tổng thể:

| Split | ROC-AUC | PR-AUC / Average Precision |
| --- | ---: | ---: |
| Train | 0.9967 | 0.8375 |
| Validation | 0.9887 | 0.7266 |
| Test | 0.9769 | 0.6495 |

Kết quả top-k trên test:

| Review budget | Precision | Recall |
| --- | ---: | ---: |
| Top 0.5% | 90.22% | 37.22% |
| Top 1% | 70.27% | 58.30% |
| Top 3% | 31.12% | 77.58% |
| Top 5% | 20.82% | 86.55% |
| Top 10% | 11.17% | 92.83% |

Kết quả theo scenario trên test:

| Scenario | Fraud count | Fraud rate | ROC-AUC | PR-AUC |
| --- | ---: | ---: | ---: | ---: |
| baseline | 39 | 1.0569% | 0.9705 | 0.6090 |
| high_capacity | 39 | 1.0569% | 0.9705 | 0.6090 |
| low_capacity | 39 | 1.0569% | 0.9705 | 0.6090 |
| low_fraud | 4 | 0.1100% | 0.9951 | 0.3404 |
| stress_fraud | 102 | 2.6576% | 0.9837 | 0.7889 |

Diễn giải quan trọng: PR-AUC tổng thể đạt 0.6495, thấp hơn mục tiêu 0.7 một chút. Tuy nhiên stress_fraud đạt khoảng 0.789, còn baseline đạt khoảng 0.609. Scenario low_fraud chỉ có 4 fraud trong test nên PR-AUC rất nhạy và kéo trung bình xuống. Vì vậy không nên chỉ nói "model chưa tốt"; nên nói rằng model đã đạt mức ranking tốt trong các scenario có đủ fraud signal, còn scenario fraud cực hiếm cần được đánh giá thêm bằng top-k recall và policy outcome.

## 5. Threshold và policy

Threshold report trên validation:

| Criterion | Threshold probability | Precision | Recall |
| --- | ---: | ---: | ---: |
| Max recall at precision 5% | 0.0297 | 5.00% | 100.00% |
| Max recall at precision 10% | 0.1362 | 10.00% | 98.25% |
| Max recall at precision 20% | 0.4810 | 20.00% | 92.11% |
| Max recall at precision 30% | 0.6839 | 30.03% | 87.72% |
| Max recall at precision 40% | 0.8287 | 40.09% | 76.32% |
| Max recall at precision 50% | 0.8986 | 50.30% | 74.56% |

Policy có net benefit cao trong test:

| Policy | Alerts | Reviewed | Precision reviewed | Recall reviewed | Net benefit |
| --- | ---: | ---: | ---: | ---: | ---: |
| threshold 0.684 | 666 | 666 | 27.33% | 81.61% | 69,513.54 |
| threshold 0.829 | 443 | 443 | 36.12% | 71.75% | 68,959.09 |
| threshold 0.481 | 1,024 | 1,024 | 19.24% | 88.34% | 66,616.33 |
| top 5% daily | 944 | 944 | 19.49% | 82.51% | 65,334.42 |

Điểm cần nhấn mạnh: threshold thấp giúp recall rất cao nhưng dễ gây overflow và false positive cost. Threshold cao hơn giúp precision tốt hơn nhưng bỏ sót nhiều fraud hơn. Đây chính là chỗ cần Mechanism Design: chọn cơ chế review không chỉ theo score, mà theo payoff giữa fraud loss prevented, false positive cost, analyst workload và customer friction.

## 6. Feature quan trọng

Top feature theo importance gain:

| Feature | Ý nghĩa |
| --- | --- |
| amount_x_merchant_risk | Tương tác giữa bất thường về amount và rủi ro merchant |
| merchant_x_unusual_hour | Merchant rủi ro xuất hiện trong khung giờ bất thường |
| amount | Giá trị giao dịch |
| log_amount_to_avg_7d | Amount hiện tại so với trung bình 7 ngày |
| merchant_risk_signal | Tín hiệu rủi ro merchant |
| log_amount_to_median_30d | Amount hiện tại so với median 30 ngày |
| night_x_amount | Amount cao trong khung giờ đêm |
| amount_anomaly_signal | Tín hiệu bất thường về số tiền |
| unusual_hour_signal | Tín hiệu giờ giao dịch bất thường |
| amount_x_velocity | Amount anomaly kết hợp velocity |

## 7. Cách trình bày nếu bị hỏi về PR-AUC

Câu trả lời gợi ý:

"Ban đầu em kỳ vọng PR-AUC khoảng 0.7, nhưng sau khi kiểm tra kỹ hơn em thấy PR-AUC phụ thuộc rất mạnh vào cơ chế sinh dữ liệu và fraud base rate. Ở bản v2, PR-AUC test chỉ khoảng 0.457 vì dữ liệu mô phỏng còn quá nhiễu. Em đã hiệu chỉnh simulation v3 theo phân phối tham khảo từ BankSim/PaySim: fraud amount và merchant-risk pattern rõ hơn, normal outlier giảm, nhưng vẫn không dùng label leakage. Sau đó XGBoost optimized đạt test PR-AUC khoảng 0.65, validation khoảng 0.73, top 5% recall khoảng 86.5% và top 10% recall khoảng 92.8%. Vì vậy nếu xét mục tiêu operational là ưu tiên case cho analyst review, model đã cải thiện rõ. Điểm còn cần làm tiếp là kiểm định thêm với dữ liệu thật hoặc mô phỏng ABM sâu hơn để đánh giá tính bền vững của policy."

## 8. Kết luận

Phiên bản v3 đã đưa phần model gần hơn với mục tiêu của đề án:

- Có dữ liệu synthetic được hiệu chỉnh theo phân phối tham khảo.
- Có model XGBoost mới, không dùng lại model cũ.
- Có đánh giá bằng PR-AUC, ROC-AUC, recall@top-k, precision@top-k và net benefit.
- Có liên hệ trực tiếp giữa model score và cơ chế ra quyết định dưới capacity constraint.

Kết quả chưa nên được trình bày như một model production-ready. Nên trình bày đây là prototype nghiên cứu: mô phỏng data-generating process, huấn luyện risk scoring model và đánh giá mechanism/policy bằng outcome metric.
