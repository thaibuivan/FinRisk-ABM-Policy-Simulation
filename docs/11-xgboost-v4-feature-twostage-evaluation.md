# 11. XGBoost v4: behavior features và two-stage decisioning

## 1. Mục tiêu của v4

Sau phiên bản v3, test PR-AUC đạt khoảng 0.6495, gần mục tiêu 0.7 nhưng chưa vượt qua. Thay vì tiếp tục làm dữ liệu synthetic dễ hơn, phiên bản v4 tập trung vào hai hướng an toàn hơn về mặt học thuật:

1. Cải thiện feature: bổ sung các biến hành vi dựa trên lịch sử giao dịch trước đó.
2. Cải thiện cơ chế decisioning: thêm tầng stage-2 ranking theo expected review value, không chỉ sort theo xác suất fraud.

Cách này phù hợp hơn với định hướng đề án vì không chỉ tối ưu model score, mà còn mô phỏng cơ chế phân bổ sự chú ý của analyst dưới giới hạn capacity.

## 2. Script mới

Script:

`scripts/train_simulation_xgboost_v4_features_twostage.py`

Output đúng sau khi sửa alignment:

`data/model_runs/xgboost_v4_features_twostage_20260723_152304`

Lưu ý: run `xgboost_v4_features_twostage_20260723_151809` là run lỗi do feature sequence bị sort lại nhưng label chưa được đưa về đúng thứ tự. Không dùng run này để báo cáo.

## 3. Feature mới

V4 giữ lại các feature của v3:

- amount anomaly
- velocity signal
- unusual hour signal
- merchant risk signal
- amount-to-history ratios theo 24h, 3d, 7d, 30d
- interaction giữa amount, merchant, timing và velocity

V4 bổ sung thêm nhóm behavior sequence features, chỉ dùng lịch sử trước giao dịch hiện tại:

| Nhóm feature | Ý nghĩa |
| --- | --- |
| category_switch_from_prev | Giao dịch hiện tại có đổi merchant category so với giao dịch trước không |
| channel_switch_from_prev | Giao dịch hiện tại có đổi channel so với giao dịch trước không |
| recent_category_unique_5/10/20 | Số category khác nhau trong 5/10/20 giao dịch trước |
| recent_channel_unique_5/10/20 | Số channel khác nhau trong 5/10/20 giao dịch trước |
| recent_category_entropy_5/10/20 | Mức độ phân tán hành vi merchant category gần đây |
| recent_high_risk_category_share_5/10/20 | Tỷ lệ giao dịch gần đây thuộc nhóm category rủi ro cao |
| recent_wallet_share_5/10/20 | Tỷ lệ giao dịch gần đây qua ví/wallet |
| recent_amount_p99_5/10/20 | Mốc p99 amount trong lịch sử rất gần |
| amount_to_recent_p99_5/10/20 | Amount hiện tại so với p99 gần đây |

Các biến này giúp model nhìn được sự thay đổi hành vi, không chỉ nhìn từng giao dịch riêng lẻ.

## 4. Kết quả model

So sánh v3 và v4 trên test:

| Metric | XGBoost v3 | XGBoost v4 |
| --- | ---: | ---: |
| ROC-AUC | 0.9769 | 0.9755 |
| PR-AUC / Average Precision | 0.6495 | 0.6520 |
| Brier score | 0.0323 | 0.0177 |
| Precision top 0.5% | 90.22% | 91.30% |
| Recall top 0.5% | 37.22% | 37.67% |
| Precision top 1% | 70.27% | 70.27% |
| Recall top 1% | 58.30% | 58.30% |
| Precision top 3% | 31.12% | 31.47% |
| Recall top 3% | 77.58% | 78.48% |
| Precision top 5% | 20.82% | 20.82% |
| Recall top 5% | 86.55% | 86.55% |
| Precision top 10% | 11.17% | 11.22% |
| Recall top 10% | 92.83% | 93.27% |

Nhận xét:

- PR-AUC tăng nhẹ, không phải nhảy vọt.
- Recall top 3% và top 10% tăng nhẹ.
- Brier score giảm mạnh, nghĩa là xác suất dự báo được hiệu chỉnh tốt hơn.
- Feature mới không làm model overfit mạnh: validation PR-AUC khoảng 0.7355, test PR-AUC khoảng 0.6520.

Điều này hợp lý: v3 đã có nhiều signal mạnh; v4 thêm behavior sequence nên cải thiện biên, đặc biệt ở calibration và một số top-k budget.

## 5. Kết quả theo scenario

| Scenario | Fraud count test | Fraud rate | ROC-AUC | PR-AUC |
| --- | ---: | ---: | ---: | ---: |
| baseline | 39 | 1.0569% | 0.9678 | 0.6069 |
| high_capacity | 39 | 1.0569% | 0.9678 | 0.6069 |
| low_capacity | 39 | 1.0569% | 0.9678 | 0.6069 |
| low_fraud | 4 | 0.1100% | 0.9953 | 0.3725 |
| stress_fraud | 102 | 2.6576% | 0.9840 | 0.7881 |

