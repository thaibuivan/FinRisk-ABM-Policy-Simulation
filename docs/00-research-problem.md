# 00. Research Problem: Transaction Risk Decisioning as a Mechanism Design Problem

## 1. Mục đích của file này

File này là điểm bắt đầu của đề án. Trước khi thiết kế mô phỏng, sinh dữ liệu hoặc chỉnh sản phẩm demo, cần làm rõ:

- Vấn đề nghiên cứu là gì?
- Vì sao vấn đề này quan trọng trong fintech?
- Khoảng trống của cách tiếp cận hiện tại nằm ở đâu?
- Câu hỏi nghiên cứu chính là gì?
- Đề án sẽ đo lường thành công bằng KPI nào?
- Phạm vi nào làm, phạm vi nào chưa làm?

Nếu không có bước này, đề án dễ rơi vào hướng cũ: tạo dữ liệu synthetic, huấn luyện model, làm dashboard, nhưng chưa trả lời rõ hệ thống đó tối ưu quyết định nghiệp vụ như thế nào.

## 2. Bối cảnh

Trong các nền tảng tài chính số, số lượng giao dịch phát sinh mỗi ngày rất lớn. Mỗi giao dịch có thể mang các tín hiệu rủi ro khác nhau như số tiền bất thường, tần suất giao dịch cao, thời điểm giao dịch khác thường, merchant rủi ro hoặc hành vi lệch khỏi lịch sử của khách hàng.

Các hệ thống hiện đại thường sử dụng rule-based system hoặc machine learning model để chấm điểm rủi ro. Kết quả đầu ra thường là risk score, risk level hoặc danh sách alert/case cần analyst review.

Tuy nhiên, risk score chỉ là một tín hiệu dự báo. Từ risk score đến quyết định nghiệp vụ còn một khoảng cách lớn:

- Giao dịch nào nên approve ngay?
- Giao dịch nào nên đưa vào review queue?
- Khi nào nên yêu cầu xác thực bổ sung?
- Khi nào nên escalation?
- Analyst nên ưu tiên case nào trước?
- Có nên dùng AI explanation/report để hỗ trợ review không?
- Chính sách nào giảm tổn thất nhưng không làm tăng quá nhiều false positive và customer friction?

Vì vậy, bài toán không chỉ là bài toán dự báo fraud/risk. Nó còn là bài toán thiết kế cơ chế ra quyết định trong điều kiện nhiều tác nhân, nhiều chi phí và nhiều ràng buộc vận hành.

## 3. Vấn đề nghiên cứu

Cách tiếp cận phổ biến trong fraud/risk analytics thường tập trung vào model performance, ví dụ precision, recall, ROC-AUC hoặc PR-AUC. Các chỉ số này quan trọng, nhưng chưa đủ để trả lời câu hỏi cuối cùng của tổ chức tài chính:

Một policy ra quyết định có thật sự giúp giảm tổn thất và tối ưu chi phí vận hành không?

Một model có recall cao có thể bắt được nhiều giao dịch rủi ro hơn, nhưng cũng có thể tạo ra nhiều false positive hơn. Khi false positive tăng, analyst workload tăng, khách hàng hợp lệ bị review/block nhầm nhiều hơn, thời gian xử lý dài hơn và trải nghiệm khách hàng xấu đi.

Ngược lại, một policy quá lỏng có thể giảm workload và customer friction, nhưng lại bỏ sót nhiều giao dịch rủi ro, dẫn đến fraud loss cao hơn.

Vì thế, vấn đề nghiên cứu của đề án là:

Làm thế nào để thiết kế và đánh giá cơ chế ra quyết định rủi ro giao dịch sao cho cân bằng giữa phát hiện rủi ro, chi phí vận hành, trải nghiệm khách hàng và vai trò của analyst?

## 4. Khoảng trống nghiên cứu/thực tiễn

### 4.1. Khoảng trống 1: Từ predictive score đến decision policy

Nhiều hệ thống dừng ở việc đưa ra risk score. Nhưng trong thực tế, tổ chức cần một policy để biến score thành action.

Ví dụ:

- Score 40 nên approve hay review?
- Score 75 nên review hay yêu cầu xác thực bổ sung?
- Score 95 có nên ưu tiên analyst trước không?

Nếu chỉ tối ưu model mà không tối ưu policy, hệ thống có thể tạo ra alert quá nhiều, analyst bị quá tải và giá trị thực tế bị giảm.

### 4.2. Khoảng trống 2: Metric kỹ thuật chưa quy đổi sang KPI nghiệp vụ

Precision, recall hoặc PR-AUC không trực tiếp cho biết:

- Tiết kiệm được bao nhiêu fraud loss?
- Tốn bao nhiêu chi phí analyst?
- Bao nhiêu khách hàng tốt bị ảnh hưởng?
- Review time giảm bao nhiêu?
- Expected net benefit của policy là bao nhiêu?

Đề án cần quy đổi model/policy performance sang các KPI gần với quyết định kinh doanh hơn.

### 4.3. Khoảng trống 3: Thiếu mô phỏng phản ứng của tác nhân

Fraud actor có thể thay đổi hành vi khi policy thay đổi. Khách hàng bình thường có thể rời bỏ nếu bị friction quá nhiều. Analyst có thể bị quá tải nếu review queue quá lớn.

Do đó, hệ thống không nên được xem là dữ liệu tĩnh. Nó nên được mô phỏng như một môi trường có nhiều tác nhân và phản ứng qua lại.

### 4.4. Khoảng trống 4: AI explanation cần được đánh giá theo tác động vận hành

AI Agent có thể giải thích vì sao case bị cảnh báo, nhưng câu hỏi quan trọng hơn là:

- AI explanation có giúp analyst review nhanh hơn không?
- Có giảm lỗi review không?
- Có tạo audit trail tốt hơn không?
- Chi phí LLM có xứng đáng so với lợi ích vận hành không?

Đề án cần đặt AI explanation vào cơ chế ra quyết định, thay vì chỉ xem nó là một tính năng giao diện.

## 5. Mục tiêu nghiên cứu

Mục tiêu tổng quát:

Xây dựng một framework mô phỏng đa tác nhân để đánh giá các cơ chế ra quyết định rủi ro giao dịch trong tài chính số, xét đồng thời hiệu quả phát hiện rủi ro, chi phí vận hành, customer friction và hỗ trợ của AI explanation.

Mục tiêu cụ thể:

1. Xây dựng mô hình khái niệm gồm các tác nhân chính: khách hàng bình thường, tác nhân rủi ro/gian lận, hệ thống risk scoring, analyst, platform và policy maker.
2. Thiết kế các policy ra quyết định dựa trên rule, risk score, analyst review và AI explanation.
3. Sinh dữ liệu mô phỏng theo hành vi của các tác nhân và cơ chế tương tác.
4. Đánh giá các policy bằng cả model metrics, operational metrics và business metrics.
5. Phân tích trade-off giữa fraud loss prevented, false positive cost, analyst workload, customer friction và expected net benefit.
6. Đề xuất hướng prototype cá nhân minh họa cho framework nghiên cứu.

## 6. Câu hỏi nghiên cứu

### 6.1. Câu hỏi nghiên cứu chính

Trong hệ thống giao dịch số, cơ chế kết hợp risk scoring, analyst review và AI explanation có thể cải thiện hiệu quả ra quyết định rủi ro như thế nào khi xét đồng thời tổn thất gian lận, false positive cost, workload của analyst và customer friction?

### 6.2. Câu hỏi nghiên cứu phụ

1. Risk threshold khác nhau tạo ra trade-off như thế nào giữa fraud loss prevented và false positive cost?
2. Cơ chế human-in-the-loop có giúp cân bằng giữa phát hiện rủi ro và tránh quyết định tự động sai không?
3. AI explanation/report có thể giảm review time và hỗ trợ analyst hiểu case tốt hơn không?
4. Khi analyst capacity bị giới hạn, policy ưu tiên case theo risk score có giúp giảm backlog và tập trung vào case quan trọng hơn không?
5. Khi fraud actor thay đổi hành vi, policy hiện tại có còn hiệu quả không?
6. Policy nào tạo expected net benefit tốt nhất trong các điều kiện fraud rate, transaction volume và analyst capacity khác nhau?

## 7. Giả thuyết/kỳ vọng nghiên cứu

Đề án có thể kiểm tra một số kỳ vọng sau:

### H1. Threshold thấp làm tăng recall nhưng cũng làm tăng false positive cost

Khi threshold cảnh báo thấp, hệ thống phát hiện được nhiều giao dịch rủi ro hơn. Tuy nhiên, số giao dịch hợp lệ bị review nhầm cũng tăng, làm tăng chi phí analyst và customer friction.

### H2. Human-in-the-loop giúp giảm rủi ro quyết định tự động sai

So với cơ chế tự động xử lý theo score, cơ chế đưa case rủi ro vào analyst review có thể giảm các quyết định sai ở nhóm case nhạy cảm, nhưng đổi lại làm tăng workload.

### H3. AI explanation có thể giảm review time nhưng phát sinh AI cost

