# VIETLAB NEXUS Team · V10.1 Pilot

Bản nền tảng dùng chung cho nhiều nhân viên, dành cho chạy thử quy trình phòng thử nghiệm môi trường. **Chưa phải bản thay thế đầy đủ V9.2 hoặc hệ thống đã được xác nhận đáp ứng VILAS.** Không tự động chuyển dữ liệu thật và chưa triển khai lên dịch vụ web.

## Đã có trong bản này
- Máy chủ FastAPI và dữ liệu quan hệ; cấu hình PostgreSQL cho triển khai, SQLite chỉ để thử trên một máy.
- Đăng nhập riêng, mật khẩu Argon2, phiên cookie HttpOnly, chống CSRF, khóa tài khoản và thu hồi phiên.
- Sáu vai trò: quản trị, tiếp nhận, phân tích, trưởng phòng, KCS, giám đốc. Phân quyền thực thi ở máy chủ.
- Danh mục Method theo chỉ tiêu, nền mẫu, phòng và phiên bản. Người soạn không tự duyệt.
- Tiếp nhận mẫu, phân công chỉ tiêu cho nhân viên đúng phòng, nhập kết quả cuối và tham chiếu hồ sơ gốc.
- Kết quả: nháp → gửi → trưởng phòng soát xét → KCS phát hành phiếu nội bộ. Có trả lại để sửa trước phát hành.
- Kiểm tra phiên bản khi sửa; xung đột trả HTTP 409. Nhật ký trước/sau ghi cùng giao dịch với thay đổi.
- Phân trang 50 dòng, giới hạn API 100 dòng, chỉ mục truy vấn; danh sách mẫu chỉ hiển thị theo quyền. Nhân viên và trưởng phòng không thấy tên khách hàng/mã hợp đồng trong mẫu.
- Phiếu nội bộ là bản chụp kết quả tại thời điểm phát hành; không có API sửa/xóa phiếu đã phát hành.
- Công cụ chuyển riêng danh mục Method từ bản sao JSON V9, mặc định chỉ kiểm tra, bắt buộc duyệt lại sau nhập.

## Chạy thử trên máy tính (Python 3.12, cần mạng để cài thư viện lần đầu)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m app.manage init-db
python -m app.manage create-admin
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Mở **http://localhost:8000**. Không mở file HTML mới trực tiếp: bản Team cần máy chủ.
Không có tài khoản hay mật khẩu mặc định. Lệnh create-admin hỏi username, họ tên và mật khẩu; mật khẩu không hiển thị khi gõ.

1. Admin tạo tài khoản `intake`, `analyst`, `head`, `qa` bằng giao diện; dùng ít nhất bốn người thử riêng vai trò.
2. Analyst soạn Method thuộc phòng mình, gồm phiên bản, SOP, hồ sơ xác nhận, nền và đơn vị.
3. Head cùng phòng đăng nhập, duyệt Method do người khác soạn.
4. Intake tiếp nhận mẫu và phân công Method đúng nền cho analyst.
5. Analyst nhập kết quả cuối, ghi hồ sơ gốc, ghi chú QC, xác nhận QC đạt rồi gửi trưởng phòng.
6. Head soát xét, duyệt hoặc trả lại. QA kiểm tra và phát hành phiếu nội bộ; có thể xem/in phiếu bằng trình duyệt.

Admin chỉ quản trị tài khoản/xem kiểm tra, không có quyền nhập hoặc duyệt thay chuyên môn. Với phòng chỉ có một trưởng phòng, nên để analyst soạn Method để trưởng phòng đó duyệt.

## Bổ sung ở V10.1
- Tiếp nhận sửa thông tin mẫu trước phát hành/hủy và khi tất cả chỉ tiêu còn ở nháp; bắt buộc lý do. Không đổi mã mẫu đã cấp hoặc nền mẫu đã phân công.
- Đổi vị trí, thời gian lấy mẫu hoặc tình trạng tiếp nhận sẽ bỏ xác nhận QC cũ; nhân viên phải kiểm tra lại.
- Tiếp nhận hủy mẫu chưa phân công; mẫu đã phân công chỉ KCS được hủy. Mẫu đã hủy vẫn giữ hồ sơ và lịch sử, không cho ghi kết quả/duyệt/phát hành tiếp.
- Tiếp nhận/trưởng phòng chuyển công việc nháp cho người đang hoạt động cùng phòng. Người cũ mất quyền thao tác công việc; người mới phải kiểm tra và lưu lại trước khi gửi.
- Trưởng phòng ngừng dùng Method đã duyệt để chặn phân công mới. Công việc đã giao trước đó vẫn được tiếp tục; đây không phải chức năng thu hồi kỹ thuật toàn bộ Method. Nếu phát hiện sai phương pháp, KCS cần đánh giá các mẫu liên quan và hủy/trả lại theo quy trình công ty.
- Bảng tổng quan không tính mẫu đã hủy vào quá hạn hoặc kết quả đang chờ duyệt.

V10.1 không thay cấu trúc bảng so với V10.0; không cần tạo lại DB. Dừng ứng dụng, sao lưu DB, thay mã nguồn và khởi động lại; giữ nguyên cấu hình và DB hiện có. Không dùng SQLite cho triển khai đông người.

## Tài liệu kèm theo
- `docs/DANH_GIA_VA_LO_TRINH.md`: phạm vi nâng cấp, các phần chưa chuyển và điều kiện nghiệm thu.
- `docs/TRIEN_KHAI.md`: PostgreSQL, HTTPS, quyền DB và sao lưu/khôi phục.
- `docs/PHAN_QUYEN.md`: ma trận vai trò.
- `docs/KIEM_THU.md`: kiểm thử thực tế và giới hạn xác nhận.
- `legacy/vietlab_nexus_v9_1.html`: bản V9.2 offline đã sửa ở lượt trước, giữ để đối chiếu và dùng các mô-đun cũ. Dữ liệu bản này và bản Team **không tự đồng bộ**.

## Kiểm thử

```bash
python -m pytest -q
node --check app/static/app.js
```

Bộ kiểm thử tạo DB SQLite tạm riêng. Không chạy trên DB sản xuất.

## Chuyển Method từ V9

Xuất JSON ở bản cũ, giữ bản sao gốc riêng. Chạy trước:

```bash
python -m app.import_v9_methods duong_dan_backup.json
```

Công cụ báo dòng thiếu/sai hoặc trùng trong file, chưa ghi dữ liệu. Khi toàn bộ hợp lệ và đã sao lưu DB đích:

```bash
python -m app.import_v9_methods duong_dan_backup.json --apply --actor ten_admin
```

Toàn bộ lần nhập là một giao dịch; nếu có trùng DB thì hoàn tác. Chỉ nhập Method có đủ thông tin, tất cả ở trạng thái nháp. Không mang tài khoản demo, phê duyệt, mẫu hoặc kết quả lịch sử vào hệ thống mới.
