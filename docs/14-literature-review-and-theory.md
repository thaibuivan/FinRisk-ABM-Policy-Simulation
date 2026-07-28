# 14. Cơ sở lý thuyết và tổng quan tài liệu

## 1. Vai trò của file này

File này chắt lọc các nền tảng lý thuyết quan trọng cho đề án:

**Mô phỏng đa tác nhân và thiết kế cơ chế trong ra quyết định rủi ro giao dịch số.**

Hai tài liệu tham khảo chính được sử dụng làm nền tảng tư duy là:

1. Marco A. Janssen, *Introduction to Agent-Based Modeling: with applications to social, ecological, and social-ecological systems*.
2. Bastien Baldacci, *Quantitative finance at the microstructure scale: algorithmic trading and regulation*.

Tài liệu của Janssen giúp xây dựng nền tảng về mô hình hóa đa tác nhân, hệ phức hợp thích nghi, emergence, sensitivity analysis và cách so sánh dữ liệu mô phỏng với dữ liệu thực nghiệm. Tài liệu của Baldacci giúp mở rộng góc nhìn sang tài chính định lượng ở cấp vi mô, nơi quyết định của các tác nhân, incentive, regulation và cơ chế thị trường có thể làm thay đổi outcome chung của hệ thống.

Trong đề án này, hai hướng trên được kết nối lại: hệ thống xử lý rủi ro giao dịch không chỉ là một mô hình dự báo fraud, mà là một cơ chế ra quyết định gồm nhiều tác nhân, nhiều chi phí và nhiều phản ứng qua lại.

---

## 2. Vì sao cần nền tảng lý thuyết thay vì chỉ xây mô hình dự báo

Một cách tiếp cận phổ biến trong các bài toán fraud/risk analytics là xây dựng mô hình dự báo: mô hình nhận dữ liệu giao dịch, trả về xác suất gian lận hoặc điểm rủi ro. Sau đó hệ thống dùng một ngưỡng để quyết định giao dịch nào bị cảnh báo.

Cách tiếp cận này có giá trị, nhưng chưa đủ cho một hệ thống ra quyết định thực tế. Lý do là risk score chỉ trả lời câu hỏi:

> Giao dịch này có vẻ rủi ro đến mức nào?

Trong khi hệ thống vận hành cần trả lời nhiều câu hỏi rộng hơn:

- Có nên cho giao dịch đi tiếp ngay không?
- Có nên đưa giao dịch vào hàng đợi analyst review không?
- Có nên yêu cầu xác thực bổ sung không?
- Analyst nên xử lý case nào trước khi năng lực review bị giới hạn?
- Nếu policy quá chặt, chi phí false positive và customer friction tăng bao nhiêu?
- Nếu policy quá lỏng, tổn thất do bỏ sót rủi ro tăng bao nhiêu?
- AI explanation có thật sự giảm thời gian review và chi phí vận hành không?

Do đó, đề án cần chuyển trọng tâm từ “dự báo giao dịch rủi ro” sang “thiết kế và đánh giá cơ chế ra quyết định rủi ro”. Đây là lý do các khái niệm như Agent-Based Modeling, Game Theory, Mechanism Design, Principal-Agent và market microstructure trở nên phù hợp.

---

## 3. Hệ phức hợp thích nghi và hiện tượng nổi lên

### 3.1. Khái niệm hệ phức hợp thích nghi

Trong tài liệu của Janssen, agent-based modeling được đặt trong bối cảnh rộng hơn của complex adaptive systems. Một hệ phức hợp thích nghi gồm nhiều tác nhân tương tác với nhau. Mỗi tác nhân thường chỉ có thông tin cục bộ, hành động theo quy tắc riêng, nhưng tương tác giữa các tác nhân có thể tạo ra hành vi tổng thể phức tạp ở cấp hệ thống.

Điểm quan trọng là hệ thống không nhất thiết được điều khiển hoàn toàn từ trên xuống. Nhiều hiện tượng tổng thể xuất hiện từ các quyết định nhỏ ở cấp cá nhân. Janssen dùng nhiều ví dụ như đàn kiến, giao thông, flocking, social diffusion và thị trường tài chính để minh họa rằng kết quả vĩ mô có thể xuất hiện từ tương tác vi mô.

Áp dụng vào đề án, hệ thống rủi ro giao dịch số cũng có đặc điểm tương tự:

