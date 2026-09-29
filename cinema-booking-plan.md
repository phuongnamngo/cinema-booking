# Kế hoạch dự án Cinema Booking

> Stack: Django + DRF + Channels + Celery, React, PostgreSQL, Redis, Docker
> Mục tiêu: web đặt vé rạp chiếu phim hoàn chỉnh, chạy được thực tế, có realtime chọn ghế và thanh toán.

---

## 1. Kiến trúc tổng quan

Làm **modular monolith**, chưa cần microservices. Một project Django chia thành nhiều app, dễ dev và deploy, vẫn đủ "chuẩn" để đưa vào portfolio.

```
Browser (React SPA)
   │  REST (HTTP)          │  WebSocket
   ▼                       ▼
 Nginx ──► Django (ASGI: Uvicorn/Daphne)
              ├─ DRF (REST API)
              ├─ Channels (WebSocket)
              └─ Celery worker/beat (job nền)
                    │
        ┌───────────┴───────────┐
     PostgreSQL               Redis
   (dữ liệu chính)   (seat hold, channel layer, celery broker, cache)
```

## 2. Tech stack

| Lớp | Công nghệ | Ghi chú |
|---|---|---|
| Backend | Django + Django REST Framework | JWT auth (`simplejwt`), `drf-spectacular` sinh OpenAPI |
| Realtime | Django Channels + `channels-redis` | Chạy ASGI |
| Job nền | Celery + Celery Beat | Hết hạn giữ ghế, gửi email, nhắc suất chiếu |
| DB | PostgreSQL | Dùng constraint, index, transaction |
| Cache / hold | Redis | Giữ ghế tạm (TTL), channel layer, broker |
| Frontend | React + Vite + TypeScript | TanStack Query (server state), Zustand (client state), React Router, Tailwind |
| Thanh toán | VNPay/MoMo sandbox (hoặc Stripe test) | Có webhook/IPN |
| Infra | Docker Compose, Nginx | Sau này thêm GitHub Actions CI/CD |
| Test | pytest-django, Vitest/RTL, Playwright (E2E) | |

Phần FE (React) đã quen nên không tốn nhiều sức. Điểm mới cần đầu tư: Django, Channels, Celery.

## 3. Domain model

- **User**: role gồm customer, staff, admin.
- **Cinema → Room → Seat**: seat có `row`, `number`, `type` (standard/VIP/couple), tọa độ để vẽ sơ đồ.
- **Movie**: title, genre, duration, poster, trailer, rating, trạng thái (now showing / coming soon).
- **Showtime**: movie, room, start_time, end_time, giá theo loại ghế.
- **Booking**: user, showtime, status (`PENDING → CONFIRMED / EXPIRED / CANCELLED`), total, expires_at, mã QR/booking code.
- **BookingSeat**: booking, showtime, seat, price.
- **Payment**: booking, provider, transaction_id, status, raw payload.
- **Bổ sung**: Combo/Food, Promotion/Voucher, Review.

## 4. Bài toán cốt lõi: chống đặt trùng ghế và realtime

Đây là phần làm dự án khác biệt so với một app CRUD.

### Luồng giữ ghế

1. Người dùng chọn ghế và gửi request hold.
2. Backend dùng Redis: `SET hold:{showtime}:{seat} {user_id} NX EX 600`. Nếu `NX` thất bại nghĩa là ghế đã có người giữ.
3. Broadcast qua Channels group `showtime_{id}` để mọi client đang xem sơ đồ ghế đổi màu ngay (đang giữ, đã bán).
4. Thanh toán thành công: mở transaction Postgres, dùng `select_for_update`, insert `BookingSeat`, xóa key hold và broadcast trạng thái "đã bán".
5. Hết TTL hoặc hủy thì ghế tự nhả, Celery cập nhật booking sang `EXPIRED`.

### Lớp bảo vệ cuối ở DB

