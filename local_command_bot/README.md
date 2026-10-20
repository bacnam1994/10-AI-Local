# LOCAL COMMAND BOT — STREAMLINED AI DOCUMENT ORCHESTRATOR

![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=flat&logo=windows)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python)
![PySide6](https://img.shields.io/badge/UI-PySide6%20Qt6-41CD52?style=flat&logo=qt)
![Status](https://img.shields.io/badge/Status-Streamlined%20Beta-blue)
![Tests](https://img.shields.io/badge/Tests-44%20Passed%20%7C%204%20Optional%20Skipped-brightgreen)

> **Bot Chỉ huy Local (Kiến trúc Tinh gọn)**: Phân tích yêu cầu, lập kế hoạch đồ thị (DAG) qua Local AI (Ollama `llama3.1`), soạn thảo nội dung chuyên sâu qua Cloud AI Gateway (OmniRoute `auto`), kiểm tra chất lượng bằng mã nguồn (Code-First Validator) trước khi sửa mục tiêu, và xuất bản tài liệu chuẩn DOCX/SOP.

---

## 🌟 KIẾN TRÚC ĐÍCH & TÍNH NĂNG CỐT LÕI

1. **Luồng Tinh gọn Mặc định (Streamlined Pipeline)**:
   - **Local AI (Ollama)**: Phân tích prompt tự nhiên, thiết kế đồ thị DAG vừa đủ, giữ vai trò tổng chỉ huy và kiểm định.
   - **Cloud AI (OmniRoute)**: Soạn thảo văn bản chuyên sâu song song qua giao thức tương thích OpenAI chuẩn.
   - **Code-First QA**: Kiểm định cấu trúc, mục thiếu, placeholder bằng code trước; chỉ gọi AI sửa khi thực sự phát hiện lỗi ngữ nghĩa, tối ưu chi phí và thời gian.

2. **Xác minh Pháp quy Trung thực (Regulatory Verification)**:
   - Danh mục quy chuẩn GMP Việt Nam (Thông tư 35/2018/TT-BYT, DĐVN V,...) được đối chiếu như danh mục gợi ý chuẩn.
   - Không tự động gán dấu thời gian giả lập `verified_at` khi chưa tra cứu trực tuyến hoặc được chuyên viên phê duyệt.
   - Minh bạch trạng thái: `Đối chiếu danh mục chuẩn (Cần kiểm tra hiệu lực thực tế)` vs `Chưa xác minh — cần tra cứu thủ công`.

3. **Orchestrator & DAG Scheduler Độc lập**:
   - Tách biệt rõ 4 giai đoạn nghiệp vụ: Lập kế hoạch (Planning) ➔ Tra cứu (Research) ➔ Chạy DAG (Execution) ➔ Tổng hợp & Xuất bản (Synthesis).
   - Concurrency pool có giới hạn, hỗ trợ Exponential Backoff Retry với Jitter.
   - Trần ngân sách (Budget Cap) và cơ chế ngắt an toàn khi vượt ngưỡng.

4. **Tạo Tài liệu Chuyên nghiệp (Document Engine)**:
   - **DOCX (Ưu tiên chính)**: Trang bìa, mã tài liệu, phiên bản, Bảng lịch sử sửa đổi, Bảng quy chuẩn tham chiếu, mục lục tự động, header/footer, đánh số trang.
   - Tuân thủ tiêu chuẩn SOP Dược phẩm GMP: Tự động đóng dấu `DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT`.

5. **Độ tin cậy & An toàn Dữ liệu**:
   - Lưu trạng thái từng bước vào cơ sở dữ liệu **SQLite (WAL mode)**.
   - **Crash Recovery**: Tự động khôi phục công việc nếu mất điện hoặc tắt ứng dụng đột ngột.
   - **Bảo mật**: API Key lưu qua Windows Credential Manager (Keyring), chống lộ key trong log bằng bộ lọc regex, chống tấn công Path Traversal, không ghi đè tệp cũ khi chưa được phép.

6. **Giao diện Desktop PySide6 Đẳng cấp**:
   - Thiết kế Dark Mode chuyên nghiệp, bảng màu HSL hiện đại.
   - Kiến trúc bất đồng bộ không chặn UI thread (60fps responsive).
   - Theo dõi tiến độ DAG theo thời gian thực và xem live console logs.

---

## 🚀 KHỞI ĐỘNG NHANH

### 1. Chạy ngay bằng script có sẵn
Click đúp vào:
```cmd
run_app.bat
```
hoặc chạy bằng PowerShell:
```powershell
.\run_app.ps1
```

### 2. Chạy qua Python Virtual Environment
```powershell
d:\10 AI Local\.venv\Scripts\python.exe -m app.main
```

---

## 📁 CẤU TRÚC DỰ ÁN

```text
local_command_bot/
├── app/
│   ├── main.py                  # Entry point ứng dụng
│   ├── ui/                      # Giao diện PySide6
│   │   ├── main_window.py       # Cửa sổ chính, luồng worker bất đồng bộ
│   │   ├── theme.py             # Dark mode theme & style tokens
│   │   └── components/          # Task table, log viewer, config dialog
│   ├── core/                    # Bộ não điều phối
│   │   ├── models.py            # Pydantic schemas (Job, Task, Plan, Review)
│   │   ├── state_store.py       # SQLite persistence & Crash Recovery
│   │   ├── scheduler.py         # DAG topological resolver & concurrency pool
│   │   ├── planner.py           # Phân tích prompt & lập kế hoạch JobPlan
│   │   ├── writer.py            # Chuyên viên soạn thảo
│   │   ├── reviewer.py          # Kiểm định chất lượng & vòng lặp sửa
│   │   ├── orchestrator.py      # Điều phối toàn bộ luồng công việc
│   │   └── job_manager.py       # Quản lý vòng đời và sự kiện
│   ├── providers/               # Multi-Cloud AI Adapters
│   │   ├── base.py              # BaseProviderAdapter interface
│   │   ├── openai_adapter.py    # OpenAI REST client
│   │   ├── anthropic_adapter.py # Anthropic REST client
│   │   ├── gemini_adapter.py    # Google Gemini REST client
│   │   └── mock_adapter.py      # Mock adapter dành cho tests & dry-run
│   ├── research/                # Tra cứu quy chuẩn pháp quy VN & GMP
│   ├── document/                # Xuất bản tài liệu (DOCX, PDF, Markdown)
│   ├── security/                # Keyring manager & Log/Path Sanitizer
│   └── config/                  # Settings, đường dẫn, bảng giá token
├── docs/                        # Tài liệu hướng dẫn & kiến trúc
│   ├── ARCHITECTURE.md          # Tài liệu kiến trúc phân tầng
│   ├── USER_GUIDE.md            # Hướng dẫn sử dụng & tạo Job đầu tiên
│   ├── INSTALLATION_GUIDE.md    # Hướng dẫn cài đặt chi tiết
│   ├── API_CONFIG_GUIDE.md      # Hướng dẫn cấu hình API key
│   ├── TEST_RESULTS.md          # Báo cáo kết quả kiểm thử 32 tests
│   ├── PROVIDER_CONFIG_EXAMPLE.md # Ví dụ phân bổ model theo vai trò
│   ├── LIMITATIONS.md           # Danh sách giới hạn còn tồn tại
│   └── PACKAGING_GUIDE.md       # Hướng dẫn đóng gói exe Windows
├── outputs/                     # Thư mục đầu ra của tài liệu
│   └── sample_sop_gmp/          # Mẫu SOP hoàn chỉnh tạo từ dữ liệu thử nghiệm
├── prompts/                     # Prompt hệ thống cho Planner, Writer, Reviewer
├── templates/                   # Template cấu trúc SOP GMP
├── tests/                       # 20 bộ test bắt buộc (32 test cases)
├── pyproject.toml
├── requirements.txt
├── run_app.bat
├── run_app.ps1
└── README.md
```

---

## 🧪 HỆ THỐNG KIỂM THỬ 3 TẦNG (TESTING FRAMEWORK)

Ứng dụng áp dụng tiêu chí đánh giá nghiêm ngặt theo 3 tầng kiểm thử:

1. **Tầng 1 — Unit Tests (Kiểm thử chức năng nội bộ & An toàn)**:
   - Bao quát toàn bộ: Lập kế hoạch DAG, concurrency, retry exponential backoff, ngắt an toàn budget, crash recovery SQLite, bộ lọc chống lộ secret trong log, chống path traversal, không ghi đè file, và kiểm tra pháp quy trung thực.
2. **Tầng 2 — Integration Tests (Kiểm thử tích hợp dịch vụ thật Ollama & OmniRoute)**:
   - File: `tests/test_real_api_optional.py`.
   - Tự động phát hiện dịch vụ live: kiểm tra kết nối tới Ollama (`http://localhost:11434`) và OmniRoute Gateway (`http://localhost:20128`).
   - Tự động bỏ qua an toàn (skip) khi môi trường offline để đảm bảo CI/CD và bộ unit test không bị nghẽn.
3. **Tầng 3 — End-to-End Tests (Quy trình hoàn chỉnh)**:
   - Kiểm thử tạo tài liệu thực tế với văn bản dài, tổng hợp và xuất bản DOCX chuẩn, xác thực format và bảng kiểm định.

### Lệnh chạy kiểm thử:
```powershell
d:\10 AI Local\.venv\Scripts\python.exe -m pytest -v
```
*(Kết quả mặc định khi offline/mock: 44 PASSED, 4 SKIPPED, 0 FAILED).*

---

## 📄 GIẤY PHÉP & BẢN QUYỀN
Phát triển bởi Đội ngũ Kỹ thuật Chuyên môn Cao cấp — Dự án Local Command Bot.
Mọi tài liệu tạo ra mặc định mang trạng thái **DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT**.
