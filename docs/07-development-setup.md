# 07. Thiết lập môi trường phát triển cho đề án cá nhân

## 1. Thư mục dự án

Dự án đề án cá nhân này đã được tách khỏi codebase đã nộp cho chương trình trước đó.

Đường dẫn dự án:

```text
D:\Đề án\FinRisk-Decision-Simulation
```

Từ thời điểm này, nên dùng thư mục này cho toàn bộ phần nghiên cứu, mô phỏng và viết báo cáo đề án.

## 2. Môi trường Python

Dự án đã có virtual environment riêng nằm trong:

```text
.venv
```

Kích hoạt môi trường trong PowerShell:

```powershell
cd "D:\Đề án\FinRisk-Decision-Simulation"
.\.venv\Scripts\Activate.ps1
```

Kiểm tra phiên bản Python:

```powershell
python --version
```

Phiên bản kỳ vọng hiện tại:

```text
Python 3.11.x
```

## 3. Thư viện phục vụ mô phỏng

Các thư viện tối thiểu cho profiling và simulation được lưu trong:

```text
requirements-simulation.txt
```

Cài đặt hoặc cài lại:

```powershell
python -m pip install --only-binary=:all: -r requirements-simulation.txt
```

Các package chính hiện tại:

- `pandas`
- `numpy`

## 4. Dữ liệu tham chiếu công khai

Các bộ dữ liệu public dùng để tham khảo phân phối được lưu local tại:

```text
data/reference/raw/
```

Các file kỳ vọng:

```text
data/reference/raw/ulb_creditcard/creditcard.csv
data/reference/raw/banksim/bs140513_032310.csv
data/reference/raw/paysim/PS_20174392719_1491204439457_log.csv
```

Dữ liệu raw đang được ignore bởi Git và không nên commit lên repository.

## 5. Profiling dữ liệu tham chiếu

Ví dụ chạy profiling:

```powershell
python tools/profile_reference_datasets.py --input data/reference/raw/ulb_creditcard/creditcard.csv --name ulb_creditcard --output-dir data/reference/profiles
python tools/profile_reference_datasets.py --input data/reference/raw/banksim/bs140513_032310.csv --name banksim --output-dir data/reference/profiles
python tools/profile_reference_datasets.py --input data/reference/raw/paysim/PS_20174392719_1491204439457_log.csv --name paysim --output-dir data/reference/profiles
```

Output profiling nằm trong:

```text
data/reference/profiles/
```

Các kết quả profiling được dùng để viết giả định hiệu chỉnh trong:

```text
docs/06-calibration-assumptions.md
```

## 6. An toàn Git

File `.gitignore` hiện loại trừ các thành phần local và dữ liệu nặng:

- `.venv/`
- `data/`
- `logs/`
- `node_modules/`
- build/cache outputs
- `.env` files

Điều này giúp tránh commit nhầm raw data, secret key hoặc môi trường local.

## 7. Các script chính của phần mô phỏng

Các script đã có:

```text
scripts/generate_simulation_data.py
scripts/run_simulation_scenarios.py
scripts/compare_decision_policies.py
scripts/build_analysis_report.py
```

Ý nghĩa ngắn gọn:

- `generate_simulation_data.py`: sinh dữ liệu giao dịch mô phỏng và risk score.
- `run_simulation_scenarios.py`: chạy nhiều scenario để so sánh fraud pressure và analyst capacity.
- `compare_decision_policies.py`: so sánh nhiều policy decisioning trên cùng một baseline.
- `build_analysis_report.py`: tạo báo cáo Markdown/HTML từ kết quả mô phỏng.

## 8. Bước phát triển tiếp theo

Bước tiếp theo nên là chuyển các notes và kết quả mô phỏng thành báo cáo đề án hoàn chỉnh, gồm phần lý thuyết, phương pháp, kết quả mô phỏng, thảo luận và hạn chế.
