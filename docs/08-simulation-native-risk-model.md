# Simulation-native risk model

File này ghi lại bước nâng cấp sau prototype sensitivity analysis: tạo một model
chấm điểm rủi ro mới cho chính dữ liệu mô phỏng của đề án.

## Vì sao không dùng trực tiếp model cũ?

Model cũ của RiskGuard AI được huấn luyện trên schema và phân phối dữ liệu khác.
Nếu bê nguyên weight cũ sang dữ liệu mô phỏng mới, score có thể bị lệch vì
data/model mismatch. Trong đề án này, model cần học lại trên synthetic simulation
được thiết kế theo Agent-Based Modeling và Mechanism Design.

## Pipeline hiện tại

Script `scripts/train_simulation_risk_model.py` thực hiện các bước:

1. Lấy run mới nhất của các scenario: `low_fraud`, `baseline`,
   `stress_fraud`, `low_capacity`, `high_capacity`.
2. Ghép `transactions.csv` với `behavior_features.csv` theo `transaction_id`.
3. Tạo feature gồm amount, log amount, hour, velocity, amount anomaly,
   merchant risk, các thống kê hành vi 1h/24h/3d/7d/30d và one-hot category.
4. Chia train/test theo thời gian: các ngày cuối của mỗi scenario được giữ làm
   test set.
5. Train logistic regression bằng numpy với class weighting để xử lý fraud rate
   thấp.
6. Xuất `ml_risk_probability`, `ml_risk_score`, model metrics, coefficient và
   policy comparison.

## Metric cần đọc

- `ROC-AUC`: khả năng xếp hạng fraud cao hơn non-fraud.
- `PR-AUC / Average Precision`: phù hợp hơn khi fraud rất hiếm.
- `precision@top K`: trong nhóm giao dịch ưu tiên review, bao nhiêu phần là fraud.
- `recall@top K`: bắt được bao nhiêu fraud trong giới hạn review.
- `net benefit`: payoff sau khi tính fraud loss prevented, false positive cost,
  analyst cost và overflow penalty.

## Vai trò trong đề án

Model này không phải mục tiêu cuối cùng. Nó là một thành phần trong cơ chế:

`transaction -> behavior features -> model risk score -> policy -> analyst capacity -> outcome/KPI`

Điểm quan trọng là đánh giá model thông qua tác động lên policy và KPI nghiệp vụ,
không chỉ qua accuracy.


## XGBoost branch

Script `scripts/train_simulation_xgboost_model.py` là phiên bản model mạnh hơn
so với logistic regression baseline. Model này dùng `XGBClassifier`, xử lý mất
cân bằng bằng `scale_pos_weight`, giữ validation/test theo thời gian và báo cáo:

- ROC-AUC và PR-AUC trên train/valid/test.
- Precision/recall tại các nhóm top 0.5%, 1%, 3%, 5%, 10%.
- Threshold report trên validation.
- Policy comparison trên test set theo top percentile và probability threshold.
- Feature importance để giải thích model đang dựa vào tín hiệu nào.

Khi đọc kết quả, không nên chỉ nhìn PR-AUC. Với bài toán cơ chế ra quyết định,
cần xem thêm policy nào tạo net benefit cao nhất dưới analyst capacity và cost
assumptions đã đặt ra.
