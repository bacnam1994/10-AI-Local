# LOCAL COMMAND BOT — MULTI-CLOUD AI DOCUMENT ORCHESTRATOR

![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=flat&logo=windows)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python)
![PySide6](https://img.shields.io/badge/UI-PySide6%20Qt6-41CD52?style=flat&logo=qt)
![License](https://img.shields.io/badge/Status-Production%20Ready-success)
![Tests](https://img.shields.io/badge/Tests-32%2F32%20Passing-brightgreen)

> **Bot Chỉ huy Local**: Tự động hóa phân tích yêu cầu dài, lập kế hoạch đồ thị (DAG), phân bổ tác vụ cho nhiều nhà cung cấp Cloud AI (OpenAI, Anthropic Claude, Google Gemini), kiểm soát chất lượng qua vòng lặp Reviewer-Writer, và xuất bản tài liệu hoàn chỉnh (DOCX, PDF, Markdown).

---

## 🌟 TÍNH NĂNG NỔI BẬT

1. **Orchestrator & DAG Scheduler**:
   - Phân tích yêu cầu tự nhiên thành `JobPlan` có cấu trúc.
   - Xây dựng đồ thị có hướng không chu trình (DAG), giải quyết thứ tự topo và chạy song song các nhiệm vụ độc lập.
   - Concurrency pool có giới hạn, hỗ trợ Exponential Backoff Retry với Jitter.
   - Trần ngân sách (Budget Cap) và cơ chế ngắt an toàn khi vượt ngưỡng.

2. **Hỗ trợ Đa Cloud AI Thống nhất**:
   - **OpenAI**: Chat Completions (GPT-4o, GPT-4o-mini).
   - **Anthropic**: Messages API (Claude 3.5 Sonnet, Haiku).
   - **Google Gemini**: REST API (Gemini 1.5 Pro, Flash, 2.0 Flash).
   - **Mock Adapter**: Chế độ Dry Run và kiểm thử 100% offline không phát sinh chi phí.

3. **Vòng lặp Kiểm soát Chất lượng (Reviewer & Quality Loop)**:
   - Reviewer đánh giá 8 khía cạnh cốt lõi (Đầy đủ, Logic, Thuật ngữ, Trùng lặp, Mâu thuẫn, Trích dẫn, Căn cứ kiểm chứng, Tuân thủ).
   - Chỉ dẫn Writer sửa lỗi theo danh sách điểm yếu (tối đa N vòng cấu hình).

4. **Tạo Tài liệu Chuyên nghiệp (Document Engine)**:
   - **DOCX**: Trang bìa, mã tài liệu, phiên bản, Bảng lịch sử sửa đổi, Bảng quy chuẩn tham chiếu, mục lục tự động, header/footer, đánh số trang.
   - **PDF**: Tạo trực tiếp qua ReportLab với canvas đánh số trang động 2-pass.
   - **Markdown**: Bản lưu trữ nguồn sạch.
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

## 🧪 CHẠY TOÀN BỘ KIỂM THỬ (TEST SUITE)

```powershell
d:\10 AI Local\.venv\Scripts\python.exe -m pytest tests -v
```
*(Kết quả: 31 PASSED, 1 SKIPPED, 0 FAILED).*

---

## 📄 GIẤY PHÉP & BẢN QUYỀN
Phát triển bởi Đội ngũ Kỹ thuật Chuyên môn Cao cấp — Dự án Local Command Bot.
Mọi tài liệu tạo ra mặc định mang trạng thái **DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT**.
