# 13. Roadmap hoàn thiện đề án theo hướng cân bằng

## 1. Mục tiêu hoàn thiện

Đề án nên được hoàn thiện theo hướng vừa có nền tảng lý thuyết đủ chặt, vừa có prototype minh họa kết quả. Không nên biến đề án thành một dự án phần mềm quá nặng, vì trọng tâm chính là tư duy thiết kế cơ chế ra quyết định rủi ro.

Tên hướng đề án đề xuất:

`Mô phỏng đa tác nhân và thiết kế cơ chế trong ra quyết định rủi ro giao dịch số`

Câu hỏi trung tâm:

`Một nền tảng tài chính số nên thiết kế cơ chế cảnh báo và review giao dịch như thế nào để cân bằng giữa phát hiện rủi ro, chi phí vận hành, chi phí false positive và tải xử lý của analyst?`

## 2. Những phần đã có

### 2.1. Khung lý thuyết và câu hỏi nghiên cứu

Đã có các file:

- `docs/00-research-problem.md`
- `docs/01-de-an-framework.md`
- `docs/02-simulation-design.md`
- `docs/03-data-generator-plan.md`
- `docs/04-report-outline.md`

Các file này dùng để viết phần mở đầu, tổng quan tư duy và phương pháp nghiên cứu.

### 2.2. Nguồn dữ liệu tham khảo

Đã có các file mô tả nguồn dữ liệu:

- `docs/05-reference-data-sources.md`
- `docs/06-calibration-assumptions.md`

Đã có profile tham khảo từ các dataset công khai trong:

- `data/reference/profiles/`

Ý nghĩa: dữ liệu mô phỏng không được tạo tùy tiện, mà được hiệu chỉnh từ phân phối quan sát trong các nguồn công khai.

### 2.3. Dữ liệu mô phỏng và kết quả thực nghiệm

Đã sinh các simulation runs trong:

- `data/simulation_runs/`

Đã có kết quả so sánh scenario trong:

- `data/scenario_comparisons/`

Đã có kết quả so sánh policy trong:

- `data/policy_comparisons/`

Đã có báo cáo phân tích trong:

- `reports/analysis/`

### 2.4. Prototype minh họa

Đã có static interactive dashboard trong:

- `reports/prototype/risk_decision_dashboard_20260721_122533.html`

Đây là phần sản phẩm minh họa, có thể dùng trong đề án để chứng minh kết quả mô phỏng không chỉ nằm ở bảng số liệu.

## 3. Những phần nên làm tiếp

### Ưu tiên 1: Viết báo cáo đề án bản hoàn chỉnh

Nên gom các nội dung hiện có thành một báo cáo mạch lạc với cấu trúc:

1. Giới thiệu bài toán
2. Cơ sở lý thuyết
3. Thiết kế mô phỏng
4. Thiết kế cơ chế ra quyết định
5. Kết quả thực nghiệm
6. Prototype minh họa
7. Giới hạn và hướng phát triển
8. Kết luận

Phần quan trọng nhất không phải là dashboard, mà là giải thích được tại sao mỗi cơ chế tạo ra outcome khác nhau.

### Ưu tiên 2: Làm rõ metric nghiệp vụ

Cần nhấn mạnh các metric sau:

- Fraud loss prevented
- Fraud loss realized
- False positive cost
- Analyst cost
- Review overflow
- Precision reviewed
- Recall reviewed
- Net benefit

Trong đó `net benefit` nên được gọi là `utility mô phỏng`, không gọi trực tiếp là lợi nhuận thật.

### Ưu tiên 3: Viết rõ phần giả định

Các giả định cần minh bạch:

- Tỷ lệ fraud được mô phỏng.
- Chi phí false positive được giả định.
- Chi phí analyst được giả định.
- Năng lực review theo ngày được giả định.
- Risk score hiện tại là hàm mô phỏng, chưa phải model ML production.

Điểm này giúp đề án chặt hơn và tránh bị bắt bẻ là dữ liệu không thật.

### Ưu tiên 4: Đưa prototype vào phụ lục hoặc chương thực nghiệm

Dashboard nên được dùng như minh họa:

- Chọn scenario.
- Chọn capacity.
- Chọn cost assumption.
- So sánh policy.

Không nên trình bày prototype như sản phẩm thương mại hoàn chỉnh.

## 4. Những phần chưa cần làm ngay

Không cần làm ngay nếu thời gian hạn chế:

- Full frontend/backend app.
- Login, database, deploy online.
- LLM agent.
- Real-time stream.
- Model ML phức tạp.

Những phần này có thể đưa vào hướng phát triển tiếp theo.

## 5. Cách trình bày với giảng viên

Có thể nói ngắn gọn:

`Em sẽ không đi theo hướng chỉ build một hệ thống fraud detection. Em sẽ chuyển trọng tâm sang bài toán thiết kế cơ chế ra quyết định rủi ro. Dữ liệu được mô phỏng dựa trên các nguồn tham khảo công khai, sau đó em so sánh nhiều policy dưới các giả định về chi phí và năng lực analyst. Prototype dashboard chỉ dùng để minh họa trade-off giữa phát hiện rủi ro, chi phí false positive và tải vận hành.`

## 6. Tiêu chí để biết đề án đã đủ tốt

Đề án đạt mức hoàn chỉnh khi trả lời rõ được 5 câu hỏi:

1. Bài toán ra quyết định là gì?
2. Các tác nhân trong hệ thống là ai và họ có vai trò gì?
3. Cơ chế/policy nào được so sánh?
4. Metric nào dùng để đánh giá outcome?
5. Kết quả cho thấy trade-off gì và cơ chế nào phù hợp hơn trong điều kiện nào?