- Khách hàng bình thường tạo giao dịch theo thói quen cá nhân.
- Tác nhân rủi ro/gian lận thay đổi hành vi để né phát hiện.
- Hệ thống risk scoring phản ứng với tín hiệu trong dữ liệu.
- Policy maker thay đổi ngưỡng và cơ chế review.
- Analyst xử lý case với năng lực hữu hạn.
- Platform chịu tổng chi phí và lợi ích cuối cùng.

Tổng thể rủi ro không nằm ở từng giao dịch riêng lẻ, mà xuất hiện từ tương tác giữa hành vi giao dịch, luật chấm điểm, policy review, năng lực analyst và phản ứng của các tác nhân.

### 3.2. Emergence trong bài toán rủi ro giao dịch

Emergence có thể hiểu là hiện tượng cấp hệ thống xuất hiện từ tương tác cấp cá nhân. Trong giao dịch số, các hiện tượng như backlog của analyst, customer friction tăng cao, hoặc fraud loss tăng không nhất thiết xuất hiện từ một giao dịch đơn lẻ. Chúng có thể xuất hiện khi nhiều giao dịch, nhiều policy và nhiều giới hạn vận hành cùng tương tác.

Ví dụ:

- Nếu threshold cảnh báo quá thấp, nhiều giao dịch hợp lệ bị đưa vào review. Ban đầu chỉ là vài false positive riêng lẻ, nhưng khi số lượng tăng, analyst queue bị quá tải và thời gian xử lý kéo dài.
- Nếu threshold quá cao, số case review giảm, nhưng một phần giao dịch rủi ro bị bỏ sót. Khi fraud actor nhận ra cơ chế này, họ có thể điều chỉnh hành vi để nằm dưới ngưỡng cảnh báo.
- Nếu AI explanation giúp giảm thời gian review, cùng một số lượng analyst có thể xử lý nhiều case hơn. Điều này không chỉ giảm chi phí thời gian mà còn thay đổi hiệu quả của policy ưu tiên case.

Vì vậy, đề án không nên chỉ đo precision/recall của model. Cần đo cả các outcome nổi lên ở cấp hệ thống như review overflow, analyst workload, false positive cost, customer friction và simulated net benefit.

---

## 4. Mô hình là sự đơn giản hóa có mục đích

Janssen nhấn mạnh rằng mô hình không phải bản sao của thực tế. Mô hình là một sự đơn giản hóa có mục đích, trong đó người nghiên cứu phải quyết định điều gì cần đưa vào và điều gì cần bỏ ra. Một mô hình tốt không nhất thiết phải mô phỏng toàn bộ thế giới, mà cần giữ lại các cơ chế quan trọng nhất để trả lời câu hỏi nghiên cứu.

Điều này đặc biệt quan trọng với đề án hiện tại. Nếu cố mô phỏng toàn bộ hệ thống ngân hàng, đề án sẽ quá rộng và không kiểm soát được. Thay vào đó, mô hình nên tập trung vào một quy trình nhỏ nhưng có ý nghĩa:

Transaction stream -> Risk score -> Policy decision -> Analyst review -> Outcome -> KPI.

Các yếu tố được giữ lại trong mô hình gồm:

- Hành vi giao dịch của khách hàng.
- Một nhóm giao dịch rủi ro hoặc gian lận mô phỏng.
- Risk score/risk level.
- Policy approve/review/escalate.
- Năng lực xử lý của analyst.
- Chi phí false positive, chi phí analyst, fraud loss và lợi ích do phát hiện đúng.

Các yếu tố chưa cần đưa vào giai đoạn đầu gồm:

- Dữ liệu PII thật.
- Luồng tiền ngân hàng thực tế.
- Mạng thiết bị/IP phức tạp.
- Tác động pháp lý đầy đủ.
- Model ML production-ready.

Như vậy, mô hình không nhằm khẳng định có thể phát hiện fraud thật trong ngân hàng, mà nhằm kiểm tra cơ chế ra quyết định trong một môi trường giả lập có kiểm soát.

---

## 5. Agent-Based Modeling trong đề án

### 5.1. Vì sao ABM phù hợp

Agent-Based Modeling phù hợp với các hệ thống có nhiều tác nhân tự chủ, có hành vi khác nhau và tương tác theo thời gian. Thay vì mô hình hóa hệ thống bằng một công thức tổng quát duy nhất, ABM mô tả từng loại tác nhân, quy tắc hành vi của họ, môi trường họ tương tác và outcome sinh ra sau mô phỏng.

