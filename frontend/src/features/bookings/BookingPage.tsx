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
import { editsLockedByPendingPayment } from "./pendingPayment";
import { PriceSummary } from "./PriceSummary";
import { bookingKeys, useBooking } from "./queries";
import { StatusBadge } from "./StatusBadge";
import { useComboEditor } from "./useComboEditor";
import { useVoucherActions } from "./useVoucherActions";
import { VoucherBox } from "./VoucherBox";

// Khớp PAYMENT_MIN_SECONDS_TO_PAY ở backend: đơn còn ít hơn ngần này thì server từ chối thanh toán
const MIN_SECONDS_TO_PAY = 60;
// Khớp SEAT_HOLD_SECONDS mặc định ở backend; chỉ dùng để vẽ vòng đếm ngược
const HOLD_SECONDS = 600;

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

  const cancelPayment = useMutation({
    mutationFn: () => bookingsApi.cancelPayment(booking.code),
    onSuccess: (updated) => {
      queryClient.setQueryData(bookingKeys.detail(updated.code), updated);
      void queryClient.invalidateQueries({ queryKey: bookingKeys.lists });
    },
  });

  const enoughTime = secondsLeft >= MIN_SECONDS_TO_PAY;
  const paymentLocked = editsLockedByPendingPayment(booking.has_pending_payment);
  // 409 từ combo/voucher: đơn đã có giao dịch chờ (hoặc vừa hết hạn, khi đó trang sẽ tự đổi giao diện)
  const conflict = [combos.error, voucher.error].find(isConflict);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className={styles.heading}>Đơn đặt vé</h1>
        <StatusBadge status={booking.status} />
      </div>

      {booking.status === "confirmed" && <ETicket booking={booking} />}

      <section className={`${styles.card} space-y-4`}>
        <div>
          <p className="font-display text-2xl font-semibold uppercase tracking-wide">{booking.movie_title}</p>
          <p className="mt-1 text-sm text-muted">
            {booking.cinema_name} · {booking.room_name} ·{" "}
            <span className="font-mono">{formatDateTime(booking.start_time)}</span>
          </p>
        </div>
        <PriceSummary booking={booking} stale={editing} />
      </section>

      {booking.status === "pending" && (
        <>
          <section className={`${styles.card} flex flex-col items-center gap-4 text-center sm:flex-row sm:text-left`}>
            <CountdownRing secondsLeft={secondsLeft} />
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Ghế được giữ cho bạn trong</p>
              <p className="text-sm text-muted">Hết giờ, ghế sẽ tự mở lại cho khách khác.</p>
              {secondsLeft === 0 && <p className="text-sm text-muted">Đang kiểm tra…</p>}
              {secondsLeft > 0 && !enoughTime && (
                <p className="text-sm text-amber-400">
                  Còn dưới 1 phút nên không thể bắt đầu thanh toán. Vui lòng chọn lại ghế.
                </p>
              )}
            </div>
          </section>

          <section className={`${styles.card} space-y-4`}>
            <h2 className="font-display text-xl font-semibold uppercase tracking-wide">🍿 Bắp nước</h2>
            <ComboPicker editor={combos} lines={booking.combos} locked={paymentLocked || voucher.isPending} />
          </section>

          <section className={`${styles.card} space-y-4`}>
            <h2 className="font-display text-xl font-semibold uppercase tracking-wide">🎟 Mã giảm giá</h2>
            <VoucherBox
              booking={booking}
              actions={voucher}
              locked={paymentLocked || combos.status !== "idle"}
            />
          </section>

          <section className="space-y-4">
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
            {(pay.isError || cancel.isError || cancelPayment.isError) && (
              <p role="alert" className={styles.error}>
                {(pay.error ?? cancel.error ?? cancelPayment.error)?.message}
              </p>
            )}

            <button
              type="button"
              className={`${styles.button} w-full py-4 text-base uppercase tracking-wider`}
              // Chưa lưu xong combo/voucher thì KHÔNG được thanh toán: giao dịch sẽ chốt tổng cũ
              disabled={
                !enoughTime ||
                editing ||
                pay.isPending ||
                pay.isSuccess ||
                cancel.isPending ||
                cancelPayment.isPending
              }
              onClick={() => pay.mutate()}
            >
              {pay.isPending || pay.isSuccess ? "Đang chuyển đến cổng…" : "Thanh toán →"}
            </button>
            {paymentLocked && (
              <button
                type="button"
                className={`${styles.buttonGhost} w-full`}
                disabled={pay.isPending || pay.isSuccess || cancelPayment.isPending}
                onClick={() => cancelPayment.mutate()}
              >
                Hủy giao dịch
              </button>
            )}
            <button
              type="button"
              className="w-full py-2 text-sm text-muted transition hover:text-red-300 disabled:opacity-40"
              disabled={pay.isPending || pay.isSuccess || cancel.isPending || cancelPayment.isPending}
              onClick={() => {
                if (window.confirm("Hủy đơn và trả ghế?")) cancel.mutate();
              }}
            >
              Hủy đơn
            </button>
          </section>
        </>
      )}

      {(booking.status === "expired" || booking.status === "cancelled") && (
        <section className={`${styles.card} flex flex-col items-center gap-4 py-10 text-center`}>
          <span className="flex h-16 w-16 items-center justify-center rounded-full border border-smoke bg-field text-3xl opacity-70" aria-hidden>
            ⌛
          </span>
          <p className="text-lg font-semibold text-zinc-300">
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

function CountdownRing({ secondsLeft }: { secondsLeft: number }) {
  const ratio = Math.min(1, secondsLeft / HOLD_SECONDS);
  const urgent = secondsLeft < MIN_SECONDS_TO_PAY;
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  return (
    <div className={`relative h-32 w-32 shrink-0 ${urgent ? "animate-pulse" : ""}`}>
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90" aria-hidden>
        <circle cx="60" cy="60" r={radius} fill="none" stroke="currentColor" strokeWidth="8" className="text-smoke" />
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - ratio)}
          className={`transition-[stroke-dashoffset] duration-1000 ease-linear ${urgent ? "text-brand" : "text-amber-400"}`}
        />
      </svg>
      <p
        className={`absolute inset-0 flex items-center justify-center font-mono text-3xl font-bold tabular-nums ${
          urgent ? "text-brand-hover" : "text-amber-400"
        }`}
      >
        {formatCountdown(secondsLeft)}
      </p>
    </div>
  );
}

