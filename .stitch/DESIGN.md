# Design System: Cinema Booking — "Cinema Noir"
**Project ID:** 13825592516016028319
**Design System Asset:** assets/6069199120842790442

## 1. Visual Theme & Atmosphere
Bước vào một rạp chiếu tối: nền đen sâu, một luồng "đèn chiếu" đỏ ấm toả từ trên xuống, hạt film rất nhẹ và các quầng sáng mềm. Cảm giác sang trọng, đắm chìm, điện ảnh; mật độ thông tin vừa phải, khoảng thở rộng ở hero và dày hơn ở các trang nghiệp vụ (soát vé, báo cáo). Toàn bộ chữ trên giao diện là tiếng Việt.

## 2. Color Palette & Roles
- **Theater Black (#0A0A0F)** — nền trang, có quầng đỏ radial mờ ở trên-giữa và lớp chấm "film grain" đỏ 8% (lưới 24px).
- **Velvet Charcoal (#14141C)** — bề mặt card; viền **Smoke (#26263A)** 1px; overlay dùng kính mờ (backdrop-blur).
- **Input Ink (#0F0F16)** — nền ô nhập.
- **Cinema Red (#E11D48)** — nút chính, tab đang chọn, ghế đang chọn, focus ring. Glow: `0 0 24px rgba(225,29,72,0.45)`; hover sáng hơn (#F43F5E).
- **Marquee Gold (#F5C451)** — ghế VIP, điểm đánh giá, hạng #1, điểm nhấn cao cấp.
- **Sweetbox Pink (#EC4899)** — ghế đôi.
- **Holding Sky (#38BDF8)** — ghế bạn đang giữ, banner thông tin.
- **Countdown Amber (#F59E0B)** — cảnh báo, đồng hồ đếm ngược, ghế người khác giữ.
- **Success Green (#22C55E)** / **Error Red (#F87171)** — trạng thái thành công / lỗi.
- **Off White (#F4F4F5)** chữ chính · **Muted Gray (#A1A1AA)** chữ phụ · **Dim Gray (#71717A)** chữ mờ.

## 3. Typography Rules
- **Headline/Display:** Bebas Neue — chữ IN HOA, cao, tracking ~0.02em; dùng cho tiêu đề trang, tên phim, số lớn (KPI, tổng tiền).
- **Body/Label:** Be Vietnam Pro (300–800) — hỗ trợ đầy đủ dấu tiếng Việt.
- **Mono:** JetBrains Mono — mã vé, mã voucher, đồng hồ, số tiền dạng bảng (tabular-nums).

## 4. Component Stylings
* **Buttons:** Bo vừa (10px). Primary: nền Cinema Red đặc, glow đỏ khi hover, vệt shimmer lướt qua, nhấn co 0.97. Ghost: nền trong suốt viền Smoke, sáng lên khi hover. Disabled: mờ 40%.
* **Cards/Containers:** Bo rộng (16px), nền Velvet Charcoal bán trong suốt + blur, viền Smoke, bóng đổ đen sâu; hover nhấc lên và viền đỏ phát sáng.
* **Ticket cards:** Hình dạng vé thật — khía bán nguyệt hai bên, đường xé nét đứt, cuống vé chứa mã mono và QR.
* **Inputs/Forms:** Nền Input Ink, viền Smoke, focus ring đỏ có glow; lỗi hiển thị chữ đỏ dưới field.
* **Pills/Badges:** Bo tròn hoàn toàn. Trạng thái đơn: Chờ thanh toán (amber), Đã thanh toán (green), Hết hạn (gray), Đã hủy (red). Độ tuổi: P green, K sky, T13 yellow, T16 orange, T18 red.
* **Seat map:** Màn hình cong phát sáng + chùm sáng chiếu xuống; ghế bo trên; lối đi giữa ghế 6–7; VIP viền vàng, đôi viền hồng rộng gấp đôi.
* **Header:** Sticky, kính mờ đen bán trong suốt, viền dưới mảnh; logo "🎬 CINEMA" đỏ.

## 5. Layout Principles
- Khung nội dung tối đa ~1200px (`max-w-6xl`/`7xl`), padding ngang 16–24px.
- Trang catalog: hero full-bleed, lưới poster 2/3/4 cột.
- Trang thao tác: bố cục 2 cột (nội dung + sidebar sticky 320px) trên desktop, xếp dọc trên mobile.
- Trang đơn/tài khoản: cột giữa hẹp (440–720px).

## 6. Motion
- Vào trang: fade + trượt lên 16px, 400–550ms, `cubic-bezier(0.16,1,0.3,1)`; danh sách stagger 60ms.
- Card hover: nhấc −6px, poster zoom 1.08 trong khung overflow-hidden, glow đỏ.
- Skeleton: shimmer quét trái → phải.
- Hero: Ken Burns zoom chậm. Ghế chọn: pop. Ghế bị giữ: pulse chậm. Chấm "Trực tiếp": ping.
- Tôn trọng `prefers-reduced-motion`: tắt transform/animation, chỉ giữ fade.

## Screens
| # | Screen | Stitch screen ID | File |
|---|---|---|---|
| 1 | Trang chủ catalog | ebcba1797524458bbafaac8875575e75 | designs/01-home.* |
| 2 | Chi tiết phim + lịch chiếu | 5e36cd32aefa4a2a88296aadd29c75c6 | designs/02-movie-detail.* |
| 3 | Chọn ghế | b8076690c068496ca331aea167629238 | designs/03-seat-selection.* |
| 4 | Đơn đặt vé (3 trạng thái) | 4f49e1f89c4b4e73839bfe5a338ef9c6 | designs/04-booking.* |
| 5 | Vé của tôi + Tài khoản | 8b33fe62f8d74212a8484957a65e8799 | designs/05-my-tickets-account.* |
| 6 | Đăng nhập, Đăng ký, 404 | 935591d2ffd44815b37a6f949bd06211 | designs/06-auth-404.* |
| 7 | Soát vé | efacb77695a1470fad3d1ab3c1a4ff05 | designs/07-staff-checkin.* |
| 8 | Báo cáo admin | 5f87662f81624f51b72785137e57035c | designs/08-admin-dashboard.* |
