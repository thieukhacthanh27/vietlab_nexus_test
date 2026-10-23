# Kết quả kiểm thử V10.1 Team Pilot

Thời điểm: 23/10/2026. Python 3.12, FastAPI/SQLAlchemy theo requirements.lock.txt.

## Đã thực hiện
`python -m pytest -q`: **27 passed**, 10,46 giây trong lần chạy cuối; một cảnh báo deprecation của Starlette TestClient về httpx, không phải lỗi nghiệp vụ. Thời gian này là thời gian bộ kiểm thử, không phải kết quả đo tải.

1. Luồng nhận mẫu → phân công → nhập kết quả → gửi → trưởng phòng duyệt → KCS phát hành, đọc snapshot và chặn sửa sau phát hành.
2. Giới hạn theo phòng/người được giao; ẩn khách hàng/hợp đồng với phân tích và trưởng phòng.
3. Chặn tự duyệt Method; admin không được vượt quyền chuyên môn.
4. Bản ghi cũ bị từ chối, không tạo nhật ký giả hoặc ghi đè kết quả.
5. Hai phiên ghi cùng phiên bản đồng thời: một 200, một 409; chỉ có một lần lưu được ghi nhật ký.
6. Chặn gửi khi chưa có kết quả/QC chưa đạt; chặn phát hành khi chưa duyệt đủ.
7. KCS trả lại, sửa kết quả, giữ cả giá trị trước và sau trong nhật ký.
8. Chặn thiếu phiên, thiếu CSRF, Origin khác, kiểu nội dung sai và body quá giới hạn.
9. Khóa tài khoản thu hồi phiên, chặn tự khóa admin đang thao tác.
10. Đổi mật khẩu thu hồi mọi phiên.
11. Chặn mã mẫu và Method trùng.
12. Kiểm tra giá trị NaN/dấu phẩy, trường thừa, giới hạn phân trang, ngày lấy mẫu tương lai và thiếu múi giờ.
13. Chặn phân công Method nháp và người sai phòng.
14. Tệp giao diện truy cập được, có các header bảo vệ và cookie HttpOnly.
15. Hạn chế đăng nhập thất bại lưu tại DB.
16. 32 yêu cầu đọc với 8 luồng kiểm thử: đều trả đúng phạm vi. Không tương đương 32 người dùng thật hoặc benchmark mạng.
17. Chuyển Method V9 không mang phê duyệt cũ; từ chối hồ sơ thiếu.
18. Chặn sai nền mẫu và phát hành trùng.
19. Trưởng phòng không được đoán mã mẫu chưa thuộc phòng để tự phân công.

20. Sửa hồ sơ mẫu tăng phiên bản, lưu trước/sau và từ chối ghi đè cũ.
21. Sửa thông tin ảnh hưởng mẫu hủy xác nhận QC và làm bản kết quả mở trước đó trở thành phiên bản cũ.
22. Chặn sửa khi có kết quả đã soát xét; chặn đổi mã/nền mẫu trái quy tắc.
23. Chuyển người phụ trách thu hồi quyền người cũ, yêu cầu người mới kiểm tra và lưu lại.
24. Chặn chuyển sang người khác phòng, người bị khóa hoặc bằng phiên bản cũ.
25. Hủy mẫu chưa phân công, giữ hồ sơ và chặn sửa tiếp.
26. Chỉ KCS hủy mẫu đã giao việc, bỏ khỏi số chờ duyệt và chặn duyệt tiếp; giữ kết quả cũ.
27. Method ngừng dùng chặn phân công mới, giữ công việc đang có.

JavaScript qua `node --check`; Python qua compileall. Dữ liệu kiểm thử là giả, DB SQLite tạm, không truy cập dữ liệu khách hàng.

## Chưa xác minh
- Không có Docker/PostgreSQL chạy được trong môi trường này: chưa kiểm thử hành vi khóa PostgreSQL, quyền SQL runtime, build container hoặc phục hồi pg_dump.
- Preview có quản lý không tìm thấy Python của virtualenv và không khởi động được ứng dụng; đã dừng preview. Chưa kiểm tra trực quan trên desktop/iPhone, thao tác form thật hoặc bố cục in PDF bằng trình duyệt.
- Chưa có penetration test, quét lỗ hổng toàn bộ dependency, kiểm thử SSO/MFA, kiểm tra vận hành qua proxy thật.
- Chưa benchmark 30–100 người dùng, tải nhập thiết bị hoặc tập dữ liệu lớn.
- Chưa nghiệm thu với quy trình, mẫu CoA và phạm vi VILAS của công ty.

## Bộ UAT cần chạy ở staging
Dùng các tài khoản riêng của 4–6 người thử nghiệm, nhiều phòng và ít nhất 20–50 mẫu giả. Có mẫu nhiều chỉ tiêu/nhiều phòng, QC không đạt, trả lại sửa, hai người mở một hồ sơ, khóa người đang đăng nhập, phát hành trùng, mất mạng ngay lúc lưu, nhập giá trị lớn và bản sao dữ liệu cũ. Kiểm tra dữ liệu sau tải lại, bản phiếu, nhật ký và sao lưu khôi phục. Ghi rõ kỳ vọng/kết quả/người xác nhận cho từng ca.
