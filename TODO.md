# TODO

## Hoàn tiền và hủy sau thanh toán

- Outcome: hoàn một payment `succeeded`, lưu trạng thái refund và kết quả cổng; hủy được vé đã thanh toán; hủy suất chiếu đã có đơn thì hoàn các đơn bị ảnh hưởng; ghi audit cho các thao tác đó.
- Why deferred: change `payment-safety` chỉ làm Phase 1. Quy tắc hạn hủy, hoàn toàn bộ hay một phần, và ai được hoàn chưa có trong source.
- Origin: `payment-safety`, từ nhóm A trong `booking_remaining_work.md` (Phase 2).
- Resume: payment đã có `cancelled` và `needs_review`. Django Admin hiện chỉ ghi `review_note`. Hủy suất vẫn là `Showtime.is_active=false` và không đụng đơn đã bán. Làm sau khi IPN, đối soát, và hàng `needs_review` đã chạy.
