# 09 - Scenario Comparison Notes

File này ghi lại kết quả so sánh các kịch bản mô phỏng đầu tiên. Mục tiêu là chuyển dữ liệu mô phỏng thành phân tích chính sách/risk decisioning.

## 1. File kết quả chính

Bảng so sánh scenario mới nhất nằm tại:

```text
data/scenario_comparisons/scenario_comparison_20260721_100604.csv
data/scenario_comparisons/scenario_comparison_20260721_100604.md
```

Các simulation run tương ứng nằm trong:

```text
data/simulation_runs/
```

## 2. Các scenario đã chạy

### low_fraud

Mô phỏng môi trường fraud rất thấp, gần các bộ dữ liệu có tỷ lệ gian lận hiếm.

Ý nghĩa: kiểm tra xem cơ chế review có còn đáng làm khi fraud quá hiếm không.

### baseline

Mô phỏng môi trường tham chiếu với fraud rate khoảng 1% và analyst capacity 100 case/ngày.

Ý nghĩa: dùng làm mốc để so sánh.

### stress_fraud

Mô phỏng môi trường fraud pressure cao hơn, khoảng 3%.

Ý nghĩa: kiểm tra cơ chế ra quyết định khi rủi ro tăng mạnh.

### low_capacity

Dùng cùng môi trường giao dịch với baseline, nhưng analyst capacity giảm xuống 20 case/ngày.

Ý nghĩa: kiểm tra tác động của giới hạn nguồn lực analyst.

### high_capacity

Dùng cùng môi trường giao dịch với baseline, nhưng analyst capacity tăng lên 200 case/ngày.

Ý nghĩa: kiểm tra liệu tăng capacity có tạo thêm lợi ích hay không.

## 3. Kết quả tổng hợp

| Scenario | Fraud rate | Precision | Recall | Review overflow | Net benefit |
|---|---:|---:|---:|---:|---:|
| low_fraud | 0.1676% | 2.08% | 38.30% | 0 | -1,147.00 |
| baseline | 1.0642% | 12.33% | 36.95% | 0 | 52,233.60 |
| stress_fraud | 3.0247% | 30.09% | 36.06% | 0 | 185,799.53 |
| low_capacity | 1.0642% | 12.33% | 36.95% | 289 | 24,004.96 |
| high_capacity | 1.0642% | 12.33% | 36.95% | 0 | 52,233.60 |

## 4. Nhận xét ban đầu

### Nhận xét 1: Fraud hiếm làm false positive trở thành vấn đề lớn

Trong kịch bản `low_fraud`, net benefit âm dù hệ thống vẫn phát hiện một phần fraud. Lý do là fraud quá hiếm, nên nhiều alert gửi cho analyst là false positive. Chi phí review và customer friction có thể vượt lợi ích từ fraud loss prevented.

Ý nghĩa nghiên cứu: mô hình có recall không thấp chưa chắc tạo giá trị nghiệp vụ nếu base rate fraud quá thấp.

### Nhận xét 2: Khi fraud pressure tăng, cùng một policy tạo lợi ích cao hơn

Trong `stress_fraud`, precision tăng lên 30.09% và net benefit tăng mạnh. Khi môi trường có nhiều fraud hơn, mỗi alert có xác suất hữu ích cao hơn, nên chi phí review dễ được bù đắp.

Ý nghĩa nghiên cứu: policy threshold không nên cố định trong mọi trạng thái thị trường/rủi ro; nên có cơ chế thích ứng theo fraud pressure.

### Nhận xét 3: Analyst capacity là một ràng buộc quan trọng

`low_capacity` dùng cùng dữ liệu với baseline nhưng capacity giảm xuống 20 case/ngày. Kết quả có 289 case bị overflow và net benefit giảm từ 52,233.60 xuống 24,004.96.

Ý nghĩa nghiên cứu: hệ thống risk decisioning không thể chỉ tối ưu model score; phải tính cả năng lực xử lý của analyst.

### Nhận xét 4: Tăng capacity quá ngưỡng không tạo thêm lợi ích

`high_capacity` giống baseline vì baseline đã không bị overflow. Tăng capacity từ 100 lên 200 không cải thiện net benefit trong cùng môi trường.

Ý nghĩa nghiên cứu: bài toán không chỉ là tăng nhân sự, mà là thiết kế ngưỡng, hàng đợi và ưu tiên review hợp lý.

## 5. Cách đưa vào báo cáo

Có thể viết theo hướng:

> Kết quả mô phỏng cho thấy giá trị của hệ thống không chỉ phụ thuộc vào độ chính xác của mô hình phát hiện rủi ro, mà còn phụ thuộc vào fraud base rate, chi phí false positive và năng lực xử lý của analyst. Trong kịch bản fraud thấp, cơ chế review tạo net benefit âm do chi phí false positive lớn hơn lợi ích ngăn chặn fraud. Ngược lại, khi fraud pressure tăng, cùng một cơ chế tạo lợi ích ròng cao hơn. Khi analyst capacity bị giới hạn, review overflow làm giảm đáng kể net benefit. Điều này ủng hộ hướng tiếp cận mechanism design: thiết kế policy không chỉ để tối đa hóa model recall, mà để cân bằng fraud loss, customer friction và operational workload.

## 6. Bước tiếp theo

Các kết quả hiện tại mới so sánh cùng một policy dưới nhiều trạng thái môi trường. Bước tiếp theo nên là so sánh nhiều policy khác nhau:

- threshold thấp: review nhiều hơn, recall cao hơn nhưng false positive cost lớn hơn.
- threshold cao: review ít hơn, precision cao hơn nhưng dễ bỏ sót fraud.
- capacity-aware policy: chỉ đưa top risk cases vào queue theo capacity mỗi ngày.
- cost-sensitive policy: review khi expected benefit lớn hơn expected cost.

Đây sẽ là phần quan trọng nhất để đưa đề án từ mô phỏng dữ liệu sang thiết kế cơ chế ra quyết định.
