# Vai trò trong V10 Pilot

| Chức năng | Admin | Tiếp nhận | Phân tích | Trưởng phòng | KCS | Giám đốc |
|---|---|---|---|---|---|---|
| Tạo/khóa tài khoản | Có | Không | Không | Không | Không | Không |
| Xem mẫu | Toàn bộ | Toàn bộ | Chỉ mẫu được giao | Mẫu thuộc phòng | Toàn bộ | Toàn bộ |
| Xem tên KH/hợp đồng | Có | Có | Ẩn | Ẩn | Có | Có |
| Tiếp nhận mẫu | Không | Có | Không | Không | Không | Không |
| Phân công chỉ tiêu | Không | Có | Không | Cùng phòng, mẫu đã tới phòng | Không | Không |
| Sửa thông tin mẫu | Không | Khi mọi kết quả nháp, chưa phát hành/hủy | Không | Không | Không | Không |
| Hủy mẫu | Không | Mẫu chưa phân công | Không | Không | Mẫu chưa phát hành | Không |
| Chuyển người phụ trách | Không | Công việc nháp | Không | Cùng phòng, công việc nháp | Không | Không |
| Ngừng dùng Method cho phân công mới | Không | Không | Không | Cùng phòng | Không | Không |
| Soạn Method | Không* | Không | Cùng phòng | Cùng phòng | Không | Không |
| Duyệt Method | Không | Không | Không | Cùng phòng, khác người soạn | Không | Không |
| Nhập kết quả cuối | Không | Không | Việc được giao, đang nháp | Không | Không | Không |
| Soát xét kết quả | Không | Không | Không | Cùng phòng, khác người nhập | Không | Không |
| Trả toàn bộ kết quả về nháp | Không | Không | Không | Không | Có, trước phát hành | Không |
| Phát hành phiếu nội bộ | Không | Không | Không | Không | Có, độc lập người nhập/duyệt | Không |
| Xem phiếu đã phát hành | Có | Có | Không | Không | Có | Có |
| Xem nhật ký toàn công ty | Có | Không | Không | Không | Có | Có |

* Công cụ chuyển đổi qua console cho phép admin nhập Method từ V9 ở trạng thái nháp. Trưởng phòng phải duyệt lại trên web.

Vai trò được gán theo tài khoản; bản pilot chưa có một người kiêm nhiều vai trò, năng lực theo từng Method, ủy quyền có thời hạn hoặc quyền theo chi nhánh. Cần chốt ma trận thực tế với công ty trước mở rộng.

Khóa/mở khóa tài khoản thu hồi toàn bộ phiên của tài khoản đó. Đổi mật khẩu cũng thu hồi mọi phiên. Đặt lại mật khẩu khi quên thực hiện qua console được quản lý:

`python -m app.manage reset-password`

Không có tài khoản mặc định, không có chức năng chọn vai trò tùy ý như bản demo cũ. Quyền cấp admin vẫn là quyền rất nhạy cảm vì admin có thể tạo tài khoản mới thuộc vai trò khác; công ty cần quy trình cấp quyền và rà soát nhật ký độc lập.
