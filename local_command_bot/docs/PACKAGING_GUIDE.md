# HƯỚNG DẪN ĐÓNG GÓI VÀ CHẠY TRÊN WINDOWS
## PyInstaller Windows Executable Packaging Guide

---

## 1. MỤC TIÊU ĐÓNG GÓI

Đóng gói toàn bộ ứng dụng **Local Command Bot** thành thư mục chạy độc lập (`dist/LocalCommandBot/`), cho phép người dùng mở ứng dụng bằng cách click đúp vào file `LocalCommandBot.exe` mà không cần cài đặt Python hay môi trường ảo.

---

## 2. QUY TRÌNH ĐÓNG GÓI BẰNG PYINSTALLER

### Cách 1: Sử dụng tệp thực thi nhanh
Tại thư mục `local_command_bot/`, chạy:
```cmd
build_package.bat
```

### Cách 2: Chạy thông qua script Python
Trong môi trường ảo `.venv`:
```powershell
python build_package.py
```

### Cách 3: Lệnh trực tiếp bằng PyInstaller
```powershell
pyinstaller --noconfirm --onedir --windowed `
  --name "LocalCommandBot" `
  --add-data "prompts;prompts" `
  --add-data "templates;templates" `
  --hidden-import "pyside6" `
  --hidden-import "httpx" `
  --hidden-import "reportlab" `
  --hidden-import "docx" `
  --hidden-import "keyring" `
  --hidden-import "keyring.backends" `
  --hidden-import "keyring.backends.Windows" `
  app/main.py
```

---

## 3. CẤU TRÚC KẾT QUẢ ĐẦU RA

Sau khi đóng gói thành công, thư mục phân phối sẽ có cấu trúc:

```text
local_command_bot/
    dist/
        LocalCommandBot/
            LocalCommandBot.exe   <-- File thực thi chính
            prompts/              <-- Các tệp Prompt hệ thống
            templates/            <-- Các tệp mẫu SOP
            _internal/            <-- Thư viện Python, DLL Qt6, C-extensions
```

---

## 4. PHÂN PHỐI VÀ CHẠY ỨNG DỤNG TRÊN MÁY KHÁCH

1. Nén toàn bộ thư mục `dist/LocalCommandBot` thành file ZIP: `LocalCommandBot_v1.0.0_win64.zip`.
2. Chuyển sang máy trạm Windows của người dùng cuối.
3. Giải nén và click đúp vào `LocalCommandBot.exe` để sử dụng ngay lập tức mà không cần bất kỳ bước cài đặt phức tạp nào.
