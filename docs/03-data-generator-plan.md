# 03. Data Generator Plan: Synthetic Data for Transaction Risk Decision Simulation

## 1. Mục đích

File này mô tả cách sinh dữ liệu cho đề án theo hướng mô phỏng đa tác nhân và thiết kế cơ chế ra quyết định rủi ro giao dịch.

Mục tiêu không phải tạo một bộ dữ liệu giả để model đạt điểm cao, mà là tạo dữ liệu có logic hành vi, có cơ chế tương tác và có outcome sau quyết định.

Dữ liệu cần phục vụ 4 việc:

1. Mô phỏng hành vi giao dịch của khách hàng bình thường.
2. Mô phỏng hành vi của tác nhân gian lận/rủi ro.
3. Tạo risk score và evidence để hệ thống ra quyết định.
4. Đánh giá policy qua KPI nghiệp vụ như fraud loss, false positive cost, analyst workload và expected net benefit.

## 2. Nguyên tắc sinh dữ liệu

Dữ liệu phải đi từ bài toán đến mô phỏng, không đi ngược lại.

Thứ tự đúng:

1. Xác định câu hỏi nghiên cứu.
2. Xác định agent và hành vi.
3. Xác định policy/can thiệp.
4. Xác định KPI cuối cùng.
5. Sinh dữ liệu đủ để kiểm tra các KPI đó.

Điều cần tránh:

- Không sinh feature ngẫu nhiên chỉ để model phân loại tốt.
- Không để fraud label quá dễ đoán một cách phi thực tế.
- Không dùng dữ liệu nhạy cảm/thật nếu không có quyền.
- Không để mọi giao dịch rủi ro đều Critical.
- Không để policy chỉ là threshold cứng mà không có chi phí đi kèm.

## 3. Simulation inputs

Một lần chạy mô phỏng nên có các tham số đầu vào sau:

- simulation_run_id
- random_seed
- n_customers
- n_days
- avg_transactions_per_customer_per_day
- fraud_rate
- fraud_strategy_mix
- analyst_capacity_per_day
- policy_id
- use_ai_explanation
- threshold_low
- threshold_high
- cost_per_false_positive
- cost_per_review
- cost_per_ai_call
- customer_friction_cost
- fraud_loss_multiplier

Ví dụ config MVP:

- n_customers = 500
- n_days = 30
- avg_transactions_per_customer_per_day = 0.8
- fraud_rate = 2 percent
- analyst_capacity_per_day = 80 cases
- policy_id = ML_PLUS_ANALYST_AI

## 4. Synthetic customer profiles

### 4.1. Customer segments

Nên chia khách hàng thành 3 nhóm:

1. Low value customer
   - Amount trung bình thấp.
   - Tần suất giao dịch thấp.
   - Ít giao dịch ban đêm.

2. Medium value customer
   - Amount trung bình vừa.
   - Tần suất đều.
   - Hành vi ổn định.

3. High value customer
   - Amount trung bình cao.
   - Có thể giao dịch nhiều hơn.
   - Dễ bị false positive nếu policy chỉ dựa vào amount.

### 4.2. Bảng customers.csv

Các cột đề xuất:

- customer_id
- segment
- normal_amount_mean
- normal_amount_std
- transaction_frequency
- active_hour_start
- active_hour_end
- night_activity_prob
- preferred_mcc_group
- friction_tolerance
- baseline_risk

### 4.3. Logic sinh customer

Gợi ý:

- 60 percent low value.
- 30 percent medium value.
- 10 percent high value.

Mỗi segment có phân phối amount riêng. Ví dụ:

Low value:

- normal_amount_mean khoảng 20-80
- transaction_frequency thấp

Medium value:

- normal_amount_mean khoảng 80-250
- transaction_frequency vừa

High value:

- normal_amount_mean khoảng 250-800
- transaction_frequency cao hơn

Điểm quan trọng:

High value customer không nên tự động bị coi là fraud. Nếu không, mô phỏng sẽ tạo bias và false positive cao không thực tế.

## 5. Normal transaction generation

### 5.1. Bảng transactions.csv

Các cột đề xuất:

- transaction_id
- customer_id
- timestamp
- amount
- currency
- merchant_id
- merchant_category
- merchant_risk_level
- channel
- device_trust_level
- is_fraud_true
- fraud_strategy

### 5.2. Logic sinh giao dịch bình thường

Với mỗi customer và mỗi ngày:

1. Sinh số giao dịch bằng Poisson distribution.
2. Sinh amount dựa trên profile khách hàng.
3. Sinh hour dựa trên active hour và night_activity_prob.
4. Sinh merchant category theo preferred_mcc_group.
5. Gán device/channel thông thường.

Gợi ý phân phối:

- Số giao dịch/ngày: Poisson(lambda theo segment).
- Amount: log-normal để tránh amount âm và tạo đuôi phải tự nhiên.
- Hour: categorical distribution, tập trung vào giờ hoạt động chính.

## 6. Fraud transaction generation

### 6.1. Fraud strategies

Nên có 5 nhóm fraud/risk behavior:

1. High amount attack
   - Amount cao hơn nhiều so với profile.
   - Tạo amount_anomaly_signal cao.

2. Burst velocity attack
   - Nhiều giao dịch trong 1h hoặc 24h.
   - Tạo txn_count_1h và txn_count_24h cao.

3. Late-hour attack
   - Giao dịch vào giờ khách hàng ít hoạt động.
   - Tạo timing anomaly.

4. Merchant/category abuse
   - Merchant risk cao hoặc MCC bất thường.
   - Tạo merchant risk signal.

5. Mixed attack
   - Kết hợp amount, timing và velocity.
   - Thường có risk score cao nhất.

### 6.2. Fraud adaptation

Để đúng tinh thần agent-based simulation, có thể thêm phiên bản nâng cao:

Nếu policy bắt được quá nhiều high amount attack, fraud actor sẽ giảm amount nhưng tăng số lượng giao dịch nhỏ hơn.

Ví dụ:

- Giai đoạn 1: fraud chủ yếu high_amount.
- Giai đoạn 2: khi threshold amount cao được áp dụng, fraud chuyển sang burst_velocity với amount nhỏ hơn.

Điều này giúp mô phỏng có phản ứng, không phải dữ liệu tĩnh.

## 7. Behavior feature engineering

Sau khi có transactions, cần tính behavior features theo từng customer tại thời điểm giao dịch.

### 7.1. Windows

Các window nên có:

- last_1_day
- last_3_days
- last_7_days
- last_30_days

### 7.2. Features

Các feature đề xuất:

- txn_count_1h
- txn_count_24h
- txn_count_3d
- txn_count_7d
- txn_count_30d
- amount_sum_1d
- amount_sum_3d
- amount_sum_7d
- amount_sum_30d
- amount_avg_7d
- amount_median_7d
- amount_p95_7d
- amount_avg_30d
- amount_median_30d
- amount_p95_30d
- max_amount_7d
- max_amount_30d
- night_transaction_share_7d
- common_transaction_hours_7d
- gap_since_previous_transaction_minutes
- amount_anomaly_signal

### 7.3. Amount anomaly signal

Gợi ý công thức đơn giản:

amount_anomaly_signal = max(0, current_amount - median_30d) / max(p95_30d - median_30d, small_constant)

Sau đó clip về khoảng 0 đến 1.

Ý nghĩa:

- 0: amount không bất thường.
- 1: amount rất cao so với lịch sử gần đây.

### 7.4. Timing signal

Gợi ý:

late_hour_signal = 1 nếu hour nằm trong khoảng 22h-5h, ngược lại 0.

Có thể nâng cấp:

unusual_hour_signal = 1 nếu hour không nằm trong top common hours của customer trong 30 ngày.

## 8. Risk scoring proxy

Ở giai đoạn đầu, chưa cần huấn luyện ML model thật. Có thể dùng scoring proxy để phục vụ mô phỏng policy.

Ví dụ:

risk_score_raw =
  35 * amount_anomaly_signal
+ 20 * normalized_txn_count_1h
+ 15 * normalized_txn_count_24h
+ 10 * late_hour_signal
+ 10 * merchant_risk_signal
+ 10 * device_risk_signal
+ random_noise

risk_score = clip(risk_score_raw, 0, 100)

Risk level:

- 0-39: Low
- 40-69: Medium
- 70-84: High
- 85-100: Critical

Top drivers:

Chọn 3 feature có contribution lớn nhất trong công thức score.

## 9. Policy simulation

### 9.1. Policy A: Rule-Based Only

Rule ví dụ:

- Review nếu amount > fixed_amount_threshold.
- Review nếu txn_count_24h > threshold.
- Review nếu merchant_risk_level = high.

### 9.2. Policy B: Score Threshold

Rule ví dụ:

- risk_score < 50: approve
- 50 <= risk_score < 85: review
- risk_score >= 85: high priority review

