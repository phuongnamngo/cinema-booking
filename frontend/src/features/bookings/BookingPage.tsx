import { useEffect } from "react";
import { useIsMutating, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { ApiError } from "@/api/client";
import { bookingsApi } from "@/api/endpoints";
import type { Booking } from "@/api/types";
import { styles } from "@/components/styles";
import { ErrorBox, NotFound, Spinner } from "@/components/ui";
import { formatCountdown, formatDateTime } from "@/lib/format";
import { useSecondsLeft } from "@/lib/useSecondsLeft";
import { ComboPicker } from "./ComboPicker";
import { isConflict } from "./errors";
import { PriceSummary } from "./PriceSummary";
import { bookingKeys, useBooking } from "./queries";
import { StatusBadge } from "./StatusBadge";
import { useComboEditor } from "./useComboEditor";
import { useVoucherActions } from "./useVoucherActions";
import { VoucherBox } from "./VoucherBox";

// Khớp PAYMENT_MIN_SECONDS_TO_PAY ở backend: đơn còn ít hơn ngần này thì server từ chối thanh toán
const MIN_SECONDS_TO_PAY = 60;

export function BookingPage() {
  const { code } = useParams();
  // Đang ghi (combo/voucher) thì tạm dừng poll: kết quả poll xuất phát trước lúc ghi
  // có thể về sau và đè dữ liệu mới
  const writing = useIsMutating({ mutationKey: bookingKeys.editing(code ?? "") }) > 0;
  const query = useBooking(code, { poll: !writing });

  if (query.error instanceof ApiError && query.error.status === 404) return <NotFound />;
  // Lỗi thoáng qua khi đang poll mà đã có dữ liệu thì vẫn hiển thị dữ liệu cũ
  if (query.error && !query.data) return <ErrorBox error={query.error} onRetry={() => void query.refetch()} />;
  if (!query.data) return <Spinner />;
  // key: sang đơn khác thì dựng lại view, vì số lượng combo đang chỉnh là state của riêng từng đơn
  return <BookingView key={query.data.code} booking={query.data} updatedAt={query.dataUpdatedAt} />;
}

function BookingView({ booking, updatedAt }: { booking: Booking; updatedAt: number }) {
  const queryClient = useQueryClient();
  const combos = useComboEditor(booking);
  const voucher = useVoucherActions(booking.code);

  // Còn thay đổi chưa lưu xong (đang chờ debounce, đang gửi) thì số tiền hiển thị là số cũ
  const editing = combos.status !== "idle" || voucher.isPending;

  // Mốc hết hạn = lúc nhận dữ liệu + seconds_left do SERVER tính (không tin đồng hồ máy khách)
  const deadline = booking.status === "pending" ? updatedAt + booking.seconds_left * 1000 : null;
  const secondsLeft = useSecondsLeft(deadline);

  // Hết giờ ở phía client: hỏi lại server xem đơn đã thật sự hết hạn chưa
  useEffect(() => {
    if (booking.status === "pending" && secondsLeft === 0) {
      void queryClient.invalidateQueries({ queryKey: bookingKeys.detail(booking.code) });
    }
  }, [booking.status, booking.code, secondsLeft, queryClient]);

  const pay = useMutation({
    mutationFn: async () => {
      const payment = await bookingsApi.pay(booking.code);
      if (!payment.payment_url) throw new Error("Không lấy được đường dẫn thanh toán.");
      return payment.payment_url;
    },
    // Sang trang cổng thanh toán. Khi quay về, trang này hỏi lại API chứ không tin URL
    onSuccess: (url) => window.location.assign(url),
  });

  const cancel = useMutation({
    mutationFn: () => bookingsApi.cancel(booking.code),
    onSuccess: (updated) => {
      queryClient.setQueryData(bookingKeys.detail(updated.code), updated);
      void queryClient.invalidateQueries({ queryKey: bookingKeys.lists });
    },
  });

  const enoughTime = secondsLeft >= MIN_SECONDS_TO_PAY;
  // 409 từ combo/voucher: đơn đã có giao dịch chờ (hoặc vừa hết hạn, khi đó trang sẽ tự đổi giao diện)
  const conflict = [combos.error, voucher.error].find(isConflict);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Đơn đặt vé</h1>
        <StatusBadge status={booking.status} />
      </div>

      <section className={`${styles.card} space-y-3`}>
        <div>
          <p className="text-lg font-semibold">{booking.movie_title}</p>
          <p className="text-sm text-slate-400">
            {booking.cinema_name} · {booking.room_name} · {formatDateTime(booking.start_time)}
          </p>
        </div>
        <PriceSummary booking={booking} stale={editing} />
      </section>

      {booking.status === "pending" && (
        <>
          <section className={`${styles.card} space-y-3`}>
            <h2 className="font-semibold">Bắp nước</h2>
            <ComboPicker editor={combos} lines={booking.combos} locked={voucher.isPending} />
          </section>

          <section className={`${styles.card} space-y-3`}>
            <h2 className="font-semibold">Mã giảm giá</h2>
            <VoucherBox booking={booking} actions={voucher} locked={combos.status !== "idle"} />
          </section>

          <section className={`${styles.card} space-y-4 text-center`}>
            <p className="text-sm text-slate-400">Ghế được giữ cho bạn trong</p>
            <p className="text-4xl font-bold tabular-nums text-amber-400">
              {formatCountdown(secondsLeft)}
            </p>
            {secondsLeft === 0 && <p className="text-sm text-slate-400">Đang kiểm tra…</p>}
            {secondsLeft > 0 && !enoughTime && (
              <p className="text-sm text-amber-400">
                Còn dưới 1 phút nên không thể bắt đầu thanh toán. Vui lòng chọn lại ghế.
              </p>
            )}

            {conflict && (
              <div role="alert" className={`${styles.error} space-y-2`}>
                <p>{conflict.message}</p>
                <button
                  type="button"
                  className={styles.buttonGhost}
                  disabled={pay.isPending || pay.isSuccess}
                  onClick={() => pay.mutate()}
                >
                  Tiếp tục thanh toán
                </button>
              </div>
            )}
            {(pay.isError || cancel.isError) && (
              <p role="alert" className={styles.error}>
                {(pay.error ?? cancel.error)?.message}
              </p>
            )}

            <div className="flex justify-center gap-3">
              <button
                type="button"
                className={styles.button}
                // Chưa lưu xong combo/voucher thì KHÔNG được thanh toán: giao dịch sẽ chốt tổng cũ
                disabled={!enoughTime || editing || pay.isPending || pay.isSuccess || cancel.isPending}
                onClick={() => pay.mutate()}
              >
                {pay.isPending || pay.isSuccess ? "Đang chuyển đến cổng…" : "Thanh toán"}
              </button>
              <button
                type="button"
                className={styles.buttonGhost}
                disabled={pay.isPending || pay.isSuccess || cancel.isPending}
                onClick={() => {
                  if (window.confirm("Hủy đơn và trả ghế?")) cancel.mutate();
                }}
              >
                Hủy đơn
              </button>
            </div>
          </section>
        </>
      )}

      {booking.status === "confirmed" && (
        <section className={`${styles.card} space-y-4 text-center`}>
          <p className="text-sm text-slate-400">Mã vé của bạn</p>
          <p className="font-mono text-3xl font-bold tracking-widest">{booking.code}</p>
          <div className="flex justify-center">
            <TicketQr code={booking.code} />
          </div>
          {booking.combos.length > 0 && (
            <p className="text-sm text-slate-300">
              Kèm combo: {booking.combos.map((c) => `${c.quantity}× ${c.name}`).join(", ")}. Nhận tại
              quầy bắp nước bằng mã vé.
            </p>
          )}
          <p className="text-sm text-slate-400">
            Đưa mã QR hoặc mã vé cho nhân viên khi vào rạp. Vé cũng đã được gửi qua email.
          </p>
        </section>
      )}

      {(booking.status === "expired" || booking.status === "cancelled") && (
        <section className={`${styles.card} space-y-3 text-center`}>
          <p className="text-slate-300">
            {booking.status === "expired"
              ? "Đơn đã hết thời gian giữ ghế."
              : "Đơn đã được hủy và ghế đã được trả lại."}
          </p>
          <Link to={`/showtimes/${booking.showtime}`} className={styles.button}>
            Chọn lại ghế
          </Link>
        </section>
      )}
    </div>
  );
}

function TicketQr({ code }: { code: string }) {
  const qr = useQuery({
    queryKey: bookingKeys.qr(code),
    queryFn: ({ signal }) => bookingsApi.qr(code, signal),
    staleTime: Infinity, // mã vé không đổi
  });

  if (qr.isPending) return <div className="h-48 w-48 animate-pulse rounded bg-slate-800" />;
  if (qr.isError) return <ErrorBox error={qr.error} onRetry={() => void qr.refetch()} />;

  // SVG nhúng bằng <img> thì không chạy được script, an toàn
  const src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(qr.data)}`;
  return <img src={src} alt={`Mã QR của vé ${code}`} className="h-48 w-48 rounded bg-white p-2" />;
}