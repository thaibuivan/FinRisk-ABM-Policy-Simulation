# 02. Simulation Design: Agent-Based Transaction Risk Decisioning

## 1. Mục đích của file này

File này mô tả thiết kế mô phỏng cho đề án cá nhân theo hướng:

Agent-Based Simulation and Mechanism Design for Transaction Risk Decisioning in Digital Finance.

Nếu file 01 trả lời câu hỏi "vì sao đề tài này đáng làm và nền tảng lý thuyết là gì", thì file 02 trả lời câu hỏi:

- Mô phỏng những tác nhân nào?
- Mỗi tác nhân có hành vi và lợi ích gì?
- Dữ liệu được sinh ra theo cơ chế nào?
- Chính sách ra quyết định được so sánh như thế nào?
- KPI nào được dùng để đánh giá hiệu quả cuối cùng?

File này là bản thiết kế trước khi code. Mục tiêu là bảo đảm dữ liệu mô phỏng không bị tạo ngẫu nhiên cho đẹp model, mà được sinh ra từ một cơ chế có logic kinh tế, vận hành và rủi ro.

## 2. Tư duy thiết kế mô phỏng

Trong một hệ thống giao dịch số, rủi ro không chỉ đến từ từng giao dịch riêng lẻ. Rủi ro xuất hiện từ tương tác giữa nhiều bên:

- Khách hàng bình thường tạo giao dịch hợp lệ.
- Tác nhân gian lận tìm cách tạo giao dịch bất thường và tránh bị phát hiện.
- Hệ thống risk scoring đưa ra điểm rủi ro.
- Policy quyết định giao dịch nào được approve, review hoặc block.
- Analyst xử lý case theo năng lực giới hạn.
- Ngân hàng/fintech platform chịu chi phí từ fraud loss, false positive, customer friction và vận hành.

Do đó, mô phỏng cần đi theo chuỗi:

Customer/Fraud Actor -> Transaction -> Risk Score -> Policy Decision -> Analyst Review -> Outcome -> KPI.

Điểm quan trọng: outcome cuối cùng không nằm sẵn trong bảng dữ liệu ban đầu, mà xuất hiện sau khi hệ thống ra quyết định và các tác nhân tương tác với nhau.

## 3. Phạm vi mô phỏng MVP

Phiên bản đầu tiên không cần mô phỏng toàn bộ hệ thống ngân hàng. MVP nên tập trung vào một quy trình nhỏ nhưng đủ ý nghĩa:

Một nền tảng fintech xử lý luồng giao dịch trong ngày. Mỗi giao dịch được chấm điểm rủi ro. Tùy theo policy, giao dịch có thể được approve ngay, đưa vào hàng đợi analyst review, hoặc block/escalate. Sau đó hệ thống đo lường tổn thất gian lận, chi phí xử lý, chi phí block nhầm và workload của analyst.

Phạm vi MVP:

- Một tập khách hàng mô phỏng.
- Một tập giao dịch theo thời gian.
- Một nhóm fraud actor với hành vi khác khách hàng bình thường.
- Một risk scoring model đơn giản hoặc proxy score.
- Ba đến bốn policy để so sánh.
- Một analyst pool có giới hạn năng lực xử lý.
- Một bộ KPI nghiệp vụ.

Chưa cần ở MVP:

- Mô phỏng mạng lưới thiết bị/IP quá phức tạp.
- Huấn luyện model fraud detection tối ưu.
- Tự động block thật.
- Dữ liệu PII thật.
- Kết nối realtime production.

## 4. Các tác nhân trong mô phỏng

### 4.1. Normal Customer Agent

Vai trò:

Đại diện cho khách hàng hợp lệ, tạo giao dịch theo hành vi thông thường.

Thuộc tính chính:

- customer_id
- segment: low_value, medium_value, high_value
- normal_amount_mean
- normal_amount_std
- active_hours
- merchant_preference
- transaction_frequency
- friction_tolerance

Hành vi:

- Sinh giao dịch theo phân phối số tiền và giờ hoạt động quen thuộc.
- Có xác suất nhỏ tạo giao dịch bất thường nhưng vẫn hợp lệ.
- Nếu bị review/block nhầm, tạo customer friction cost.

