# DANH SÁCH GIỚI HẠN CÒN TỒN TẠI (SYSTEM LIMITATIONS)

Dưới đây là các giới hạn kỹ thuật và phạm vi hiện tại của ứng dụng nhằm đảm bảo tính minh bạch và kỳ vọng vận hành:

1. **Tính chất Pháp lý của Tài liệu Tạo ra**:
   - Mọi tài liệu SOP, quy chuẩn kỹ thuật xuất ra đều mang trạng thái bắt buộc: **`DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT`**.
   - Ứng dụng **không** thay thế vai trò thẩm định, ký duyệt của Dược sĩ phụ trách chuyên môn, Trưởng phòng Đảm bảo Chất lượng (QA) hoặc Cơ quan Quản lý Dược có thẩm quyền.

2. **Cập nhật Mục lục trong Word (TOC Auto-Update)**:
   - File `.docx` được tạo bằng mã trường Word TOC chuẩn (`{ TOC \o "1-3" \h \z \u }`).
   - Khi mở bằng Microsoft Word lần đầu, người dùng cần bấm chuột phải vào mục lục và chọn **"Update Field" (hoặc phím tắt F9)** để Word tính toán số trang thực tế của bản in và hiển thị danh sách trang.

3. **Xuất PDF qua ReportLab**:
   - Bộ xuất PDF sử dụng thư viện chuẩn `reportlab` hỗ trợ đầy đủ tiếng Việt không dấu và ký tự Latin chuẩn. Với các văn bản tiếng Việt có dấu phức tạp trên PDF thuần ReportLab, nếu môi trường chưa nạp font TrueType Unicode hệ thống (`Arial.ttf`/`DejaVuSans.ttf`), tệp DOCX xuất kèm theo luôn là nguồn tham chiếu chuẩn xác nhất.

4. **Phụ thuộc Hạn ngạch (Quota & Rate Limit) của Nhà cung cấp**:
   - Khi tài khoản người dùng hết tiền hoặc bị khóa quyền truy cập API từ phía OpenAI/Anthropic/Google, ứng dụng sẽ dừng có kiểm soát và báo lỗi rõ ràng; không thể tự động vượt qua giới hạn tài khoản của nhà cung cấp.

5. **Hỗ trợ Hệ điều hành**:
   - Ứng dụng được thiết kế và kiểm thử chuyên sâu cho môi trường **Windows 10 / Windows 11 (64-bit)** với Windows Credential Manager. Việc chuyển đổi sang macOS hoặc Linux sẽ yêu cầu cấu hình thêm thư viện SecretService của hệ điều hành đó.
