import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { ApiError } from "@/api/client";
import { bookingsApi } from "@/api/endpoints";
import type { Booking } from "@/api/types";
import { styles } from "@/components/styles";
import { ErrorBox, NotFound, Spinner } from "@/components/ui";
import { formatCountdown, formatDateTime, formatVnd } from "@/lib/format";
import { useSecondsLeft } from "@/lib/useSecondsLeft";
import { useBooking } from "./queries";
import { StatusBadge } from "./StatusBadge";

// Khớp PAYMENT_MIN_SECONDS_TO_PAY ở backend: đơn còn ít hơn ngần này thì server từ chối thanh toán
const MIN_SECONDS_TO_PAY = 60;

export function BookingPage() {
  const { code } = useParams();
  const query = useBooking(code);

  if (query.error instanceof ApiError && query.error.status === 404) return <NotFound />;
  // Lỗi thoáng qua khi đang poll mà đã có dữ liệu thì vẫn hiển thị dữ liệu cũ
  if (query.error && !query.data) return <ErrorBox error={query.error} onRetry={() => query.refetch()} />;
  if (!query.data) return <Spinner />;
  return <BookingView booking={query.data} updatedAt={query.dataUpdatedAt} />;
}

function BookingView({ booking, updatedAt }: { booking: Booking; updatedAt: number }) {
  const queryClient = useQueryClient();

  // Mốc hết hạn = lúc nhận dữ liệu + seconds_left do SERVER tính (không tin đồng hồ máy khách)
  const deadline = booking.status === "pending" ? updatedAt + booking.seconds_left * 1000 : null;
  const secondsLeft = useSecondsLeft(deadline);

  // Hết giờ ở phía client: hỏi lại server xem đơn đã thật sự hết hạn chưa
  useEffect(() => {
    if (booking.status === "pending" && secondsLeft === 0) {
      void queryClient.invalidateQueries({ queryKey: ["bookings", "detail", booking.code] });
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
      queryClient.setQueryData(["bookings", "detail", updated.code], updated);
      void queryClient.invalidateQueries({ queryKey: ["bookings", "list"] });
    },
  });

  const canPay = secondsLeft >= MIN_SECONDS_TO_PAY;

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
        <ul className="divide-y divide-slate-800 text-sm">
          {booking.seats.map((s) => (
            <li key={s.seat} className="flex justify-between py-2">
              <span>Ghế {s.label}</span>
              <span className="text-slate-400">{formatVnd(s.price)}</span>
            </li>
          ))}
        </ul>
        <div className="flex justify-between border-t border-slate-800 pt-3 font-semibold">
          <span>Tổng cộng</span>
          <span>{formatVnd(booking.total_amount)}</span>
        </div>
      </section>

      {booking.status === "pending" && (
        <section className={`${styles.card} space-y-4 text-center`}>
          <p className="text-sm text-slate-400">Ghế được giữ cho bạn trong</p>
          <p className="text-4xl font-bold tabular-nums text-amber-400">
            {formatCountdown(secondsLeft)}
          </p>
          {secondsLeft === 0 && <p className="text-sm text-slate-400">Đang kiểm tra…</p>}
          {secondsLeft > 0 && !canPay && (
            <p className="text-sm text-amber-400">
              Còn dưới 1 phút nên không thể bắt đầu thanh toán. Vui lòng chọn lại ghế.
            </p>
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
              disabled={!canPay || pay.isPending || pay.isSuccess || cancel.isPending}
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
      )}

      {booking.status === "confirmed" && (
        <section className={`${styles.card} space-y-4 text-center`}>
          <p className="text-sm text-slate-400">Mã vé của bạn</p>
          <p className="font-mono text-3xl font-bold tracking-widest">{booking.code}</p>
          <div className="flex justify-center">
            <TicketQr code={booking.code} />
          </div>
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
    queryKey: ["bookings", "qr", code] as const,
    queryFn: ({ signal }) => bookingsApi.qr(code, signal),
    staleTime: Infinity, // mã vé không đổi
  });

  if (qr.isPending) return <div className="h-48 w-48 animate-pulse rounded bg-slate-800" />;
  if (qr.isError) return <ErrorBox error={qr.error} onRetry={() => qr.refetch()} />;

  // SVG nhúng bằng <img> thì không chạy được script, an toàn
  const src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(qr.data)}`;
  return <img src={src} alt={`Mã QR của vé ${code}`} className="h-48 w-48 rounded bg-white p-2" />;
}