Ý nghĩa mô phỏng:

Normal customer giúp đo false positive cost. Nếu policy quá chặt, nhiều giao dịch hợp lệ bị review/block, làm tăng chi phí và giảm trải nghiệm.

### 4.2. Fraud Actor Agent

Vai trò:

Đại diện cho hành vi gian lận hoặc giao dịch rủi ro cao.

Thuộc tính chính:

- fraud_strategy: high_amount, burst_velocity, late_hour, merchant_abuse, mixed
- attack_intensity
- evasion_level
- adaptation_speed
- target_customer_segment

Hành vi:

- Tạo giao dịch có amount cao hơn hành vi bình thường.
- Có thể tạo nhiều giao dịch trong thời gian ngắn.
- Có xu hướng xuất hiện ở giờ bất thường hoặc merchant rủi ro.
- Nếu policy quá dễ đoán, fraud actor có thể giảm amount hoặc giãn khoảng cách giao dịch để né rule.

Ý nghĩa mô phỏng:

Fraud actor giúp kiểm tra khả năng policy phát hiện rủi ro và chi phí khi bỏ sót fraud.

### 4.3. Risk Scoring System Agent

Vai trò:

Đại diện cho rule/model tạo risk score cho từng giao dịch.

Input:

- amount
- amount_anomaly_signal
- transaction_hour
- txn_count_1h
- txn_count_24h
- gap_since_previous_transaction
- merchant_risk_level
- customer_recent_behavior

Output:

- risk_score từ 0 đến 100
- risk_level: Low, Medium, High, Critical
- top_risk_drivers
- explanation_evidence

Ở MVP, risk score có thể được tạo theo công thức rule-based/proxy thay vì cần model ML hoàn chỉnh. Sau đó mới có thể thay bằng model thật.

Ví dụ công thức proxy:

risk_score = base_score
           + amount_weight * amount_anomaly_signal
           + velocity_weight * normalized_velocity
           + time_weight * late_hour_signal
           + merchant_weight * merchant_risk_signal
           + fraud_prior_weight * customer_or_segment_risk

Score được cắt trong khoảng 0 đến 100.

### 4.4. Policy Maker Agent

Vai trò:

Đại diện cho cơ chế ra quyết định của tổ chức.

Input:

- risk_score
- risk_level
- analyst_capacity
- current_backlog
- business objective

Action:

- approve
- review
- step_up_authentication
- block/escalate trong mô phỏng

Lưu ý:

Trong sản phẩm và báo cáo, block/escalate chỉ là hành động mô phỏng policy, không phải hành động thực thi thật lên khách hàng.

### 4.5. Analyst Agent

Vai trò:

Đại diện cho người xử lý case.

Thuộc tính:

- review_capacity_per_day
- base_review_time
- accuracy_without_ai
- accuracy_with_ai
- fatigue_factor

Hành vi:

- Nhận case từ queue theo policy ưu tiên.
- Review case nếu còn capacity.
- Nếu có AI explanation/report, review time có thể giảm.
- Có xác suất ra quyết định sai tùy theo độ khó case và có/không có AI support.

Ý nghĩa:

Analyst agent cho phép đo workload, backlog, review time và lợi ích vận hành của AI assistant.

### 4.6. Platform/Bank Agent

Vai trò:

Đại diện cho tổ chức chịu chi phí và lợi ích cuối cùng.

Mục tiêu:

Tối đa hóa expected net benefit, không chỉ tối đa hóa detection rate.

Các chi phí/lợi ích:

- fraud loss nếu bỏ sót gian lận
- fraud loss prevented nếu phát hiện đúng
- false positive cost nếu review/block nhầm giao dịch hợp lệ
- analyst review cost
- customer friction cost
- AI usage cost
- operational benefit từ giảm review time

## 5. Luồng mô phỏng chi tiết

### Step 1. Khởi tạo môi trường

Thiết lập các tham số:

- number_of_customers
- simulation_days
- transactions_per_day
- fraud_rate
- analyst_capacity_per_day
- policy_type
- use_ai_explanation
- fraud_adaptation_enabled

