# 12. Hướng dẫn prototype dashboard tương tác

## 1. Mục đích của prototype

Prototype này không nhằm thay thế một hệ thống production đầy đủ. Mục tiêu chính là minh họa phần thực nghiệm của đề án: khi thay đổi cơ chế ra quyết định rủi ro, năng lực review của analyst hoặc giả định chi phí, các chỉ số vận hành và lợi ích kỳ vọng thay đổi như thế nào.

Đây là hướng cân bằng cho đề án: đủ trực quan để trình bày sản phẩm, nhưng không tốn thời gian xây dựng frontend/backend hoàn chỉnh khi trọng tâm học thuật vẫn là mô phỏng đa tác nhân, thiết kế cơ chế và đánh giá chính sách.

## 2. File cần mở

Dashboard HTML mới nhất nằm trong thư mục:

`reports/prototype/`

File đã sinh:

`risk_decision_dashboard_20260721_122533.html`

Có thể mở trực tiếp bằng cách double-click trong File Explorer. Dashboard là một file HTML tĩnh, không cần chạy backend, frontend hoặc database.

## 3. Dashboard đang thể hiện những gì

Dashboard dùng dữ liệu từ các kết quả mô phỏng đã chạy trước đó:

- Scenario comparison: so sánh các kịch bản như baseline, low fraud, stress fraud, low capacity, high capacity.
- Policy comparison: so sánh các chính sách như balanced threshold, sensitive threshold, strict threshold, capacity-aware và cost-sensitive.
- Cost sensitivity: cho phép xem kết quả dưới nhiều giả định chi phí khác nhau như base cost, high false positive cost, high analyst cost, low recovery và high recovery.

Các chỉ số chính gồm:

- Net benefit: lợi ích kỳ vọng sau khi trừ tổn thất fraud còn lại, chi phí false positive và chi phí analyst.
- Precision reviewed: trong các giao dịch được analyst review, tỷ lệ giao dịch thật sự có rủi ro theo ground-truth mô phỏng.
- Recall reviewed: tỷ lệ case rủi ro được phát hiện và review.
- Review overflow: số alert vượt quá năng lực xử lý của analyst.
- Analyst reviewed: số alert thực tế được analyst xử lý.

## 4. Cách dùng khi trình bày đề án

Có thể trình bày theo luồng sau:

1. Chọn analyst capacity để cho thấy cùng một mô hình rủi ro nhưng năng lực vận hành khác nhau sẽ tạo outcome khác nhau.
2. Chọn cost scenario để chứng minh quyết định tối ưu không chỉ phụ thuộc vào accuracy của model, mà còn phụ thuộc vào chi phí nghiệp vụ.
3. So sánh các policy để trả lời câu hỏi: chính sách nào cân bằng tốt hơn giữa phát hiện rủi ro, tải analyst và chi phí false positive.
4. Dùng biểu đồ net benefit và recall để giải thích trade-off: một chính sách nhạy hơn có thể bắt được nhiều case rủi ro hơn, nhưng cũng tạo nhiều alert và chi phí hơn.

## 5. Cách đưa vào báo cáo

Trong báo cáo đề án, prototype nên được đặt sau phần phương pháp mô phỏng và trước phần kết luận thực nghiệm.

Gợi ý tên mục:

`Prototype minh họa cơ chế ra quyết định rủi ro`

Nội dung nên nhấn mạnh:

- Đây là sản phẩm minh họa kết quả mô phỏng, không phải hệ thống quyết định thật.
- Prototype giúp người đọc nhìn được tác động của policy, capacity và cost assumption.
- Prototype thể hiện tinh thần của Mechanism Design: thiết kế luật ra quyết định dựa trên mục tiêu outcome, không chỉ tối ưu một chỉ số model đơn lẻ.

## 6. Giới hạn hiện tại

- Dữ liệu là dữ liệu mô phỏng, được hiệu chỉnh bằng các nguồn tham khảo công khai.
- Risk score hiện tại là hàm chấm điểm mô phỏng, chưa phải model ML được huấn luyện và kiểm định như production.
- Net benefit là đơn vị utility mô phỏng, không nên diễn giải trực tiếp là lợi nhuận thực tế.
- Dashboard là HTML tĩnh, chưa có backend tương tác hoặc lưu trạng thái người dùng.

## 7. Hướng phát triển tiếp theo

Nếu có thêm thời gian, có thể phát triển theo 3 hướng:

- Huấn luyện model risk scoring thật trên dữ liệu mô phỏng có ground truth và so sánh với rule-based score.
- Bổ sung agent-based simulation động hơn, trong đó customer/fraudster/platform phản ứng lại chính sách theo thời gian.
- Xây dashboard web app có backend để chọn tham số mô phỏng và chạy lại scenario trực tiếp.
