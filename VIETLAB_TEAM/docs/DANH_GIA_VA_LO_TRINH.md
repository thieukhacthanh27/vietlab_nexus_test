# Đánh giá và hướng triển khai cho công ty môi trường

## Mục tiêu thiết kế và giới hạn
Lấy 30–100 tài khoản làm giả định thiết kế ban đầu do chưa có số nhân viên, số người dùng đồng thời, số mẫu/ngày, số chi nhánh và hạ tầng cụ thể. Đây không phải cam kết tải. Bản này tạo lõi máy chủ và giao diện mới cho thử nghiệm một luồng hoàn chỉnh; không tuyên bố đã chuyển hết hệ thống cũ.

VILAS áp dụng ISO/IEC 17025 để đánh giá năng lực phòng thử nghiệm/hiệu chuẩn. Phần mềm chỉ hỗ trợ kiểm soát hồ sơ và quy trình; không tự tạo ra sự công nhận hoặc thay thế phạm vi công nhận của công ty.
Nguồn chính thức: https://www.boa.gov.vn/vi/phong-thu-nghiem-va-phong-hieu-chuan-vilas (tham khảo 23/10/2026).

## Thay đổi nền tảng
| Nội dung | V9.2 offline | V10 Team Pilot |
|---|---|---|
| Dữ liệu | localStorage từng trình duyệt | DB máy chủ; PostgreSQL cho triển khai |
| Người dùng | Vai trò demo ở trình duyệt | Tài khoản + phiên đăng nhập + quyền API |
| Ghi đồng thời | Có thể ghi đè cả khối dữ liệu | Số phiên bản từng hồ sơ, báo xung đột |
| Method | Danh mục và trạng thái demo | Phiên bản, soạn/duyệt khác người, đúng nền trước phân công |
| Kết quả | Kết quả cục bộ | Kết quả cuối + QC khai báo + tham chiếu hồ sơ + nhật ký chỉnh sửa |
| Phát hành | Luồng demo cũ | Phiếu nội bộ chụp dữ liệu, khóa sửa sau phát hành |
| Nhật ký | Người dùng có thể sửa localStorage | Máy chủ ghi cùng giao dịch; cấu hình quyền DB hạn chế sửa/xóa |
| Khối lượng danh sách | Dựng nhiều màn hình | Phân trang và lọc theo quyền ở DB |

## Những mô-đun CHƯA chuyển sang máy chủ
Các chức năng sau còn ở bản legacy hoặc chưa xây mới, không coi là đã có ở V10:
- Báo giá/hợp đồng nhiều hạng mục, công nợ; V10 chỉ giữ mã hợp đồng và khách hàng trên mẫu.
- Lịch quan trắc, đội lấy mẫu, GPS/QR, chuỗi bàn giao và biên bản hiện trường.
- Kho hóa chất, vật tư, thiết bị, hiệu chuẩn, kiểm tra hạn dùng trước lập mẻ.
- Lập mẻ phân tích đầy đủ, nhập Excel/PDF/GC-MS, tính Csurr, hiệu suất thu hồi, độ không đảm bảo đo và biểu đồ kiểm soát.
- QC tự tính từ dữ liệu; hiện QC là xác nhận của người nhập kèm ghi chú và tham chiếu hồ sơ, chưa có kiểm tra độc lập giá trị QC.
- Kho file gốc có tải lên, checksum, lưu phiên bản và hạn lưu; hiện chỉ lưu đường dẫn/mã hồ sơ, không tự kiểm tra đường dẫn có tồn tại.
- CoA chính thức theo mẫu công ty, đánh dấu chỉ tiêu trong phạm vi công nhận, quy tắc ra quyết định, chữ ký số, sửa đổi/thu hồi phiếu đã phát hành.
- SSO/MFA, quyền theo từng phương pháp và chi nhánh, hệ thống thông báo, theo dõi giao nhận báo cáo với khách hàng.
- Thu hồi Method do lỗi kỹ thuật có xử lý tác động tới toàn bộ mẫu/phiếu. V10.1 đã có ngừng dùng cho phân công mới, nhưng chưa có quy trình thu hồi toàn diện.

## Trình tự đưa vào công ty
1. **Chạy thử bằng dữ liệu giả**: xác nhận vai trò, tách người nhập/duyệt, chạy 20–50 mẫu nhiều phòng; đối chiếu phiếu và nhật ký.
2. **Chốt yêu cầu nghiệp vụ**: cơ cấu phòng/chi nhánh, danh mục phương pháp và phạm vi VILAS, loại mẫu, quy trình sửa sai, mẫu CoA và ký duyệt.
3. **Bổ sung mô-đun vận hành**: chuỗi bàn giao/quan trắc, thiết bị và mẻ/QC, kho hồ sơ gốc, CoA/phiên bản sửa đổi; kiểm thử từng bước.
4. **Chuẩn bị hạ tầng thật**: PostgreSQL, TLS, phân quyền DB, sao lưu ngoài máy, giám sát, tài khoản vận hành riêng; đánh giá an ninh và phụ thuộc.
5. **Chuyển dữ liệu có đối chiếu**: duyệt danh mục Method, ánh xạ mã phòng/khách/mẫu; nhập nháp theo đợt, so sánh tổng số và kết quả, giữ bản cũ đọc được. Không chuyển trạng thái phê duyệt demo thành phê duyệt chính thức.
6. **Nghiệm thu có kiểm soát**: đo tải bằng dữ liệu và số người thực tế, thử phục hồi sao lưu, chạy song song rồi mới thay quy trình chính.

## Cấu hình để bắt đầu đo tải (ước lượng, chưa benchmark)
Một máy thử nghiệm 4 vCPU / 8 GB RAM / SSD, web 2 workers, PostgreSQL riêng dịch vụ, có máy/kho lưu sao lưu tách biệt. Đo p95 thời gian phản hồi, lỗi, số kết nối DB, CPU/RAM và thời gian xuất báo cáo trước khi quyết định cấu hình. Mức 30–100 tài khoản không đồng nghĩa 30–100 thao tác nặng đồng thời.

Đề xuất tiêu chí nghiệm thu: không mất/ghi đè dữ liệu ở thử đồng thời; kiểm soát quyền ở mọi API; thử phản hồi với 30, 60, 100 người dùng mô phỏng; thống nhất RPO/RTO với công ty. Chưa có kết quả benchmark PostgreSQL cho bản giao này.