AI explanation/report giúp analyst hiểu case nhanh hơn, từ đó giảm review time trung bình. Tuy nhiên, lợi ích này cần được so sánh với chi phí token/latency của LLM.

### H4. Policy tối ưu theo model metric chưa chắc tối ưu theo business KPI

Một policy có recall cao nhất chưa chắc có expected net benefit cao nhất nếu false positive cost, analyst workload và customer friction quá lớn.

### H5. Fraud adaptation làm giảm hiệu quả của policy tĩnh

Khi fraud actor thay đổi chiến lược để né rule/threshold, policy tĩnh có thể mất hiệu quả. Điều này cho thấy cần cơ chế theo dõi và cập nhật policy.

## 8. Đối tượng và phạm vi nghiên cứu

### 8.1. Đối tượng nghiên cứu

Đối tượng nghiên cứu là cơ chế ra quyết định rủi ro giao dịch trong môi trường tài chính số, bao gồm:

- Giao dịch mô phỏng.
- Risk score/risk evidence.
- Policy approve/review/escalate.
- Analyst review.
- AI explanation hỗ trợ analyst.
- KPI vận hành và kinh doanh.

### 8.2. Phạm vi làm trong đề án

Đề án tập trung vào:

- Mô phỏng dữ liệu synthetic theo cơ chế đa tác nhân.
- So sánh một số policy ra quyết định cơ bản.
- Tính KPI đánh giá policy.
- Thiết kế prototype minh họa nếu có thời gian.

### 8.3. Phạm vi chưa làm

Đề án chưa khẳng định:

- Có thể phát hiện fraud thật trong ngân hàng thực tế.
- Có thể tự động block/reject giao dịch thật.
- Có thể thay thế analyst.
- Có thể dùng dữ liệu thật không qua kiểm định pháp lý/bảo mật.

Các kết quả mô phỏng chỉ dùng để minh họa cơ chế và so sánh policy trong môi trường giả lập.

## 9. Phương pháp nghiên cứu dự kiến

Đề án kết hợp 4 hướng:

1. Literature review
   - Tổng quan transaction risk decisioning, XAI, human-in-the-loop, Game Theory, Mechanism Design và Agent-Based Modeling.

2. Conceptual framework
   - Thiết kế framework tác nhân, hành động, policy, outcome và KPI.

3. Simulation experiment
   - Sinh dữ liệu synthetic và chạy mô phỏng nhiều scenario/policy.

4. Prototype demonstration
   - Nếu có thời gian, xây dashboard/AI agent minh họa cách analyst hoặc policy maker theo dõi kết quả.

## 10. Đóng góp dự kiến

Đề án có ba đóng góp chính:

1. Đóng góp về tư duy
   - Chuyển bài toán từ fraud prediction sang transaction risk decisioning.
   - Nhấn mạnh việc đánh giá policy bằng KPI nghiệp vụ thay vì chỉ metric model.

2. Đóng góp về phương pháp
   - Đề xuất framework mô phỏng đa tác nhân cho quy trình xử lý rủi ro giao dịch.
   - Kết hợp risk scoring, policy decision, analyst review và AI explanation trong cùng một cơ chế.

3. Đóng góp về ứng dụng
   - Minh họa cách fintech/ngân hàng có thể thử nghiệm policy trong môi trường mô phỏng trước khi triển khai.
   - Tạo nền cho sản phẩm cá nhân về decision simulation trong financial risk.

## 11. Tiêu chí thành công của đề án

Đề án được xem là đạt yêu cầu nếu:

1. Câu hỏi nghiên cứu rõ ràng và nhất quán.
2. Lý thuyết Game Theory, Mechanism Design và ABM được kết nối đúng với bài toán fintech.
3. Dữ liệu mô phỏng được sinh từ cơ chế hành vi, không chỉ random feature.
4. Có ít nhất 3 policy được so sánh.
5. Có KPI business/operation ngoài model metric.
6. Kết quả phân tích chỉ ra trade-off rõ ràng.
7. Có phần hạn chế trung thực về synthetic data.
8. Prototype nếu có chỉ đóng vai trò minh họa, không thay thế phần nghiên cứu.

## 12. Câu chốt định hướng

Đề án này không đặt mục tiêu xây dựng một mô hình phát hiện gian lận tối ưu nhất. Thay vào đó, đề án tập trung vào câu hỏi rộng hơn: trong một hệ thống giao dịch số có nhiều tác nhân và nhiều loại chi phí, cơ chế ra quyết định nào giúp tổ chức xử lý rủi ro hiệu quả hơn?
