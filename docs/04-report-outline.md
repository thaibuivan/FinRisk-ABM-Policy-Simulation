# 04. Report Outline: Structure for the Final Thesis/Project Report

## 1. Mục đích

File này là dàn ý báo cáo cho đề án. Nó giúp chuyển các ý tưởng trong file 01, 02 và 03 thành một báo cáo học thuật có cấu trúc rõ ràng.

Báo cáo không nên trình bày như tài liệu sản phẩm. Nó cần đi theo logic nghiên cứu:

1. Vấn đề là gì?
2. Vì sao vấn đề đáng nghiên cứu?
3. Nền tảng lý thuyết nào liên quan?
4. Mô hình/khung mô phỏng được thiết kế ra sao?
5. Dữ liệu mô phỏng như thế nào?
6. Kết quả đánh giá policy ra sao?
7. Hạn chế và hướng phát triển là gì?

## 2. Tên đề tài đề xuất

Tiếng Anh:

Agent-Based Simulation and Mechanism Design for Transaction Risk Decisioning in Digital Finance

Tiếng Việt:

Mô phỏng đa tác nhân và thiết kế cơ chế trong ra quyết định rủi ro giao dịch số

## 3. Cấu trúc báo cáo đề xuất

### Chương 1. Giới thiệu đề tài

Nội dung cần có:

- Bối cảnh fintech và giao dịch số.
- Rủi ro gian lận/rủi ro giao dịch trong ngân hàng số.
- Hạn chế của cách tiếp cận chỉ dùng rule hoặc ML score.
- Vấn đề cần nghiên cứu: không chỉ dự đoán rủi ro mà còn thiết kế cơ chế ra quyết định.
- Mục tiêu nghiên cứu.
- Câu hỏi nghiên cứu.
- Phạm vi nghiên cứu.
- Đóng góp của đề án.

Thông điệp chính:

Risk score chỉ là tín hiệu. Giá trị nghiệp vụ xuất hiện khi tổ chức biết can thiệp đúng: approve, review, step-up hoặc escalate với chi phí hợp lý.

### Chương 2. Cơ sở lý thuyết

Nội dung cần có:

1. Transaction Risk Decisioning
   - Quy trình xử lý giao dịch rủi ro.
   - Các loại quyết định: approve, review, step-up, decline/escalate.
   - Vai trò của analyst.

2. Machine Learning Risk Scoring
   - Risk score là gì.
   - Precision, recall, PR-AUC, false positive, false negative.
   - Vì sao metric model chưa đủ để đánh giá hiệu quả nghiệp vụ.

3. Explainable AI
   - Vì sao cần giải thích model.
   - SHAP và risk drivers.
   - Vai trò của AI explanation trong analyst workflow.

4. Human-in-the-loop Decisioning
   - AI hỗ trợ, không thay thế analyst.
   - Audit trail và trách nhiệm quyết định.

5. Game Theory
   - Tác nhân có lợi ích riêng.
   - Fraud actor và platform có hành vi chiến lược.
   - Quyết định của một bên ảnh hưởng đến bên khác.

6. Mechanism Design
   - Thiết kế luật chơi để dẫn hành vi đến outcome mong muốn.
   - Threshold, review queue, priority rule và incentive/cost.

7. Agent-Based Modeling
   - Mô phỏng nhiều tác nhân.
   - Outcome xuất hiện sau tương tác.
   - Phù hợp khi không có dữ liệu thật hoặc khi muốn thử policy trước khi triển khai.

### Chương 3. Phương pháp nghiên cứu

Nội dung cần có:

- Thiết kế mô phỏng đa tác nhân.
- Các agent trong mô hình.
- Luồng mô phỏng.
- Cách sinh dữ liệu synthetic.
- Cách tạo risk score.
- Các policy được so sánh.
- Các KPI đánh giá.

Các agent:

- Normal customer
- Fraud actor
- Risk scoring system
- Policy maker
- Analyst
- Platform/bank

Luồng mô phỏng:

Customer/Fraud Actor -> Transaction -> Feature Engineering -> Risk Score -> Policy Decision -> Analyst Review -> Outcome -> KPI

### Chương 4. Thiết kế hệ thống/prototype

Nếu có sản phẩm demo cá nhân, chương này trình bày:

- Kiến trúc hệ thống.
- Backend API.
- Data generator.
- Dashboard.
- Case detail.
- AI explanation/report.
- Policy comparison.

Lưu ý:

Không nên bê nguyên tên hoặc nội dung sản phẩm đã nộp cho chương trình. Cần rebrand thành sản phẩm cá nhân theo hướng simulation platform.

### Chương 5. Kết quả mô phỏng và phân tích

Nội dung cần có:

- Mô tả các scenario.
- So sánh policy bằng model metrics.
- So sánh policy bằng operational metrics.
- So sánh policy bằng business metrics.
- Phân tích trade-off.

Các biểu đồ nên có:

1. Distribution risk score theo policy/scenario.
2. Fraud loss prevented vs false positive cost.
3. Analyst workload theo policy.
4. Backlog theo ngày.
5. Expected net benefit theo policy.
6. Review time có AI vs không AI.
7. Customer friction rate theo threshold.

Điểm cần nhấn mạnh:

Policy có recall cao nhất chưa chắc tốt nhất nếu false positive cost và analyst workload quá lớn.

### Chương 6. Thảo luận

Nội dung cần có:

- Ý nghĩa của kết quả.
- Trade-off giữa fraud prevention và customer friction.
- Vai trò của AI explanation.
- Khi nào nên dùng human-in-the-loop.
- Liên hệ với mechanism design.
- Liên hệ với causal/decision mindset: can thiệp nào tạo outcome tốt hơn?

### Chương 7. Hạn chế và hướng phát triển

Hạn chế:

- Dữ liệu là synthetic, chưa phải dữ liệu ngân hàng thật.
- Risk score ban đầu có thể là proxy model.
- Hành vi fraud actor còn đơn giản.
- Analyst behavior được mô phỏng bằng giả định.
- Chi phí nghiệp vụ cần được hiệu chỉnh bằng dữ liệu thực tế nếu triển khai thật.

Hướng phát triển:

- Hiệu chỉnh tham số bằng dữ liệu thực tế hoặc expert input.
- Thêm adaptive fraud strategy.
- Thêm causal evaluation hoặc A/B testing framework.
- Tối ưu policy bằng reinforcement learning hoặc optimization.
- Mở rộng AI agent để giải thích policy-level trade-off.

## 4. Phần mở đầu mẫu

Trong bối cảnh tài chính số, các tổ chức ngân hàng và fintech phải xử lý lượng lớn giao dịch theo thời gian gần thực. Mỗi giao dịch có thể chứa các tín hiệu rủi ro khác nhau như số tiền bất thường, tần suất giao dịch cao, thời điểm giao dịch không quen thuộc hoặc merchant có mức rủi ro cao. Các hệ thống machine learning có thể hỗ trợ chấm điểm rủi ro, nhưng risk score không trực tiếp trả lời câu hỏi nghiệp vụ quan trọng hơn: tổ chức nên can thiệp như thế nào để giảm tổn thất mà không tạo ra quá nhiều chi phí vận hành và trải nghiệm tiêu cực cho khách hàng?

Đề án này tiếp cận bài toán ra quyết định rủi ro giao dịch dưới góc nhìn mô phỏng đa tác nhân và thiết kế cơ chế. Thay vì chỉ đánh giá một mô hình dự báo bằng precision hoặc recall, đề án xây dựng một môi trường mô phỏng gồm khách hàng bình thường, tác nhân gian lận, hệ thống chấm điểm rủi ro, analyst và policy maker. Trên môi trường đó, các chính sách xử lý giao dịch được so sánh theo nhiều KPI như fraud loss prevented, false positive cost, analyst workload, customer friction và expected net benefit.

## 5. Đóng góp dự kiến của đề án

Đề án có ba đóng góp chính:

1. Xây dựng framework mô phỏng đa tác nhân cho transaction risk decisioning.
2. Đề xuất cách đánh giá policy không chỉ bằng metric model mà bằng KPI nghiệp vụ.
3. Minh họa vai trò của AI explanation trong quy trình analyst review có human-in-the-loop.

## 6. Cách liên hệ với dự án cá nhân

Sản phẩm demo cá nhân có thể được trình bày như một prototype hỗ trợ nghiên cứu:

- Người dùng chọn scenario và policy.
- Hệ thống mô phỏng giao dịch và risk score.
- Dashboard hiển thị KPI.
- AI agent giải thích case hoặc policy dựa trên evidence.
- Report tổng hợp trade-off giữa các policy.

Mục tiêu của prototype không phải khẳng định phát hiện fraud thật, mà là minh họa cách một tổ chức có thể thử nghiệm cơ chế ra quyết định trước khi triển khai.

## 7. Checklist để báo cáo đạt chất lượng

Trước khi hoàn thiện báo cáo, cần đảm bảo:

- Có câu hỏi nghiên cứu rõ ràng.
- Có nền tảng lý thuyết đủ sâu.
- Có mô hình agent rõ ràng.
- Có data generation logic minh bạch.
- Có KPI nghiệp vụ cụ thể.
- Có ít nhất 3-4 policy/scenario để so sánh.
- Có phân tích trade-off, không chỉ báo cáo số liệu.
- Có phần hạn chế trung thực.
- Có hướng phát triển hợp lý.

## 8. Việc cần làm tiếp theo

Sau file này, bước tiếp theo nên là:

1. Viết script sinh dữ liệu mô phỏng nhỏ.
2. Tạo 2-3 bảng kết quả giả lập đầu tiên.
3. Dùng kết quả đó để viết thử Chương 5.
4. Sau đó mới chỉnh giao diện/prototype nếu cần.
