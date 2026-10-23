# VIETLAB NEXUS V9.2 — Kiểm tra và tối ưu

## Kết luận
Bản hiện tại phù hợp để thử nghiệm nghiệp vụ cục bộ. Chưa đủ điều kiện vận hành LIMS nhiều người dùng hoặc dùng làm hồ sơ chính thức. Đợt này tập trung sửa luồng Method/chỉ tiêu; chưa kiểm thử thực nghiệm toàn bộ chu trình khách hàng → tiếp nhận → phân tích → trả kết quả.

## Đã sửa
- Dùng chung kiểm tra dữ liệu cho nhập tay, nhập CSV và phê duyệt Method: số hữu hạn không âm, LOQ ≥ MDL, LCS tối đa ≥ tối thiểu, thiết bị phải thuộc đúng phòng.
- Giữ giá trị 0 khi mở biểu mẫu sửa MDL, LOQ, LCS, RPD.
- Lưu nháp, phê duyệt, nhập CSV, tạo yêu cầu chỉ tiêu: khi ghi localStorage thất bại, hoàn tác thay đổi danh mục và nhật ký trong bộ nhớ; không báo thành công giả.
- CSV: tối đa 2000 dòng, từ chối toàn bộ nếu vượt giới hạn thay vì bỏ qua âm thầm; từ chối tiêu đề trùng; báo số dòng lỗi. Các dòng hợp lệ vẫn nhập được khi một số dòng khác lỗi.
- Kiểm tra trùng CSV bằng Set thay vì quét lại toàn bộ danh mục cho từng dòng; cập nhật trạng thái hàng chờ sau khi nhập liên kết.
- Bộ chọn hợp đồng ưu tiên bản ghi Method hiện hành trước danh mục demo cũ; lưu danh mục tạm trong một lần mở để giảm dựng lại khi tìm kiếm.
- Bỏ tải Google Fonts: giao diện dùng phông có sẵn khi chạy offline. Cập nhật tiêu đề phiên bản.

## Kiểm chứng
- 22 khẳng định hồi quy đạt: số không hợp lệ, giá trị 0, thứ tự MDL/LOQ, LCS, thiết bị, trùng Method, nhật ký, lỗi bộ nhớ lúc lưu/duyệt/nhập CSV, CSV quá giới hạn, CSV có dấu nháy.
- Ba khối JavaScript biên dịch thành công; app.py qua kiểm tra cú pháp Python.
- Chạy lại: `node tests/method-regression.cjs`.
- Chưa kiểm thử trình duyệt: Playwright có thư viện nhưng thiếu Chromium. Kiểm thử logic dùng các hàm thực trích từ HTML, với DOM/lưu trữ được giả lập; không thay thế kiểm thử giao diện.

## Các hạn chế còn lại
1. Quyền người dùng chỉ ở JavaScript, có thể đổi qua công cụ trình duyệt; không phải xác thực máy chủ. Cần backend có kiểm tra quyền cho từng thao tác trước vận hành thật.
2. localStorage không chia sẻ giữa máy, có thể bị xóa hoặc đầy; nhiều tab có thể ghi đè nhau. Chưa có khôi phục bản sao qua giao diện hay xử lý xung đột đồng thời.
3. Nhật ký ở phía khách không bất biến. Không thể coi dấu “phê duyệt” demo là chữ ký chính thức.
4. Mã nguồn HTML lớn, còn nhiều lớp chức năng V7–V10; renderAll dựng nhiều màn hình mỗi lần thay đổi. Nên tách mô-đun theo nghiệp vụ ở đợt sau cùng bộ kiểm thử trình duyệt.
5. Chưa kiểm toán đầy đủ tính toán kết quả, QC, phân quyền mọi luồng, xuất CoA/PDF và khả năng chống chèn nội dung trên toàn bộ ứng dụng.
6. Nhập danh mục hiện hỗ trợ CSV, không đọc trực tiếp XLSX. Không bổ sung hỗ trợ XLSX trong đợt sửa này.

## Kiểm tra thủ công trước dùng thử
- Sao lưu dữ liệu bằng chức năng xuất JSON của bản cũ trước khi thay thế.
- Mở HTML tại cùng vị trí/nguồn truy cập cũ nếu cần giữ localStorage. Khóa dữ liệu được giữ nguyên; việc chuyển tên/đường dẫn file có thể làm trình duyệt dùng vùng lưu khác.
- Tạo chỉ tiêu → liên kết Method → nhập đủ hồ sơ → duyệt → chọn nền mẫu tương ứng trong hợp đồng.
- Nhập CSV có dòng hợp lệ, trùng, sai số; so sánh số lượng và thông báo; tải lại trang để kiểm tra lưu.
- Thử bằng Admin, trưởng phòng, KCS và người khác phòng; kiểm tra trên điện thoại.
- Giả lập trọn luồng hợp đồng → nhận mẫu → lập mẻ → QC → KCS → trả kết quả trước khi quyết định bước nâng cấp tiếp theo.

Không triển khai lên Google hoặc dịch vụ web trong đợt này. Không thay đổi cơ chế lưu kết quả phân tích.