Trong đề án này, ABM phù hợp vì bài toán rủi ro giao dịch có các đặc điểm sau:

1. **Tính dị biệt của tác nhân**
   Khách hàng không giống nhau. Có người giao dịch ít, có người giao dịch nhiều, có người thường mua vào ban đêm, có người chỉ giao dịch giờ hành chính. Fraud actor cũng có nhiều chiến lược khác nhau như high amount, burst velocity, merchant abuse hoặc late-hour transaction.

2. **Tương tác với policy**
   Một giao dịch không chỉ được đánh giá bởi bản thân nó, mà còn bởi policy hiện hành. Khi policy thay đổi, số giao dịch bị review, backlog và cost cũng thay đổi.

3. **Giới hạn vận hành**
   Analyst không có năng lực vô hạn. Khi review queue vượt quá capacity, một số case có thể bị trễ hoặc không được xử lý kịp. Đây là yếu tố rất khó thấy nếu chỉ nhìn vào metric model.

4. **Outcome không có sẵn trong dữ liệu ban đầu**
   Net benefit, review overflow hoặc customer friction không phải cột dữ liệu có sẵn. Chúng xuất hiện sau khi hệ thống áp dụng policy lên giao dịch.

5. **Có thể thử nghiệm nhiều kịch bản**
   ABM cho phép thay đổi fraud rate, analyst capacity, threshold, cost assumption và policy để xem outcome thay đổi thế nào.

### 5.2. Các tác nhân trong mô hình đề án

Đề án có thể mô tả các tác nhân chính như sau:

**Normal customer agent**

Tạo giao dịch hợp lệ theo hành vi bình thường. Tác nhân này giúp mô phỏng false positive: khi giao dịch hợp lệ bị review hoặc chặn nhầm, hệ thống phát sinh chi phí vận hành và customer friction.

**Risky/fraud behavior agent**

Tạo giao dịch có tín hiệu rủi ro như số tiền cao bất thường, tần suất dày, khung giờ lạ hoặc merchant rủi ro. Trong phiên bản nâng cao, tác nhân này có thể thích nghi với policy để tránh bị phát hiện.

**Risk scoring agent**

Đại diện cho rule/model tạo risk score. Ở giai đoạn MVP, risk score có thể là hàm mô phỏng dựa trên amount anomaly, velocity, time signal, merchant risk và customer behavior. Ở giai đoạn sau, hàm này có thể thay bằng model ML được huấn luyện.

**Policy maker agent**

Chuyển risk score thành hành động: approve, review, step-up authentication hoặc escalate trong mô phỏng. Đây là trung tâm của thiết kế cơ chế.

**Analyst agent**

Xử lý case trong hàng đợi review. Analyst có giới hạn capacity, thời gian review và xác suất xử lý đúng. Nếu có AI explanation, thời gian review có thể giảm hoặc evidence dễ hiểu hơn.

**Platform/bank agent**

Chịu outcome cuối cùng: fraud loss, false positive cost, analyst cost, AI cost, customer friction và simulated net benefit.

### 5.3. Mô hình hóa hành vi và outcome

Trong ABM, cần phân biệt rõ ba lớp:

- **Behavior layer:** tác nhân tạo giao dịch và phản ứng với môi trường.
- **Decision layer:** hệ thống áp dụng risk score và policy.
- **Outcome layer:** kết quả sau decision, gồm cost, workload, recall, precision và net benefit mô phỏng.

Điểm này giúp đề án tránh lỗi chỉ tạo synthetic data cho đẹp model. Dữ liệu không chỉ là bảng giao dịch ngẫu nhiên, mà là kết quả của một quy trình có tác nhân, luật chơi và hệ quả.

---

## 6. Sensitivity analysis và so sánh mô phỏng với dữ liệu tham khảo

Một phần quan trọng trong tài liệu của Janssen là model analysis, trong đó có sensitivity analysis và so sánh dữ liệu mô phỏng với dữ liệu thực nghiệm. Đây là phần rất phù hợp để làm đề án chặt hơn.

### 6.1. Sensitivity analysis

Sensitivity analysis trả lời câu hỏi: nếu thay đổi giả định đầu vào, kết quả đầu ra có thay đổi mạnh không?