PR-AUC tốt nhất ở stress_fraud vì fraud nhiều hơn và pattern rõ hơn. PR-AUC thấp nhất ở low_fraud vì test chỉ có 4 fraud, nên chỉ cần vài thứ tự ranking sai là metric biến động mạnh.

## 6. Two-stage decisioning

V4 bổ sung stage-2 policy:

Stage 1: XGBoost dự báo xác suất fraud.

Stage 2: Tính expected review value:

expected review value = p(fraud) x amount x recovery rate
                        - p(non-fraud) x false positive cost
                        - analyst review cost

Ý nghĩa:

- Không phải case nào xác suất fraud cao nhất cũng tạo lợi ích nghiệp vụ cao nhất.
- Một case xác suất vừa phải nhưng amount rất lớn có thể đáng review hơn một case xác suất cao nhưng amount nhỏ.
- Stage-2 giúp nối model score với Mechanism Design: phân bổ analyst attention theo payoff và capacity.

## 7. Policy comparison

Một số policy tốt trên test:

| Policy | Reviewed | Precision | Recall | Net benefit |
| --- | ---: | ---: | ---: | ---: |
| xgb threshold 0.386 | 687 | 26.93% | 82.96% | 69,509.92 |
| stage2 EV threshold 50 | 465 | 33.98% | 70.85% | 69,410.90 |
| stage2 EV threshold 25 | 594 | 29.29% | 78.03% | 69,149.25 |
| xgb threshold 0.609 | 431 | 37.12% | 71.75% | 69,072.12 |
| stage2 EV top 3% daily | 585 | 26.32% | 69.06% | 67,368.43 |

Diễn giải:

- Policy tốt nhất theo net benefit vẫn là threshold theo probability.
- Tuy nhiên stage-2 EV threshold 50 đạt net benefit gần tương đương nhưng review ít hơn nhiều: 465 case thay vì 687 case.
- Đây là bằng chứng tốt cho luận điểm mechanism: cùng một model score, cách thiết kế rule phân bổ review có thể thay đổi workload và payoff.

## 8. Feature importance

Top feature v4:

| Feature | Diễn giải |
| --- | --- |
| amount_x_merchant_risk | Amount anomaly kết hợp merchant risk |
| merchant_x_unusual_hour | Merchant risk xuất hiện trong giờ bất thường |
| log_amount | Quy mô giao dịch |
| category_switch_x_merchant_risk | Đổi category kết hợp merchant risk |
| merchant_risk_signal | Tín hiệu rủi ro merchant |
| log_amount_to_median_30d | Amount so với median 30 ngày |
| amount_anomaly_signal | Bất thường về số tiền |
| night_x_amount | Amount cao trong giờ đêm |
| log_amount_to_recent_p99_10 | Amount so với p99 của 10 giao dịch gần đây |
| channel_switch_x_velocity | Đổi channel kết hợp velocity |

Feature mới có xuất hiện trong top importance, đặc biệt là `category_switch_x_merchant_risk`, `log_amount_to_recent_p99_10` và `channel_switch_x_velocity`. Điều này cho thấy behavior sequence features có đóng góp thật, dù mức cải thiện tổng thể không quá lớn.

## 9. Cách trình bày

Câu trả lời gợi ý:

"Sau v3, em không tiếp tục ép dữ liệu synthetic dễ hơn để làm metric đẹp. Em chuyển sang cải thiện feature và cơ chế decisioning. V4 bổ sung các behavior sequence features như đổi merchant category, đổi channel, entropy category gần đây và amount so với p99 gần đây. Kết quả PR-AUC test tăng nhẹ từ 0.6495 lên 0.6520, recall top 10% tăng lên 93.27%, và Brier score giảm rõ từ 0.0323 xuống 0.0177. Phần cải thiện lớn hơn nằm ở decisioning: stage-2 expected value policy có thể đạt net benefit gần tương đương threshold tốt nhất nhưng review ít case hơn. Đây là điểm liên hệ với Mechanism Design: model không chỉ dự báo fraud, mà còn giúp thiết kế cơ chế phân bổ analyst review theo payoff, chi phí và capacity."

## 10. Kết luận

V4 không biến bài toán thành quá dễ, nhưng cải thiện theo hướng hợp lý hơn:

- Thêm feature hành vi mà không dùng label leakage.
- Giữ đánh giá theo PR-AUC, recall@top-k và net benefit.
- Bổ sung stage-2 policy để nối risk scoring với mechanism design.
- Tạo nền tảng để phát triển prototype thành hệ thống quyết định rủi ro có thể so sánh nhiều cơ chế review khác nhau.
