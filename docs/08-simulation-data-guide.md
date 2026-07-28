# 08 - Simulation Data Guide

File này giải thích cách sinh dữ liệu mô phỏng cho đề án `Agent-Based Simulation and Mechanism Design for Transaction Risk Decisioning`.

## 1. Mục đích của dữ liệu mô phỏng

Dữ liệu mô phỏng không nhằm thay thế dữ liệu thật của ngân hàng/fintech. Mục tiêu là tạo một môi trường thử nghiệm có kiểm soát để trả lời các câu hỏi:

- Nếu fraud rate thay đổi thì workload của analyst thay đổi thế nào?
- Nếu threshold risk score thay đổi thì false positive cost và fraud loss thay đổi ra sao?
- Nếu analyst capacity bị giới hạn thì queue overflow ảnh hưởng thế nào đến hiệu quả kiểm soát rủi ro?
- Một cơ chế decisioning tốt nên cân bằng giữa fraud loss prevented, customer friction, analyst cost và false positive cost như thế nào?

## 2. Nguồn hiệu chỉnh phân phối

Script không copy dòng dữ liệu từ dataset công khai. Thay vào đó, dữ liệu mô phỏng được hiệu chỉnh từ profile tổng hợp của ba nguồn tham chiếu:

- ULB Credit Card Fraud Detection: fraud rate rất thấp, amount lệch phải, fraud không phải lúc nào cũng là giao dịch lớn.
- BankSim: có merchant category rõ, fraud tập trung ở một số nhóm merchant rủi ro hơn.
- PaySim: có fraud rate thấp và hành vi giao dịch tài chính số như transfer/cash-out/payment.

Các profile đã được lưu trong:

```text
data/reference/profiles/
```

## 3. Phương pháp mô phỏng

Phương pháp hiện tại là calibrated agent-based Monte Carlo simulation.

Các thành phần chính:

- Customer agent: mỗi khách hàng có segment, tần suất giao dịch/ngày, mức tiền điển hình, xu hướng giao dịch đêm và baseline risk riêng.
- Transaction generator: sinh giao dịch theo ngày, giờ, category, channel và amount.
- Fraud behavior generator: sinh một tỷ lệ fraud theo các chiến lược khác nhau như high amount, low amount probe, burst velocity, late hour, merchant abuse.
- Behavior feature builder: tính feature lịch sử trước giao dịch như txn_count_1h, txn_count_24h, tổng tiền/median/p95 trong 3/7/30 ngày, gap với giao dịch trước.
- Risk scoring system: chuyển các tín hiệu hành vi thành risk_probability và risk_score.
- Policy mechanism: quyết định allow, monitor, review_queue hoặc simulated_step_up_or_hold.
- Analyst process: mô phỏng review capacity, review outcome và review time.
- KPI evaluation: tính precision/recall của alert, fraud loss prevented, fraud loss realized, false positive cost, analyst cost và net benefit.

## 4. Cách chạy

Từ thư mục project:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\generate_simulation_data.py --customers 1000 --days 30 --seed 20260720 --fraud-rate 0.01 --analyst-capacity-per-day 100 --scenario-name baseline
```

Output mặc định nằm trong:

```text
data/simulation_runs/<scenario_name>_<timestamp>/
```

## 5. Các file output

- `customers.csv`: danh sách customer agent và đặc điểm hành vi nền.
- `transactions.csv`: giao dịch mô phỏng, gồm `is_fraud` là nhãn thật trong môi trường mô phỏng.
- `behavior_features.csv`: feature hành vi tính tại thời điểm trước giao dịch.
- `risk_scores.csv`: risk probability, risk score, risk level, top driver.
- `policy_decisions.csv`: quyết định của cơ chế policy.
- `analyst_reviews.csv`: kết quả analyst review mô phỏng.
- `outcomes.csv`: chi phí/lợi ích theo từng giao dịch.
- `simulation_metrics.csv`: KPI tổng hợp của toàn bộ scenario.
- `case_examples.json`: một số case rủi ro cao để dùng minh họa.

## 6. Baseline đã chạy

Baseline đầu tiên đã được tạo với cấu hình:

```text
customers = 1000
days = 30
fraud_rate = 0.01
analyst_capacity_per_day = 100
seed = 20260720
```

Kết quả tổng hợp:

```text
transactions = 28,563
fraud_count = 314
fraud_rate = 1.0993%
alerts_sent_to_analyst = 915
analyst_reviewed = 915
precision_flagged = 13.88%
recall_flagged = 40.45%
fraud_loss_prevented = 91,805.27
fraud_loss_realized = 20,062.84
false_positive_cost = 5,675.70
analyst_cost = 3,071.27
net_benefit = 62,995.46
```

## 7. Lưu ý khi viết báo cáo

Không nên trình bày đây là dữ liệu thật hoặc hệ thống fraud detection đã triển khai thực tế.

Cách nói đúng hơn:

> Dữ liệu được mô phỏng có hiệu chỉnh theo các đặc điểm phân phối quan sát từ các bộ dữ liệu công khai. Mục tiêu là tạo môi trường thử nghiệm để đánh giá cơ chế ra quyết định rủi ro, không phải khẳng định hiệu suất trên dữ liệu vận hành thực tế.

## 8. Bước tiếp theo

Sau khi có baseline, bước tiếp theo nên là chạy nhiều scenario để so sánh:

- low_fraud: fraud_rate = 0.0015
- baseline: fraud_rate = 0.01
- stress: fraud_rate = 0.03
- low_capacity: analyst_capacity_per_day = 50
- high_capacity: analyst_capacity_per_day = 200

Sau đó so sánh các KPI để tìm policy tốt hơn theo mục tiêu kinh doanh.
