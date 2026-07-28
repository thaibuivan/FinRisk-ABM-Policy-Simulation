# 11 - Hướng dẫn sử dụng analysis report

File này hướng dẫn cách sử dụng các output phân tích đã sinh từ simulation.

## Output chính

Báo cáo Markdown:

```text
reports/analysis/simulation_analysis_report_20260721_114711.md
```

Báo cáo HTML có biểu đồ:

```text
reports/analysis/simulation_analysis_report_20260721_114711.html
```

Mở file HTML bằng browser để xem các bar chart về scenario và policy.

## Dùng trong chương nào của đề án

Nên đưa các kết quả này vào chương **Kết quả mô phỏng và thảo luận**.

Cấu trúc gợi ý:

1. Scenario comparison: fraud pressure và analyst capacity ảnh hưởng đến net benefit như thế nào.
2. Policy comparison: với cùng risk score, các policy khác nhau tạo trade-off khác nhau.
3. Sensitivity/caveat: net benefit là utility mô phỏng, không phải lợi nhuận thực tế.

## Insight chính

- Low fraud scenario có net benefit âm vì false positive và analyst cost lớn hơn fraud loss prevented.
- Stress fraud scenario có net benefit cao hơn vì alert có xác suất hữu ích cao hơn.
- Low capacity scenario làm review overflow tăng và net benefit giảm.
- Khi capacity đủ, sensitive threshold có thể tốt hơn vì recall cao hơn.
- Khi capacity thấp, balanced threshold bền vững hơn vì tạo ít overflow hơn.

## Cách viết vào báo cáo

Có thể viết:

> Kết quả mô phỏng cho thấy hiệu quả của hệ thống transaction risk decisioning không chỉ phụ thuộc vào risk score, mà còn phụ thuộc vào fraud base rate, analyst capacity và cost assumptions. Trong môi trường fraud thấp, cơ chế review có thể tạo net benefit âm do false positive cost. Khi fraud pressure cao hơn, cùng một cơ chế có thể tạo lợi ích ròng lớn hơn. Khi analyst capacity bị giới hạn, policy nhạy hơn có thể tạo quá nhiều queue overflow và kém hiệu quả hơn policy cân bằng. Điều này ủng hộ cách tiếp cận mechanism design: thiết kế cơ chế ra quyết định phải tối ưu theo utility và ràng buộc vận hành, không chỉ theo accuracy của model.

## Lưu ý khi trình bày

Không nên nói các con số net benefit là tiền thật. Nên nói đây là **simulated utility under assumptions**. Mục đích là so sánh tương đối giữa các policy/scenario.

## Cách mở file HTML

Cách đơn giản nhất trong File Explorer:

1. Mở thư mục:

```text
D:\Đề án\FinRisk-Decision-Simulation\reports\analysis
```

2. Double-click file:

```text
simulation_analysis_report_20260721_114711.html
```

3. File sẽ mở bằng trình duyệt mặc định.

Hoặc mở bằng PowerShell:

```powershell
cd "D:\Đề án\FinRisk-Decision-Simulation"
start "" "reports\analysis\simulation_analysis_report_20260721_114711.html"
```