Trong đề án, các tham số nên kiểm tra gồm:

- Fraud rate.
- Analyst capacity.
- Review threshold.
- False positive cost.
- Analyst cost per minute.
- Fraud recovery rate.
- Tác động của AI explanation lên review time.

Nếu một policy chỉ tốt trong một bộ giả định rất hẹp, policy đó có thể không bền vững. Ngược lại, nếu một policy vẫn tạo outcome tốt trong nhiều scenario, đó là bằng chứng mạnh hơn cho tính hữu ích của cơ chế.

### 6.2. So sánh dữ liệu mô phỏng với dữ liệu tham khảo

Vì dữ liệu giao dịch thật thường nhạy cảm và khó công khai, đề án sử dụng dữ liệu synthetic. Tuy nhiên, synthetic data không nên được tạo tùy tiện. Nó cần được hiệu chỉnh bằng các nguồn dữ liệu công khai như ULB Credit Card Fraud, BankSim hoặc PaySim.

Mục tiêu của việc tham khảo dữ liệu công khai không phải là sao chép dữ liệu, mà là lấy một số đặc điểm tổng quát:

- Fraud thường là lớp hiếm.
- Phân phối amount thường lệch phải, có một số giao dịch rất lớn.
- Hành vi giao dịch có yếu tố thời gian và tần suất.
- Một số kịch bản fraud có thể biểu hiện qua velocity, merchant/category hoặc bất thường so với hành vi lịch sử.

Do đó, trong báo cáo nên viết rõ: dữ liệu mô phỏng được hiệu chỉnh theo phân phối và đặc điểm tổng quát từ dữ liệu tham khảo, nhưng kết quả không đại diện cho hiệu suất production trong ngân hàng thật.

---

## 7. Game Theory và Mechanism Design trong bài toán ra quyết định rủi ro

### 7.1. Game Theory

Game Theory nghiên cứu tình huống trong đó nhiều tác nhân có mục tiêu riêng, và quyết định của một tác nhân ảnh hưởng đến outcome của tác nhân khác. Trong transaction risk decisioning, có thể nhìn thấy cấu trúc game ở nhiều tầng:

- Fraud actor muốn giao dịch thành công mà không bị phát hiện.
- Platform muốn giảm fraud loss nhưng không làm khách hàng tốt bị ảnh hưởng quá nhiều.
- Analyst muốn xử lý case hiệu quả trong giới hạn thời gian.
- Khách hàng hợp lệ muốn giao dịch nhanh, ít friction.
- Policy maker muốn cân bằng giữa an toàn, chi phí và trải nghiệm.

Nếu policy quá dễ đoán, fraud actor có thể điều chỉnh hành vi. Nếu policy quá chặt, khách hàng tốt chịu friction và analyst bị quá tải. Vì vậy, hệ thống không chỉ là bài toán classification, mà là bài toán chiến lược giữa nhiều bên có lợi ích khác nhau.

### 7.2. Mechanism Design

Mechanism Design có thể hiểu là thiết kế “luật chơi” để hướng hành vi của các tác nhân đến outcome mong muốn. Nếu Game Theory hỏi “với luật chơi có sẵn, các tác nhân sẽ hành động thế nào?”, thì Mechanism Design hỏi ngược lại: “muốn có outcome mong muốn, nên thiết kế luật chơi như thế nào?”

Trong đề án, “luật chơi” chính là policy ra quyết định:

- Threshold nào đưa giao dịch vào review?
- Case nào được ưu tiên khi analyst capacity giới hạn?
- Khi nào dùng AI explanation?
- Chi phí false positive được tính như thế nào?
- Có nên phân nhóm khách hàng/merchant để áp dụng policy khác nhau không?

Outcome mong muốn không phải là recall cao nhất bằng mọi giá, mà là cân bằng giữa:

- Giảm fraud loss.
- Kiểm soát false positive.
- Giảm workload analyst.
- Giảm customer friction.
- Tăng simulated net benefit.

Vì vậy, phần thực nghiệm của đề án nên trình bày như quá trình so sánh nhiều cơ chế ra quyết định, thay vì chỉ so sánh nhiều model dự báo.

---

## 8. Principal-Agent và microstructure finance: bài học từ tài liệu Quant Finance