### Step 2. Sinh customer profiles

Mỗi customer có profile riêng:

- segment
- amount distribution
- active hours
- merchant categories
- baseline velocity

Ví dụ:

- Low value customer: amount thường nhỏ, giao dịch ít.
- Medium value customer: amount vừa, giao dịch đều.
- High value customer: amount lớn hơn, dễ bị false positive nếu policy chỉ nhìn amount.

### Step 3. Sinh giao dịch bình thường

Với mỗi customer và mỗi ngày:

- Sinh số lượng giao dịch theo Poisson hoặc phân phối đơn giản.
- Sinh amount theo log-normal hoặc normal clipped.
- Sinh transaction hour theo active_hours.
- Sinh merchant category theo preference.

### Step 4. Sinh giao dịch gian lận

Chọn một phần giao dịch hoặc customer bị fraud actor tấn công.

Fraud strategies:

1. High amount attack
   - Amount cao bất thường so với profile.

2. Burst velocity attack
   - Nhiều giao dịch trong thời gian ngắn.

3. Late-hour attack
   - Giao dịch vào giờ ít gặp.

4. Merchant abuse attack
   - Merchant/category có rủi ro cao.

5. Mixed attack
   - Kết hợp nhiều tín hiệu.

### Step 5. Tính behavior features

Từ lịch sử giao dịch, tính các feature:

- txn_count_1h
- txn_count_24h
- amount_avg_7d
- amount_median_7d
- amount_p95_7d
- amount_avg_30d
- amount_median_30d
- amount_p95_30d
- night_transaction_share
- gap_since_previous_transaction
- amount_anomaly_signal

Đây là phần giúp hệ thống không chỉ nhìn giao dịch hiện tại mà còn so với hành vi gần đây của khách hàng.

### Step 6. Risk scoring

Risk scoring system tạo:

- risk_score
- risk_level
- top_risk_drivers
- model_evidence

Ví dụ risk drivers:

- amount_anomaly
- transaction_timing
- short_term_velocity
- merchant_risk
- behavior_deviation

### Step 7. Policy decision

Mỗi policy đưa ra action khác nhau.

Ví dụ:

- score < 50: approve
- 50 <= score < 80: review
- score >= 80: high priority review hoặc simulated block/escalate

Nếu analyst backlog quá cao, policy có thể chỉ review top priority cases.

### Step 8. Analyst review

Nếu giao dịch vào review queue:

- Analyst xử lý nếu còn capacity.
- Nếu có AI explanation, review_time giảm theo hệ số.
- Analyst decision có thể đúng/sai theo xác suất.

Ví dụ:

review_time_with_ai = base_review_time * 0.7

accuracy_with_ai = accuracy_without_ai + support_gain

### Step 9. Outcome và KPI

Sau khi policy/analyst quyết định, hệ thống xác định:

- fraud caught
- fraud missed
- legitimate approved
- legitimate falsely reviewed/blocked
- analyst time used
- backlog generated
- cost and benefit

## 6. Các policy so sánh trong MVP

### Policy A. Rule-Based Only

Cơ chế:

- Review nếu amount vượt ngưỡng.
- Review nếu txn_count_24h vượt ngưỡng.
- Review nếu merchant risk cao.

Ưu điểm:

- Dễ hiểu.
- Dễ triển khai.

Nhược điểm:

- Dễ false positive.
- Khó thích nghi với hành vi fraud mới.

### Policy B. ML Score Threshold

Cơ chế:

- Dùng risk_score để quyết định.
- Review hoặc escalate case có score cao.

Ưu điểm:

- Tổng hợp nhiều tín hiệu.
- Linh hoạt hơn rule đơn giản.

Nhược điểm:

- Nếu không giải thích được, analyst khó tin tưởng.
- Threshold sai có thể làm workload tăng mạnh.

### Policy C. ML + Analyst Review

Cơ chế:

- ML tạo risk score và priority.
- Analyst review case trước khi ra quyết định cuối.

Ưu điểm:

- Human-in-the-loop.
- Giảm rủi ro quyết định tự động sai.

Nhược điểm:

- Tốn thời gian analyst.
- Có backlog nếu volume cao.

