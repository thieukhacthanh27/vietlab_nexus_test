# Triển khai thử nội bộ và chuẩn bị sản xuất

Chưa triển khai ở lượt xây dựng này. Docker/Compose, PostgreSQL và Nginx là cấu hình bàn giao để IT kiểm chứng, chưa được khởi chạy trong môi trường xây dựng.

## Mô hình
Trình duyệt → HTTPS/Nginx → FastAPI (2 workers) → PostgreSQL.
Không mở cổng PostgreSQL ra Internet. Compose chỉ bind cổng web trên 127.0.0.1; cần reverse proxy cục bộ để tiếp cận từ mạng công ty. PostgreSQL giữ dữ liệu trên volume, không nằm trong container web.

## Khởi tạo lần đầu (IT)
1. Cài Docker/Compose. Sao chép `.env.example` thành `.env`, đặt mật khẩu DB riêng, tên miền và origin HTTPS đúng thực tế. Giữ `.env` ngoài Git và chỉ cho IT được đọc. Mật khẩu trong URL phải mã hóa percent nếu có ký tự đặc biệt.
2. `docker compose up -d db` rồi `docker compose build web`.
3. Khởi tạo schema bằng tài khoản chủ DB (vl_owner), không dùng tài khoản runtime. Ví dụ trên Bash:

```bash
read -rs -p 'Migration DATABASE_URL: ' DATABASE_URL
export DATABASE_URL
# Nhập URL dạng postgresql+psycopg://vl_owner:<mật khẩu đã mã hóa>@db:5432/vietlab
# Không gõ mật khẩu thật vào lệnh hoặc lưu lịch sử terminal.
docker compose run --rm web python -m app.manage init-db
docker compose run --rm web python -m app.manage create-admin
unset DATABASE_URL
```

4. Vào console DB: `docker compose exec db psql -U vl_owner -d vietlab`. Tạo tài khoản runtime và đặt mật khẩu qua prompt:

```sql
CREATE ROLE vl_runtime LOGIN;
\password vl_runtime
```

Đặt đúng mật khẩu đó trong DATABASE_URL của `.env`. Sau đó cấp quyền:

```bash
docker compose exec -T db psql -U vl_owner -d vietlab < docs/runtime-grants.sql
```

5. `docker compose up -d web`. Cấu hình HTTPS theo `docs/nginx.example.conf` và chứng chỉ hợp lệ của công ty. Origin phải khớp chính xác scheme/host/port. Không đổi sang cookie không Secure để né lỗi HTTPS.
6. Kiểm tra đăng nhập, tạo nhân sự, khóa nhân sự, luồng mẫu và nhật ký với nhiều trình duyệt riêng.

`APP_ENV=production` từ chối khởi động nếu không có PostgreSQL hoặc origin không phải HTTPS. Không dùng SQLite và HTTP để chia sẻ rộng trong công ty. Với PostgreSQL từ xa, thêm cấu hình TLS xác minh máy chủ phù hợp hạ tầng, không tắt xác minh chứng chỉ.

## Quyền DB
`vl_runtime` được SELECT/INSERT đối với audit và reports, không UPDATE/DELETE; mẫu/kết quả được cập nhật qua API có kiểm tra phiên bản. Nhật ký và báo cáo chưa phải kho bất biến mật mã: DBA/owner vẫn có thể sửa DB. Cần phân tách quyền DBA, giám sát và bản sao lưu ngoài máy.

Script schema init chỉ dùng tạo DB mới. Chưa có Alembic hoặc lộ trình migration schema nhiều phiên bản; không chạy `create_all` để thay đổi schema sản xuất đang có dữ liệu. Mỗi nâng cấp tiếp theo cần script migration và rollback đã thử trên bản sao DB.

## Sao lưu và thử khôi phục
Đây là thao tác quản trị cần thiết lập lịch bằng công cụ hạ tầng của công ty; gói này không tự tạo lịch.

```bash
mkdir -p backups
chmod 700 backups
umask 077
docker compose exec -T db pg_dump -U vl_owner -d vietlab -Fc > backups/vietlab-test.dump
# Khôi phục vào DB mới, không ghi đè DB đang chạy:
docker compose exec -T db createdb -U vl_owner vietlab_restore_test
docker compose exec -T db pg_restore -U vl_owner -d vietlab_restore_test --no-owner --no-acl < backups/vietlab-test.dump
```

Kiểm tra số mẫu, Method, kết quả, phiếu và audit; thử đăng nhập bằng môi trường riêng trỏ tới DB phục hồi. File dump chứa dữ liệu nghiệp vụ và hash mật khẩu/phiên nên cần mã hóa và kiểm soát quyền; thu hồi phiên sau phục hồi. Chưa kiểm thử các lệnh Docker/restore trong môi trường xây dựng. Không sao lưu SQLite trực tiếp bằng copy khi đang có ghi.

## Trước vận hành thật
- Kiểm thử PostgreSQL, quyền runtime và khôi phục ở máy staging.
- Đo tải bằng dữ liệu thực đã ẩn danh; kiểm tra pool DB, nhiều workers và kết nối.
- Phê duyệt quy trình tài khoản, mật khẩu, vai trò chuyên môn và thu hồi khi nghỉ việc. Cần cân nhắc SSO/MFA.
- Giới hạn đăng nhập ở proxy. Bộ hạn chế DB hiện đếm theo username và IP 15 phút; sau proxy IP có thể là IP proxy, nên một số lần sai có thể ảnh hưởng nhiều người. Chưa cấu hình tin cậy X-Forwarded-For; IT phải chốt dải proxy tin cậy trước khi thay đổi.
- Bổ sung theo dõi uptime, lỗi, dung lượng, sao lưu và cảnh báo; kiểm tra phiên bản phụ thuộc trước đưa lên mạng thật.
- Hoàn thiện các phần chưa có trong `DANH_GIA_VA_LO_TRINH.md`, đặc biệt hồ sơ gốc, QC thực và CoA.

Tài liệu kỹ thuật chính thức:
- https://fastapi.tiangolo.com/deployment/
- https://fastapi.tiangolo.com/deployment/server-workers/
- https://docs.sqlalchemy.org/en/20/orm/versioning.html