Tài liệu của Baldacci nghiên cứu tài chính định lượng ở cấp microstructure, đặc biệt là market-making, optimal trading, incentive design và regulation. Mặc dù đề án hiện tại không trực tiếp làm về order book hay market maker, tài liệu này vẫn hữu ích ở tầng tư duy cơ chế.

### 8.1. Principal-Agent và incentive design

Trong phần đầu của luận án, Baldacci đặt bài toán market-making regulation dưới góc nhìn Principal-Agent. Principal là exchange/platform, Agent là market-maker. Platform muốn cải thiện chất lượng thị trường, ví dụ thanh khoản hoặc trading activity, nhưng market-maker hành động theo lợi ích riêng. Vì vậy, platform cần thiết kế incentive/contract để hành vi của agent phù hợp hơn với mục tiêu của platform.

Bài học cho đề án rủi ro giao dịch là: hệ thống fintech cũng có cấu trúc tương tự.

- Platform/bank đóng vai trò principal, muốn giảm rủi ro và tối ưu chi phí.
- Analyst, customer và risky actor là các tác nhân có hành vi riêng.
- Policy ra quyết định là một dạng mechanism/contract mềm, quy định cách hệ thống phản ứng với từng tín hiệu rủi ro.
- Nếu policy thiết kế chưa tốt, outcome chung có thể xấu dù risk score có vẻ hợp lý.

Ví dụ, nếu chỉ khuyến khích recall, hệ thống có thể tạo quá nhiều alert. Nếu chỉ giảm workload, hệ thống có thể bỏ sót nhiều rủi ro. Thiết kế cơ chế phải phản ánh mục tiêu tổng thể, không tối ưu một chỉ số đơn lẻ.

### 8.2. Microstructure và tư duy cấp vi mô

Market microstructure nghiên cứu cách các quyết định nhỏ ở cấp giao dịch, quote, order flow hoặc fee tạo ra kết quả chung như liquidity, spread, execution cost và market impact. Đây là tư duy rất gần với đề án: trong transaction risk, mỗi quyết định approve/review/escalate ở cấp giao dịch có thể tạo ra outcome chung như backlog, loss, false positive và customer friction.

Điểm tương đồng nằm ở cách nhìn hệ thống:

- Không chỉ nhìn dữ liệu lịch sử tĩnh.
- Không giả định môi trường không phản ứng.
- Quan tâm đến cơ chế, incentive và chi phí sau quyết định.
- Dùng mô phỏng để kiểm tra policy trước khi áp dụng thật.

### 8.3. Regulation và policy testing

Trong tài liệu Quant Finance, regulation không chỉ là quy định bên ngoài, mà còn là thiết kế điều kiện để các tác nhân thị trường hành xử theo hướng tốt hơn cho hệ thống. Với đề án này, policy risk decisioning cũng đóng vai trò tương tự: nó điều tiết luồng giao dịch và luồng review.

Do đó, đề án có thể viết rằng mục tiêu không phải “tạo synthetic data để model chạy tốt”, mà là xây dựng một môi trường thử nghiệm chính sách, nơi người nghiên cứu có thể kiểm tra tác động của threshold, analyst capacity, false positive cost và AI support trước khi triển khai.

---

## 9. Human-in-the-loop và AI explanation trong cơ chế ra quyết định

Trong bài toán tài chính rủi ro, quyết định cuối cùng thường không nên giao hoàn toàn cho mô hình. Risk score có thể sai, dữ liệu có thể thiếu, và quyết định block/reject có thể ảnh hưởng trực tiếp đến khách hàng. Vì vậy, human-in-the-loop là một thành phần quan trọng.

Trong đề án, analyst không chỉ là người xem dashboard. Analyst là một tác nhân trong cơ chế:

- Có năng lực xử lý hữu hạn.
- Có thời gian review khác nhau theo độ khó case.
- Có thể được hỗ trợ bởi AI explanation/report.
- Có thể tạo feedback để cải thiện policy sau này.

AI explanation nên được hiểu là công cụ hỗ trợ analyst, không phải công cụ ra quyết định cuối cùng. Giá trị của AI explanation cần được đo bằng tác động vận hành:

- Có giảm review time không?
- Có giúp analyst hiểu evidence nhanh hơn không?
- Có giảm sai sót review không?
- Chi phí token/latency có hợp lý không?
- Có tạo audit trail tốt hơn không?

Điểm này giúp đề án kết nối AI với KPI nghiệp vụ, thay vì chỉ nói AI trả lời hay hơn.