### Policy D. ML + Analyst Review + AI Explanation

Cơ chế:

- ML tạo score.
- AI agent giải thích evidence, top drivers, behavior history và report.
- Analyst dùng explanation để review nhanh hơn.

Ưu điểm:

- Tăng khả năng hiểu case.
- Giảm review time.
- Tạo audit trail tốt hơn.

Nhược điểm:

- Có chi phí LLM.
- Cần guardrails để tránh hallucination, PII leakage và quyết định vượt quyền.

## 7. KPI và công thức đánh giá

### 7.1. Confusion matrix metrics

- True Positive: fraud được phát hiện đúng.
- False Positive: giao dịch hợp lệ bị review/block nhầm.
- True Negative: giao dịch hợp lệ được approve đúng.
- False Negative: fraud bị bỏ sót.

Metrics:

Precision = TP / (TP + FP)

Recall = TP / (TP + FN)

F1 = 2 * Precision * Recall / (Precision + Recall)

### 7.2. Business cost metrics

Fraud Loss Prevented:

Tổng amount của fraud transactions được phát hiện đúng.

Fraud Loss Missed:

Tổng amount của fraud transactions bị bỏ sót.

False Positive Cost:

Số giao dịch hợp lệ bị review/block nhầm * cost_per_false_positive.

Analyst Review Cost:

Số case được review * cost_per_review.

Customer Friction Cost:

Số khách hàng/giao dịch hợp lệ bị ảnh hưởng * friction_cost.

AI Usage Cost:

Số câu hỏi/report AI * cost_per_ai_call.

Expected Net Benefit:

Fraud Loss Prevented - Fraud Loss Missed - False Positive Cost - Analyst Review Cost - Customer Friction Cost - AI Usage Cost

Có thể dùng phiên bản đơn giản hơn:

Expected Net Benefit = Fraud Loss Prevented - Total Operating Cost - False Positive Cost - Fraud Loss Missed

### 7.3. Operational metrics

- analyst_workload: số case cần review.
- review_time_avg: thời gian review trung bình.
- backlog_end_of_day: số case chưa xử lý cuối ngày.
- escalation_rate: tỷ lệ case high priority.
- throughput: số case analyst xử lý được mỗi ngày.

### 7.4. AI assistant metrics

- groundedness_rate: tỷ lệ câu trả lời chỉ dùng evidence có sẵn.
- pii_refusal_rate: tỷ lệ từ chối đúng với câu hỏi PII.
- out_of_scope_refusal_rate: tỷ lệ từ chối đúng câu hỏi ngoài phạm vi.
- natural_language_quality: câu trả lời tự nhiên, không JSON cứng, không markdown lỗi.
- average_latency.
- average_cost_per_case.

## 8. Data schema dự kiến

### 8.1. customers.csv

Các cột:

- customer_id
- segment
- normal_amount_mean
- normal_amount_std
- transaction_frequency
- active_hour_start
- active_hour_end
- friction_tolerance

### 8.2. transactions.csv

Các cột:

- transaction_id
- customer_id
- timestamp
- amount
- merchant_category
- merchant_risk_level
- is_fraud_true
- fraud_strategy
- transaction_channel

### 8.3. behavior_features.csv

Các cột:

- transaction_id
- txn_count_1h
- txn_count_24h
- amount_avg_7d
- amount_median_7d
- amount_p95_7d
- amount_avg_30d
- amount_median_30d
- amount_p95_30d
- night_transaction_share
- gap_since_previous_transaction
- amount_anomaly_signal

### 8.4. risk_scores.csv

Các cột:

- transaction_id
- risk_score
- risk_level
- top_driver_1
- top_driver_2
- top_driver_3
- score_reason

### 8.5. policy_decisions.csv

Các cột:

- transaction_id
- policy_id
- action
- priority
- routed_to_analyst
- decision_reason

### 8.6. analyst_reviews.csv

Các cột:

- case_id
- transaction_id
- analyst_id
- review_started_at
- review_completed_at
- used_ai_explanation
- analyst_decision
- decision_correct
- review_time_minutes

### 8.7. simulation_metrics.csv

Các cột:

