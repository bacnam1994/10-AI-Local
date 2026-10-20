# HƯỚNG DẪN CẤU HÌNH API KEY VÀ CÁC NHÀ CUNG CẤP AI

---

## 1. NGUYÊN TẮC BẢO MẬT API KEY

Ứng dụng **Local Command Bot** tuân thủ các tiêu chuẩn bảo mật nghiêm ngặt:
- **Lưu trữ mã hóa**: Sử dụng **Windows Credential Manager (Keyring)**.
- **Không lưu plain-text**: Không lưu mật khẩu hoặc API key dưới dạng văn bản thô trong file mã nguồn, file cấu hình không an toàn hay file cơ sở dữ liệu.
- **Khử khuẩn nhật ký (Log Sanitization)**: Mọi chuỗi ký tự khớp với mẫu API key (`sk-...`, `AIzaSy...`, `sk-ant-...`) đều tự động được che chắn (masking) thành `***[MASKED_KEY]***` trước khi ghi ra console hoặc file nhật ký `app.log`.

---

## 2. CÁC CÁCH CẤU HÌNH API KEY

### Cách 1: Cấu hình trực tiếp trên Giao diện Đồ họa (Khuyến nghị)
1. Mở ứng dụng **Local Command Bot**.
2. Nhấn nút **"⚙ Cấu hình API Key"** ở góc trên bên phải.
3. Nhập API Key tương ứng với nhà cung cấp bạn sở hữu:
   - **OpenAI API Key**: Bắt đầu bằng `sk-proj-...` hoặc `sk-...`
   - **Anthropic API Key**: Bắt đầu bằng `sk-ant-api03-...`
   - **Google Gemini API Key**: Bắt đầu bằng `AIzaSy...`
4. Bấm nút **"Kiểm tra"** bên cạnh để ứng dụng kiểm tra tính hợp lệ và kết nối mạng đến máy chủ nhà cung cấp.
5. Bấm **"Lưu cấu hình an toàn"** để lưu trực tiếp vào Windows Credential Manager.

---

### Cách 2: Cấu hình thông qua Biến môi trường (Environment Variables)
Nếu bạn chạy trên máy chủ tự động hoặc môi trường phát triển:

```powershell
# Thiết lập cho phiên làm việc hiện tại:
$env:OPENAI_API_KEY="sk-proj-your_actual_openai_key_here"
$env:ANTHROPIC_API_KEY="sk-ant-api03-your_actual_anthropic_key_here"
$env:GEMINI_API_KEY="AIzaSyYourActualGeminiKeyHere"

# Hoặc thiết lập vĩnh viễn cho User trên Windows:
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-...', 'User')
```

---

### Cách 3: Sử dụng tệp `.env` (Dành cho nhà phát triển)
1. Sao chép tệp `.env.example` thành `.env`:
   ```powershell
   cp .env.example .env
   ```
2. Mở tệp `.env` và điền khóa của bạn:
   ```env
   OPENAI_API_KEY=sk-proj-xxxx...
   ANTHROPIC_API_KEY=sk-ant-api03-xxxx...
   GEMINI_API_KEY=AIzaSyxxxx...
   ```
*(Lưu ý: Tệp `.env` đã được liệt kê trong `.gitignore` để ngăn chặn việc sơ ý commit lên Git repository).*

---

## 3. LƯU Ý VỀ TÀI KHOẢN VÀ HẠN MỨC (QUOTA)

- **Đăng ký Web != Truy cập API**: Việc đăng ký tài khoản ChatGPT Plus, Claude Pro hay Google One trên giao diện Web **không** đồng nghĩa với việc bạn có quyền gọi API trả phí. Bạn cần tạo tài khoản trên các cổng phát triển chính thức:
  - OpenAI Platform: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
  - Anthropic Console: [https://console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
  - Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- Khi tài khoản hết số dư hoặc chạm hạn mức RPM (Requests Per Minute), ứng dụng sẽ hiển thị cảnh báo lỗi cụ thể (429 Rate Limit / Quota Exceeded) mà không làm sập ứng dụng.
