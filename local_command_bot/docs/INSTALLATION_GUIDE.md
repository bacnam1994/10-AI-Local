# HƯỚNG DẪN CÀI ĐẶT: LOCAL COMMAND BOT

---

## 1. YÊU CẦU MÔI TRƯỜNG

- **Hệ điều hành**: Windows 10 hoặc Windows 11 (64-bit).
- **Python**: Phiên bản 3.10 trở lên (Khuyến nghị **Python 3.11**).
- **Bộ nhớ RAM**: Tối thiểu 4GB RAM (Khuyến nghị 8GB RAM).
- **Dung lượng ổ đĩa**: Tối thiểu 500MB trống cho môi trường và thư viện.

---

## 2. QUY TRÌNH CÀI ĐẶT CHI TIẾT

### Bước 1: Chuẩn bị môi trường Python ảo (.venv)
Mở cửa sổ PowerShell tại thư mục dự án `d:\10 AI Local`:

```powershell
# Tạo môi trường ảo với Python 3.11
python -m venv .venv

# Hoặc nếu sử dụng uv (công cụ tốc độ cao):
uv venv .venv --python 3.11
```

### Bước 2: Kích hoạt môi trường ảo
```powershell
.\.venv\Scripts\Activate.ps1
```

*(Nếu gặp lỗi PowerShell ExecutionPolicy, mở PowerShell dưới quyền quản trị và chạy: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

### Bước 3: Cài đặt các thư viện phụ thuộc
Di chuyển vào thư mục `local_command_bot/` và cài đặt:

```powershell
cd local_command_bot
pip install -r requirements.txt
```

Các thư viện chính được cài đặt:
- `PySide6`: Giao diện desktop Qt 6.
- `httpx`: Thư viện gọi API bất đồng bộ (Async HTTP).
- `pydantic`: Kiểm thực cấu trúc dữ liệu và schema JSON.
- `python-docx`: Sinh tệp tài liệu Microsoft Word (.docx).
- `reportlab`: Sinh tệp PDF chất lượng cao.
- `keyring`: Tích hợp Windows Credential Manager lưu trữ API key an toàn.
- `pytest` & `pytest-asyncio`: Bộ khung kiểm thử tự động.
- `pyinstaller`: Đóng gói ứng dụng thành file exe độc lập trên Windows.

---

## 3. KIỂM TRA CÀI ĐẶT

Chạy lệnh kiểm thử tự động để xác nhận toàn bộ thư viện hoạt động chuẩn xác:

```powershell
python -m pytest tests -v
```

Nếu toàn bộ các bài kiểm thử hiển thị `PASSED`, quá trình cài đặt đã hoàn tất thành công 100%.