Unique constraint trên `(showtime_id, seat_id)` cho các booking chưa bị hủy (partial unique index). Dù Redis lỗi hay có race condition thì DB vẫn không cho trùng ghế.

### Event WebSocket

- `seat_held`, `seat_released`, `seat_sold`
- Snapshot đầy đủ khi client mới connect
- Xử lý reconnect và đồng bộ lại trạng thái

## 5. Cấu trúc project

```
cinema/
├─ backend/
│  ├─ config/            # settings (base/dev/prod), asgi, celery
│  └─ apps/
│     ├─ users/  movies/  cinemas/  showtimes/
│     ├─ bookings/  payments/  notifications/
├─ frontend/
│  └─ src/ (features/, components/, hooks/, api/, ws/)
├─ nginx/
├─ docker-compose.yml       # db, redis, backend, worker, beat, frontend, nginx
└─ docker-compose.prod.yml
```

## 6. Roadmap (~8–10 tuần, làm một mình)

### Phase 0: Nền tảng (3–4 ngày)
- [ ] Docker Compose: Postgres, Redis, Django, React, hot reload
- [ ] Settings tách env (base/dev/prod)
- [ ] Linter/formatter (ruff, black, eslint), pre-commit
- [ ] Skeleton Celery + Channels chạy được

### Phase 1: Auth và danh mục (1 tuần)
- [ ] Đăng ký/đăng nhập JWT, refresh token, phân quyền
- [ ] CRUD Movie, Cinema, Room, Seat (tool sinh sơ đồ ghế tự động)
- [ ] FE: trang chủ, danh sách phim, chi tiết phim

### Phase 2: Suất chiếu (1 tuần)
- [ ] CRUD Showtime, validate trùng lịch phòng
- [ ] Lọc phim theo rạp, ngày, thể loại
- [ ] FE: chọn rạp, ngày, giờ chiếu

### Phase 3: Đặt vé và realtime (2 tuần), phần khó nhất
- [ ] Sơ đồ ghế, hold bằng Redis, Channels broadcast
- [ ] Đếm ngược thời gian giữ ghế, Celery expire
- [ ] Xác thực WebSocket bằng JWT
- [ ] Script test đồng thời (nhiều user tranh 1 ghế)

### Phase 4: Thanh toán (1 tuần)
- [ ] Tích hợp cổng sandbox, webhook idempotent
- [ ] Sinh vé/QR, gửi email xác nhận
- [ ] Lịch sử đặt vé

### Phase 5: Admin và báo cáo (1 tuần)
- [ ] Dashboard doanh thu, tỉ lệ lấp đầy, phim hot
- [ ] Check-in vé bằng quét QR (role staff)
- [ ] Voucher, combo bắp nước

### Phase 6: Hoàn thiện và deploy (1 tuần)
- [ ] Test: unit, integration, E2E
- [ ] Rate limit, CORS/CSRF, logging
- [ ] CI/CD, deploy VPS bằng docker compose, HTTPS, Sentry
- [ ] README, sơ đồ kiến trúc, demo video

## 7. Điểm cần lưu ý

- **Chạy ASGI ngay từ đầu** (Uvicorn/Daphne), đừng dùng `runserver` kiểu WSGI rồi mới chuyển.
- **Xác thực WebSocket**: truyền JWT qua query param hoặc cookie, viết middleware riêng trong Channels.
- **Mọi thứ liên quan tiền và ghế nằm trong `transaction.atomic()`**.
- **Webhook thanh toán phải idempotent**, vì cổng có thể gọi lại nhiều lần.
- **Không tin client**: giá và trạng thái ghế luôn tính lại ở server.
- **Timezone**: lưu UTC, hiển thị `Asia/Ho_Chi_Minh`.
- **Django ORM**: dùng `select_related`/`prefetch_related` để tránh N+1 (giống eager loading của Laravel).

## 8. Bước tiếp theo

1. Chốt schema DB chi tiết cho các model
2. Dựng skeleton Phase 0 (`docker compose up` chạy được toàn bộ stack)