- simulation_run_id
- policy_id
- fraud_rate
- transaction_volume
- analyst_capacity
- precision
- recall
- false_positive_rate
- false_negative_rate
- fraud_loss_prevented
- fraud_loss_missed
- false_positive_cost
- analyst_review_cost
- customer_friction_cost
- ai_usage_cost
- expected_net_benefit
- average_review_time
- backlog_end_of_day

## 9. Kịch bản thử nghiệm đầu tiên

MVP nên bắt đầu với 4 kịch bản:

### Scenario 1. Low Fraud, Normal Volume

- fraud_rate thấp
- transaction volume vừa
- analyst capacity đủ

Mục tiêu:

Kiểm tra policy nào ít gây false positive và customer friction nhất.

### Scenario 2. High Fraud, Normal Volume

- fraud_rate cao hơn
- transaction volume vừa
- analyst capacity đủ

Mục tiêu:

Kiểm tra policy nào bắt được fraud tốt hơn.

### Scenario 3. Low Fraud, High Volume

- fraud_rate thấp
- transaction volume cao
- analyst capacity giới hạn

Mục tiêu:

Kiểm tra backlog và workload.

### Scenario 4. Adaptive Fraud Actor

- fraud actor thay đổi strategy sau khi policy bắt đầu phát hiện tốt

Mục tiêu:

Kiểm tra độ bền của policy khi đối tượng rủi ro phản ứng lại cơ chế.

## 10. Quy tắc kiểm tra chất lượng mô phỏng

Để mô phỏng đáng tin hơn, cần kiểm tra:

1. Distribution check
   - Amount, hour, velocity có hợp lý không?

2. Label balance check
   - Fraud rate có đúng tham số đặt ra không?

3. Policy sanity check
   - Threshold cao hơn có làm số case review giảm không?
   - Fraud rate cao hơn có làm fraud loss tăng không?

4. KPI consistency check
   - Nếu AI giảm review time, workload xử lý được phải tăng hoặc backlog giảm.
   - Nếu threshold quá thấp, false positive cost phải tăng.
   - Nếu threshold quá cao, fraud loss missed phải tăng.

5. Explainability check
   - Top drivers phải khớp với feature thật.
   - Không được tạo evidence không tồn tại trong dữ liệu.

## 11. Output mong muốn của MVP mô phỏng

Sau khi chạy một simulation run, hệ thống nên xuất ra:

1. Summary table theo policy.
2. Confusion matrix theo policy.
3. Business KPI table.
4. Operational KPI table.
5. Biểu đồ so sánh expected net benefit.
6. Biểu đồ fraud loss vs false positive cost.
7. Case examples để AI agent giải thích.
8. Report mô phỏng: policy nào tốt hơn và vì sao.

## 12. Liên hệ với sản phẩm cá nhân

Khung code cũ có thể được dùng lại ở mức kỹ thuật:

- FastAPI backend để phục vụ API simulation.
- Frontend dashboard để hiển thị KPI và case examples.
- AI agent để giải thích case/policy dựa trên evidence.
- Report panel để sinh báo cáo sau simulation.

Nhưng cần đổi domain wording:

- RiskGuard AI -> tên sản phẩm cá nhân mới.
- Fraud detection product -> transaction risk decision simulation platform.
- Case review -> simulated risk decision case.
- Demo realtime fraud stream -> simulated transaction stream.

## 13. Việc cần làm tiếp theo

Bước tiếp theo sau file này:

1. Tạo file 03-data-generator-plan.md để mô tả chi tiết cách sinh dữ liệu.
2. Viết notebook hoặc script Python sinh sample data nhỏ.
3. Tính thử KPI cho 2 policy đầu tiên: rule-based only và ML score threshold.
4. Sau đó mới chỉnh backend/frontend theo schema mới.

## 14. Kết luận

Thiết kế mô phỏng này giúp đề án tránh lỗi chỉ tạo synthetic data để model chạy tốt. Thay vào đó, dữ liệu được sinh từ một cơ chế gồm nhiều tác nhân, nhiều hành động và nhiều chi phí. Đây là điểm nối giữa Game Theory, Mechanism Design, Agent-Based Modeling và sản phẩm AI trong FinTech.
