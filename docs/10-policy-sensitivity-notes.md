# 10 - Ghi chú so sánh policy và sensitivity analysis

## Mục tiêu

Bước này so sánh nhiều cơ chế ra quyết định trên cùng một simulation baseline. Khác với scenario comparison, ở đây mỗi giao dịch và risk score được giữ nguyên; chỉ thay đổi policy và cost assumptions.

Câu hỏi nghiên cứu:

> Với cùng một risk score, policy nào tạo trade-off tốt hơn giữa fraud loss, false positive cost và analyst workload?

Đây là phần gần nhất với hướng mechanism design: không chỉ dự báo rủi ro, mà thiết kế luật quyết định dựa trên KPI nghiệp vụ.

## Files liên quan

- `config/cost_assumptions.json`: giả định chi phí và các sensitivity scenarios.
- `scripts/compare_decision_policies.py`: script so sánh policy.
- `data/policy_comparisons/policy_comparison_20260721_110505.csv`: kết quả với analyst capacity 100/ngày.
- `data/policy_comparisons/policy_comparison_20260721_110642.csv`: kết quả với analyst capacity 20/ngày.

## Cost assumptions

Base assumptions hiện tại:

| Tham số | Ý nghĩa | Giá trị |
|---|---|---:|
| fraud_recovery_rate | Tỷ lệ tổn thất fraud có thể ngăn chặn khi review đúng | 0.75 |
| false_positive_fixed_cost | Chi phí cố định cho một false positive/friction | 3.0 |
| false_positive_variable_rate | Chi phí biến đổi theo amount của false positive | 0.01 |
| analyst_cost_per_minute | Chi phí mô phỏng cho một phút analyst review | 0.45 |
| review_minutes_high_risk | Thời gian review case high risk | 9.0 |
| review_minutes_medium_risk | Thời gian review case medium risk | 6.0 |

Đơn vị là `simulated money unit`, không phải USD/VND thực tế.

## Các policy được so sánh

- `balanced_threshold`: review nếu score >= 70, simulated step-up/hold nếu score >= 90.
- `sensitive_threshold`: review nếu score >= 50, simulated step-up/hold nếu score >= 85. Policy này tăng recall nhưng tăng workload và false positives.
- `strict_threshold`: review nếu score >= 85, simulated step-up/hold nếu score >= 95. Policy này giảm workload nhưng có thể bỏ sót nhiều fraud hơn.
- `capacity_aware`: candidate nếu score >= 50, xếp hạng theo risk score và review theo daily capacity.
- `cost_sensitive`: review khi expected review utility > 0, xếp hạng theo expected value.

## Kết quả với analyst capacity 100/ngày

| Policy | Alerts | Reviewed | Overflow | Precision flagged | Recall reviewed | Net benefit |
|---|---:|---:|---:|---:|---:|---:|
| balanced_threshold | 884 | 884 | 0 | 12.33% | 36.95% | 52,188.14 |
| sensitive_threshold | 1,645 | 1,645 | 0 | 8.33% | 46.44% | 54,234.31 |
| strict_threshold | 411 | 411 | 0 | 18.73% | 26.10% | 16,114.78 |
| capacity_aware | 1,645 | 1,645 | 0 | 8.33% | 46.44% | 54,234.31 |
| cost_sensitive | 10,105 | 3,000 | 7,105 | 2.31% | 52.54% | 26,777.88 |

Nhận xét: Khi capacity đủ, `sensitive_threshold` có net benefit cao nhất trong base cost scenario vì recall tăng đủ để bù cho false positive và analyst cost. `strict_threshold` có precision cao hơn nhưng recall thấp, làm fraud loss realized lớn hơn nên net benefit kém. `cost_sensitive` hiện chưa tốt vì expected value quá rộng, tạo quá nhiều candidate và overflow.

## Kết quả với analyst capacity 20/ngày

| Policy | Alerts | Reviewed | Overflow | Precision flagged | Recall reviewed | Net benefit |
|---|---:|---:|---:|---:|---:|---:|
| balanced_threshold | 884 | 595 | 289 | 12.33% | 31.19% | 24,295.57 |
| sensitive_threshold | 1,645 | 600 | 1,045 | 8.33% | 31.19% | 20,577.31 |
| strict_threshold | 411 | 408 | 3 | 18.73% | 26.10% | 16,126.93 |
| capacity_aware | 1,645 | 600 | 1,045 | 8.33% | 31.19% | 20,577.31 |
| cost_sensitive | 10,105 | 600 | 9,505 | 2.31% | 26.78% | 8,382.91 |

Nhận xét: Khi capacity thấp, `balanced_threshold` tốt hơn `sensitive_threshold` vì sensitive tạo quá nhiều overflow. Kết quả này cho thấy policy tối ưu phụ thuộc vào ràng buộc vận hành, không chỉ phụ thuộc vào model score.

## Sensitivity analysis

Script đã chạy các cost scenarios:

- `base_cost`
- `high_false_positive_cost`
- `high_analyst_cost`
- `low_recovery`
- `high_recovery`

Diễn giải:

- False positive cost cao làm các policy review nhiều bị giảm net benefit.
- Analyst cost cao làm workload trở thành ràng buộc quan trọng hơn.
- Fraud recovery rate thấp có thể làm một policy chuyển từ net benefit dương sang âm.
- Recovery rate cao làm các policy có recall cao có lợi thế hơn.

## Cách đưa vào báo cáo

Có thể viết:

> Kết quả policy comparison cho thấy cùng một risk scoring function có thể tạo ra hiệu quả kinh tế khác nhau tùy cơ chế ra quyết định phía sau. Policy nhạy hơn giúp tăng recall và net benefit khi analyst capacity đủ, nhưng khi capacity bị giới hạn, overflow tăng làm net benefit giảm. Policy nghiêm hơn giảm workload và false positive, nhưng bỏ sót nhiều fraud. Điều này cho thấy transaction risk decisioning nên được xem là bài toán thiết kế cơ chế dưới ràng buộc nguồn lực, thay vì chỉ là bài toán tối đa hóa accuracy của model.

## Hạn chế

- Risk score vẫn là synthetic scoring function, chưa phải model train/validate trên dữ liệu thật.
- Cost assumptions là giả định mô phỏng, chưa được hiệu chỉnh bằng dữ liệu vận hành thực tế.
- Cost-sensitive policy cần calibration thêm vì hiện tạo quá nhiều candidate.
- False positive cost/customer friction mới được mô hình hóa đơn giản.

## Bước tiếp theo

1. Tinh chỉnh cost-sensitive expected value.
2. Tìm threshold tối ưu theo net benefit thay vì chọn thủ công.
3. Vẽ trade-off curve giữa recall, false positive cost, analyst workload và net benefit.