---

## 10. Khung lý thuyết tổng hợp cho đề án

Từ các nền tảng trên, có thể xây dựng framework nghiên cứu như sau:

### 10.1. Input layer

- Dữ liệu giao dịch mô phỏng.
- Hồ sơ hành vi khách hàng.
- Tín hiệu rủi ro như amount anomaly, velocity, time signal, merchant risk.
- Giả định chi phí và năng lực vận hành.

### 10.2. Agent layer

- Normal customer.
- Risky/fraud behavior actor.
- Risk scoring system.
- Policy maker.
- Analyst.
- Platform/bank.

### 10.3. Mechanism layer

- Risk threshold.
- Review/escalation policy.
- Case priority rule.
- Analyst capacity allocation.
- AI explanation support.

### 10.4. Outcome layer

- Precision/recall.
- Fraud loss prevented.
- Fraud loss realized.
- False positive cost.
- Analyst workload.
- Review overflow.
- Customer friction.
- AI cost.
- Simulated net benefit.

### 10.5. Evaluation layer

- Scenario comparison.
- Policy comparison.
- Sensitivity analysis.
- Interpretation of trade-off.
- Limitation and robustness discussion.

Framework này nối trực tiếp ba ý chính cô gợi ý: Game Theory/Mechanism Design, Agent-Based Modeling và mô phỏng theo outcome/KPI chứ không chỉ mô phỏng dữ liệu.

---

## 11. Cách đưa phần lý thuyết này vào báo cáo

Trong báo cáo đề án, phần cơ sở lý thuyết nên được viết theo thứ tự sau:

1. **Transaction risk decisioning**
   - Giải thích bài toán risk score -> decision policy -> analyst review -> outcome.

2. **Agent-Based Modeling**
   - Trình bày agent, interaction, emergence, simulation, sensitivity analysis.
   - Dẫn Janssen làm nền tảng chính.

3. **Game Theory và Mechanism Design**
   - Giải thích vì sao nhiều tác nhân có mục tiêu khác nhau.
   - Chuyển từ dự báo sang thiết kế luật ra quyết định.

4. **Microstructure và Principal-Agent trong tài chính định lượng**
   - Dẫn Baldacci để lấy tư duy incentive, regulation và thiết kế cơ chế ở cấp vi mô.
   - Không cần đi sâu công thức HJB/PDE/optimal control vì vượt phạm vi đề án.

5. **Human-in-the-loop và AI explanation**
   - Đặt AI Agent vào vai trò hỗ trợ review, không thay analyst.

6. **Khoảng trống nghiên cứu**
   - Nhiều nghiên cứu tập trung vào model metric; đề án tập trung vào policy/outcome metric.

---

## 12. Đoạn viết mẫu có thể đưa vào báo cáo

Trong các hệ thống giao dịch số, rủi ro không chỉ xuất hiện từ đặc điểm riêng lẻ của từng giao dịch, mà còn từ tương tác giữa khách hàng, tác nhân rủi ro, hệ thống chấm điểm, chính sách xử lý và năng lực vận hành của analyst. Vì vậy, việc đánh giá một mô hình phát hiện gian lận chỉ bằng precision, recall hoặc ROC-AUC là chưa đủ để phản ánh hiệu quả nghiệp vụ cuối cùng. Một policy có recall cao có thể tạo ra quá nhiều false positive, làm tăng chi phí review và customer friction; ngược lại, một policy quá lỏng có thể giảm workload nhưng làm tăng tổn thất do bỏ sót rủi ro.

Dựa trên nền tảng Agent-Based Modeling, đề án xem hệ thống ra quyết định rủi ro như một hệ phức hợp thích nghi, trong đó nhiều tác nhân có hành vi riêng và outcome tổng thể xuất hiện từ tương tác giữa các tác nhân. Cách tiếp cận này phù hợp với quan điểm của Janssen rằng mô hình là công cụ để khám phá hệ quả của các quy tắc hành vi khác nhau, thay vì là bản sao hoàn chỉnh của thực tế. Trong bối cảnh này, dữ liệu synthetic không được tạo chỉ để huấn luyện mô hình, mà được sinh ra từ một cơ chế gồm khách hàng, giao dịch, risk scoring, policy decision và analyst review.