function ETicket({ booking }: { booking: Booking }) {
  return (
    <section className="animate-ticket-in overflow-hidden rounded-2xl border border-brand/40 bg-gradient-to-b from-[#1c1020] to-surface shadow-[0_30px_80px_-30px_rgba(225,29,72,0.6)]">
      <div className="h-1.5 bg-gradient-to-r from-brand via-gold to-brand" />
      <div className="space-y-5 p-6">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-[0.25em] text-brand-hover">🎬 Cinema Ticket</span>
          <span className="rounded-full border border-green-500/40 bg-green-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-green-300">
            Vé chính thức
          </span>
        </div>
        <p className="font-display text-3xl font-bold uppercase tracking-wide">{booking.movie_title}</p>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs uppercase tracking-wider text-dim">Rạp & phòng</p>
            <p className="mt-1 font-medium">
              {booking.cinema_name} · {booking.room_name}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-dim">Suất chiếu</p>
            <p className="mt-1 font-mono font-medium">{formatDateTime(booking.start_time)}</p>
          </div>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider text-dim">Ghế</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {booking.seats.map((s) => (
              <span key={s.seat} className="rounded-lg bg-brand px-3 py-1.5 font-mono text-lg font-bold text-white shadow-glow-sm">
                {s.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="ticket-notch border-t-2 border-dashed border-smoke" />

      <div className="flex flex-col items-center gap-5 p-6 text-center">
        <p className="text-xs uppercase tracking-[0.25em] text-muted">Mã vé của bạn</p>
        <p className="font-mono text-3xl font-bold tracking-[0.35em]">{booking.code}</p>
        <TicketQr code={booking.code} />
        {booking.combos.length > 0 && (
          <p className="rounded-xl border border-brand/30 bg-brand/5 px-4 py-3 text-sm text-zinc-300">
            🍿 Kèm combo: {booking.combos.map((c) => `${c.quantity}× ${c.name}`).join(", ")}. Nhận tại quầy bắp
            nước bằng mã vé.
          </p>
        )}
        <p className="text-sm text-muted">
          Đưa mã QR hoặc mã vé cho nhân viên khi vào rạp. Vé cũng đã được gửi qua email.
        </p>
      </div>
    </section>
  );
}

function TicketQr({ code }: { code: string }) {
  const qr = useQuery({
    queryKey: bookingKeys.qr(code),
    queryFn: ({ signal }) => bookingsApi.qr(code, signal),
    staleTime: Infinity, // mã vé không đổi
  });

  if (qr.isPending) return <div className="skeleton h-52 w-52 rounded-xl" />;
  if (qr.isError) return <ErrorBox error={qr.error} onRetry={() => void qr.refetch()} />;

  // SVG nhúng bằng <img> thì không chạy được script, an toàn
  const src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(qr.data)}`;
  return (
    <div className="relative overflow-hidden rounded-xl bg-white p-3 shadow-[0_0_40px_rgba(255,255,255,0.12)]">
      <img src={src} alt={`Mã QR của vé ${code}`} className="h-48 w-48" />
      <span
        className="pointer-events-none absolute inset-0 animate-qr-sweep bg-gradient-to-b from-transparent via-brand/25 to-transparent"
        aria-hidden
      />
    </div>
  );
}