### 9.3. Policy C: Score + Analyst Capacity

Nếu analyst capacity giới hạn, chỉ review top N case theo risk_score mỗi ngày.

Các case vượt capacity tạo backlog hoặc được xử lý theo rule fallback.

### 9.4. Policy D: Score + Analyst + AI Explanation

Giống Policy C nhưng:

- review_time giảm khi có AI explanation.
- analyst accuracy có thể tăng nhẹ.
- phát sinh AI usage cost.

## 10. Analyst review simulation

### 10.1. Review time

Base review time có thể phụ thuộc vào risk level:

- Medium: 6 phút
- High: 9 phút
- Critical: 12 phút

Nếu có AI explanation:

review_time = base_review_time * 0.7

### 10.2. Analyst accuracy

Gợi ý:

- accuracy_without_ai = 0.85
- accuracy_with_ai = 0.90

Có thể làm accuracy giảm nếu backlog quá cao:

Nếu backlog lớn hơn capacity, fatigue_factor làm accuracy giảm nhẹ.

## 11. Outcome generation

Outcome không chỉ là fraud label, mà là kết quả sau policy.

Các trạng thái:

- legitimate_approved
- legitimate_reviewed
- legitimate_blocked_simulated
- fraud_caught
- fraud_missed
- fraud_reviewed_but_wrong_decision

Bảng outcome nên lưu:

- transaction_id
- policy_id
- true_label
- action
- analyst_decision
- outcome_type
- cost
- benefit

## 12. KPI calculation

### 12.1. Fraud loss prevented

Tổng amount của fraud transaction được bắt đúng.

### 12.2. Fraud loss missed

Tổng amount của fraud transaction bị approve nhầm.

### 12.3. False positive cost

Số legitimate transactions bị review/block nhầm nhân với chi phí tương ứng.

### 12.4. Analyst review cost

Số phút review * cost_per_minute hoặc số case review * cost_per_case.

### 12.5. Customer friction cost

Chi phí từ việc khách hàng tốt bị review/block/step-up quá nhiều.

### 12.6. AI usage cost

Số AI calls * cost_per_call.

### 12.7. Expected net benefit

Expected Net Benefit = Fraud Loss Prevented - Fraud Loss Missed - False Positive Cost - Analyst Review Cost - Customer Friction Cost - AI Usage Cost

## 13. Output files từ data generator

Một lần chạy generator nên tạo folder:

simulation_runs/run_YYYYMMDD_HHMMSS/

Bên trong có:

- config.json
- customers.csv
- transactions.csv
- behavior_features.csv
- risk_scores.csv
- policy_decisions.csv
- analyst_reviews.csv
- outcomes.csv
- simulation_metrics.csv
- case_examples.json

## 14. Case examples cho AI Agent

Để dùng lại khung AI agent, mỗi run nên xuất một số case examples:

- case_id
- transaction_id
- customer_profile_summary
- transaction_summary
- recent_behavior_summary
- risk_score
- risk_level
- top_risk_drivers
- policy_action
- analyst_context
- allowed_evidence

AI Agent chỉ được trả lời dựa trên allowed_evidence.

## 15. Các kiểm tra bắt buộc

Trước khi dùng data để demo hoặc viết báo cáo, cần kiểm tra:

1. Fraud rate đúng với config.
2. Risk score phân bố đủ Low/Medium/High/Critical.
3. Policy threshold thay đổi làm review rate thay đổi hợp lý.
4. Policy quá chặt làm false positive cost tăng.
5. Policy quá lỏng làm fraud loss missed tăng.
6. AI explanation làm review time giảm nhưng có thêm AI cost.
7. Expected net benefit không được luôn tăng một chiều vô lý.

## 16. Kế hoạch code bước đầu

Script đầu tiên nên là:

scripts/generate_simulation_data.py

Chức năng:

1. Đọc config.
2. Sinh customers.
3. Sinh transactions.
4. Tính behavior features.
5. Tính risk scores.
6. Chạy policy decisions.
7. Mô phỏng analyst review.
8. Tính KPI.
9. Xuất CSV/JSON.

Sau đó mới tích hợp vào backend/frontend.

## 17. Kết luận

Data generator là trung tâm của đề án. Nếu generator được thiết kế đúng, dữ liệu mô phỏng sẽ có ý nghĩa nghiên cứu: nó cho phép so sánh policy, đo chi phí cơ hội và kiểm tra cơ chế ra quyết định dưới nhiều kịch bản khác nhau.