Bên cạnh đó, đề án sử dụng tư duy Mechanism Design để đặt câu hỏi ngược lại: nếu mục tiêu của nền tảng là giảm tổn thất, kiểm soát false positive, tránh quá tải analyst và duy trì trải nghiệm khách hàng, thì cần thiết kế cơ chế ra quyết định như thế nào? Góc nhìn này gần với các bài toán incentive design và regulation trong market microstructure, nơi platform không chỉ quan sát hành vi của agent mà còn thiết kế luật và incentive để hướng hệ thống đến outcome mong muốn. Vì vậy, trọng tâm của đề án không phải là xây dựng mô hình fraud detection tối ưu nhất, mà là mô phỏng và so sánh các policy ra quyết định dưới nhiều giả định về rủi ro, chi phí và năng lực vận hành.

---

## 13. Giới hạn lý thuyết cần nêu trung thực

Đề án cần nói rõ các giới hạn sau:

1. Dữ liệu là synthetic, được hiệu chỉnh bằng nguồn tham khảo công khai, không đại diện trực tiếp cho dữ liệu ngân hàng thật.
2. Risk score hiện tại là proxy/rule-based simulation, chưa phải model ML production-ready.
3. Các chi phí như false positive cost, analyst cost, recovery rate là giả định để mô phỏng policy, không phải số liệu tài chính thật.
4. Fraud actor adaptation mới ở mức đơn giản, chưa mô phỏng chiến lược đối kháng phức tạp.
5. AI explanation mới được đưa vào như một thành phần cơ chế, chưa có user study thực tế để đo review time thật.

Các giới hạn này không làm đề án yếu đi. Ngược lại, nếu viết rõ, đề án sẽ chặt hơn vì cho thấy người nghiên cứu hiểu phạm vi của mô phỏng.

---

## 14. Tài liệu tham khảo chính

- Janssen, M. A. (2020). *Introduction to Agent-Based Modeling: with applications to social, ecological, and social-ecological systems*.
- Baldacci, B. (2021). *Quantitative finance at the microstructure scale: algorithmic trading and regulation*. Institut Polytechnique de Paris.
- PaySim: public mobile money transaction simulator literature and dataset, used as methodological support for synthetic transaction simulation.
- BankSim: bank payment simulation dataset, used as reference for agent-based transaction behavior.
- ULB Credit Card Fraud Detection dataset, used as reference for class imbalance and transaction amount distribution.

---

## 15. Kết luận của phần lý thuyết

Hai tài liệu cô gửi giúp định hình lại đề án theo hướng sâu hơn. Tài liệu ABM cung cấp nền tảng để mô phỏng hệ thống như một tập hợp tác nhân tương tác, còn tài liệu Quant Finance/Microstructure gợi ý cách nhìn các quyết định tài chính ở cấp vi mô như một bài toán thiết kế cơ chế và incentive. Kết hợp hai hướng này, đề án có thể tránh việc chỉ là một project fraud detection thông thường, mà trở thành một nghiên cứu mô phỏng cơ chế ra quyết định rủi ro trong fintech.

---

## 15. Bổ sung game-theoretic framing cho mô hình đề án

Để làm rõ hơn vai trò của Game Theory, có thể xem hệ thống ra quyết định rủi ro như một trò chơi không đối xứng thông tin giữa platform và tác nhân rủi ro. Platform không biết chắc một giao dịch có phải gian lận hay không, chỉ quan sát các tín hiệu như amount, timing, velocity, merchant risk và lịch sử gần đây. Tác nhân rủi ro lại có incentive làm cho giao dịch của mình giống hành vi bình thường để tránh review.

Trong trò chơi đơn giản này, platform chọn policy như lenient, balanced, strict hoặc capacity-aware. Risky actor chọn chiến lược như high-amount attack, transaction splitting, burst velocity hoặc normal-like behavior. Analyst capacity là ràng buộc vận hành làm payoff của platform thay đổi: một policy tạo quá nhiều alert có thể tốt về recall nhưng kém về utility nếu analyst queue bị quá tải.

Payoff của platform được đại diện bằng simulated net benefit, còn payoff của risky actor gắn với xác suất giao dịch vượt qua hệ thống. Cách đặt bài toán này giúp đề án đi đúng tinh thần Mechanism Design: thay vì chỉ hỏi model dự báo tốt đến đâu, đề án hỏi cơ chế nào khiến hệ thống đạt outcome tốt hơn khi các tác nhân có thể phản ứng chiến lược.
