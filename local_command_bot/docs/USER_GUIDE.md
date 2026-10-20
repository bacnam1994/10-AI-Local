# HƯỚNG DẪN SỬ DỤNG: LOCAL COMMAND BOT

---

## 1. KHỞI CHẠY ỨNG DỤNG

### Cách 1: Sử dụng tệp thực thi nhanh (.bat / .ps1)
- Double-click vào tệp `run_app.bat` trong thư mục `local_command_bot/`.
- Hoặc mở PowerShell tại thư mục này và chạy:
  ```powershell
  .\run_app.ps1
  ```

### Cách 2: Khởi chạy bằng lệnh Python trong môi trường ảo (.venv)
```powershell
d:\10 AI Local\.venv\Scripts\python.exe -m app.main
```

---

## 2. GIAO DIỆN CHÍNH VÀ CÁC THÀNH PHẦN

Giao diện ứng dụng được thiết kế tối ưu hoá cho desktop Windows theo ngôn ngữ thiết kế Dark Mode hiện đại:

1. **Thanh Header & Thống kê trên cùng**:
   - Hiển thị Trạng thái (SẴN SÀNG, ĐANG CHẠY, TẠM DỪNG, THÀNH CÔNG, THẤT BẠI).
   - Thống kê chi phí ước tính thời gian thực (`$ USD`).
   - Tổng số token tiêu thụ (`Total Tokens`).
   - Nút **"Cấu hình API Key"** mở hộp thoại quản lý khóa an toàn.

2. **Khung Nhập liệu bên trái (Input Panel)**:
   - **Mục 1 — Yêu cầu Văn bản (Prompt dài)**: Nơi nhập ngôn ngữ tự nhiên. Có sẵn nút `📋 Chèn Prompt SOP Mẫu` để thử nghiệm ngay lập tức.
   - **Mục 2 — Định dạng & Thư mục Đầu ra**: Chọn xuất file `DOCX (Word)`, `PDF`, `Markdown`. Cho phép chọn thư mục lưu kết quả trên ổ đĩa.
   - **Mục 3 — Thiết lập Cloud AI**: Lựa chọn nhà cung cấp chính (`OpenAI`, `Anthropic`, `Gemini`, `Mock`) và Model tương ứng. Có tùy chọn `Chế độ Dry Run` để chạy thử nghiệm không tốn tiền.
   - **Mục 4 — Giới hạn Ngân sách & Tiến trình**:
     - *Trần chi phí ($ USD)*: Tự động ngắt khi chạm ngưỡng (mặc định $5.00).
     - *Tác vụ song song*: Giới hạn concurrency pool (mặc định 3).
     - *Số lần thử lại (Retries)*: Số lần retry khi gặp sự cố mạng (mặc định 3).
     - *Timeout*: Thời gian chờ tối đa cho mỗi request HTTP.
   - **Bộ nút Điều khiển Thực thi**:
     - `▶ Bắt đầu (Start)`: Khởi chạy luồng lập kế hoạch và điều phối.
     - `⏸ Tạm dừng (Pause)`: Tạm dừng tác vụ an toàn.
     - `▶ Tiếp tục (Resume)`: Khôi phục luồng đang dừng.
     - `⏹ Hủy bỏ (Cancel)`: Hủy phiên làm việc.

3. **Khung Theo dõi bên phải (Monitoring Panel)**:
   - **Thanh Tiến độ (Progress Bar)**: Hiển thị phần trăm số nhiệm vụ đã hoàn thành.
   - **Tab "Đồ thị Nhiệm vụ (DAG Tasks)"**: Bảng chi tiết từng nhiệm vụ, vai trò (Planner, Researcher, Writer, Reviewer), model, huy hiệu trạng thái (Pending, Running, Succeeded, Retrying, Failed), số lần thử và chi phí từng task.
   - **Tab "Nhật ký Chi tiết (Console Logs)"**: Console log trực tiếp có timestamp, lọc theo cấp độ (INFO, WARN, ERROR) và tìm kiếm từ khóa.

4. **Thanh Thông báo Kết quả (Bottom Banner)**:
   - Khi hoàn tất, xuất hiện nút:
     - `📂 Mở Thư mục Kết quả`: Mở File Explorer trực tiếp tại vị trí lưu tệp.
     - `📄 Mở Tài liệu DOCX`: Mở file Word vừa tạo bằng ứng dụng mặc định.

---

## 3. HƯỚNG DẪN TẠO PHIÊN LÀM VIỆC ĐẦU TIÊN (FIRST JOB WALKTHROUGH)

### Bước 1: Thiết lập API Key (hoặc bật Dry Run)
- Nếu bạn có OpenAI/Anthropic/Gemini API Key: Nhấn nút **"⚙ Cấu hình API Key"** góc trên bên phải, nhập Key và nhấn **"Kiểm tra"** rồi nhấn **"Lưu cấu hình an toàn"**.
- Nếu bạn muốn chạy thử nghiệm ngay lập tức mà **chưa cần API Key**: Tích chọn vào ô **"Chế độ Dry Run (Chạy giả lập kiểm tra DAG, không tốn token)"**.

### Bước 2: Nhập yêu cầu văn bản
- Bấm vào nút `📋 Chèn Prompt SOP Mẫu` để tải prompt mẫu về SOP Vệ sinh phòng sạch Dược phẩm theo tiêu chuẩn GMP-WHO (Thông tư 35/2018/TT-BYT).

### Bước 3: Cấu hình đầu ra
- Đảm bảo các ô `DOCX`, `PDF`, `Markdown` được tích chọn.
- Thư mục đầu ra mặc định sẽ nằm tại `local_command_bot/outputs/`.

### Bước 4: Nhấn "▶ Bắt đầu (Start)"
- Hệ thống sẽ kích hoạt **Planner Engine**, tạo ra bản kế hoạch công việc `JobPlan` và chia nhỏ thành các nhiệm vụ phụ thuộc.
- Các nhiệm vụ độc lập sẽ chạy song song.
- Mỗi nhiệm vụ soạn thảo (Writer) sẽ được kiểm tra chất lượng bởi **Reviewer Engine**. Nếu chưa đạt, Reviewer sẽ yêu cầu Writer sửa lại (tối đa N vòng).
- Sau khi hoàn thành, hệ thống sẽ tự động ghép các phân đoạn, kiểm tra placeholder, thêm trang bìa, TOC, bảng sửa đổi, bảng quy chuẩn tham chiếu và xuất tệp.

### Bước 5: Xem và kiểm tra tài liệu
- Nhấn `📂 Mở Thư mục Kết quả` hoặc `📄 Mở Tài liệu DOCX` để đọc văn bản được tạo.
