import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router";
import { ApiError } from "@/api/client";
import { bookingsApi } from "@/api/endpoints";
import type { Showtime, ShowtimeSeat } from "@/api/types";
import { useAuth } from "@/auth/store";
import { styles } from "@/components/styles";
import { ErrorBox, NotFound, Spinner } from "@/components/ui";
import { usePendingBooking } from "@/features/bookings/queries";
import { formatDateTime, formatVnd } from "@/lib/format";
import { useShowtime, useShowtimeSeats } from "./queries";
import { SeatGrid, SeatLegend } from "./SeatGrid";
import type { SeatStatus } from "./seatState";
import { useSeatMap } from "./useSeatMap";

const MAX_SEATS = 8; // server cũng kiểm tra (MAX_SEATS_PER_BOOKING), đây chỉ để UI báo sớm
const NO_SEATS: ShowtimeSeat[] = []; // hằng số: tránh tạo mảng mới mỗi lần render

const CONNECTION = {
  connecting: { label: "Đang kết nối…", dot: "bg-zinc-500" },
  open: { label: "Trực tiếp", dot: "bg-green-500" },
  reconnecting: { label: "Mất kết nối, đang nối lại…", dot: "bg-amber-500" },
  unavailable: { label: "Suất chiếu không còn mở", dot: "bg-red-500" },
} as const;

export function ShowtimePage() {
  const { id } = useParams();
  const showtimeId = Number(id);
  const valid = Number.isInteger(showtimeId) && showtimeId > 0;
  const showtime = useShowtime(valid ? showtimeId : undefined);

  if (!valid) return <NotFound />;
  // Khách chỉ thấy suất còn hiệu lực và chưa chiếu: suất đã qua trả 404
  if (showtime.error instanceof ApiError && showtime.error.status === 404) return <NotFound />;
  if (showtime.error) return <ErrorBox error={showtime.error} onRetry={() => showtime.refetch()} />;
  if (showtime.isPending) return <Spinner />;
  return <SeatPicker showtime={showtime.data} />;
}

function SeatPicker({ showtime }: { showtime: Showtime }) {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const authStatus = useAuth((s) => s.status);
  const userId = useAuth((s) => s.user?.id ?? null);

  const seatsQuery = useShowtimeSeats(showtime.id, userId);
  const socket = useSeatMap(showtime.id);
  const pending = usePendingBooking(showtime.id);
  const [selected, setSelected] = useState<number[]>([]);

  const seats = seatsQuery.data ?? NO_SEATS;
  const seatsById = useMemo(() => new Map(seats.map((s) => [s.id, s])), [seats]);

  // Trước snapshot đầu tiên thì dùng trạng thái từ REST; sau đó WebSocket là nguồn duy nhất
  const statusOf = (seat: ShowtimeSeat): SeatStatus | undefined =>
    socket.synced
      ? socket.statuses[seat.id]
      : seat.status === "available"
        ? undefined
        : seat.status;

  // Ghế đã chọn mà vừa bị người khác lấy thì loại ngay khi render (không cần effect)
  const validSelected = selected.filter((id) => {
    const seat = seatsById.get(id);
    return seat !== undefined && statusOf(seat) === undefined;
  });
  const lostLabels = selected
    .filter((id) => !validSelected.includes(id))
    .map((id) => seatsById.get(id)?.label ?? "");
  const total = validSelected.reduce((sum, id) => sum + (seatsById.get(id)?.price ?? 0), 0);
  const closed = socket.connection === "unavailable";

  const hold = useMutation({
    mutationFn: (seatIds: number[]) => bookingsApi.hold(showtime.id, seatIds),
    onSuccess: (booking) => {
      // Trang đơn hàng hiển thị ngay, không cần chờ tải lại
      queryClient.setQueryData(["bookings", "detail", booking.code], booking);
      void queryClient.invalidateQueries({ queryKey: ["bookings", "list"] });
      navigate(`/bookings/${booking.code}`);
    },
    // Thất bại (thường là 409): lấy lại trạng thái ghế mới nhất từ REST làm dự phòng
    onError: () => void seatsQuery.refetch(),
  });

  function toggle(seat: ShowtimeSeat) {
    setSelected(
      validSelected.includes(seat.id)
        ? validSelected.filter((id) => id !== seat.id)
        : [...validSelected, seat.id],
    );
    hold.reset();
  }

  function handleContinue() {
    if (authStatus !== "authenticated") {
      navigate("/login", { state: { from: location.pathname } });
      return;
    }
    hold.mutate(validSelected);
  }

  const conn = CONNECTION[socket.connection];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div className="space-y-1">
          <Link to={`/movies/${showtime.movie}`} className="text-xs text-muted transition hover:text-fg">
            ← Đổi suất chiếu
          </Link>
          <h1>
            <Link
              to={`/movies/${showtime.movie}`}
              className="font-display text-3xl font-bold uppercase tracking-wide transition hover:text-brand-hover sm:text-4xl"
            >
              {showtime.movie_title}
            </Link>
          </h1>
          <p className="text-sm text-muted">
            <span className="text-brand-hover">{showtime.cinema_name}</span> · {showtime.room_name} ·{" "}
            <span className="font-mono">{formatDateTime(showtime.start_time)}</span>
          </p>
        </div>
        <span
          className="flex items-center gap-2 rounded-full border border-smoke bg-surface/80 px-3.5 py-1.5 text-xs text-zinc-300 backdrop-blur"
          role="status"
        >
          <span className="relative flex h-2.5 w-2.5">
            {socket.connection === "open" && (
              <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-70 ${conn.dot}`} />
            )}
            <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${conn.dot}`} />
          </span>
          {conn.label}
        </span>
      </div>

      {pending && (
        <div className="flex animate-fade-up flex-wrap items-center justify-between gap-3 rounded-2xl border border-hold/30 bg-sky-950/40 px-5 py-4 text-sm backdrop-blur">
          <span>ℹ️ Bạn đang giữ ghế cho suất chiếu này.</span>
          <Link to={`/bookings/${pending.code}`} className="font-semibold text-hold hover:underline">
            Đến trang thanh toán →
          </Link>
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-6">
          {seatsQuery.isPending ? (
            <div className="skeleton h-[420px] rounded-2xl" />
          ) : seatsQuery.isError ? (
            <ErrorBox error={seatsQuery.error} onRetry={() => seatsQuery.refetch()} />
          ) : (
            <>
              <SeatGrid
                seats={seats}
                statusOf={statusOf}
                selected={validSelected}
                locked={closed || validSelected.length >= MAX_SEATS}
                onToggle={toggle}
              />
              <SeatLegend />
            </>
          )}
        </div>

        <aside className={`${styles.card} h-fit space-y-5 lg:sticky lg:top-24`}>
          <div className="flex items-center justify-between">
            <h2 className="font-display text-xl font-semibold uppercase tracking-wide">Ghế đã chọn</h2>
            {validSelected.length > 0 && (
              <span className="rounded-full bg-brand/15 px-2.5 py-0.5 text-xs font-semibold text-brand-hover">
                {validSelected.length} ghế
              </span>
            )}
          </div>
          {validSelected.length === 0 ? (
            <p className="rounded-xl border border-dashed border-smoke px-4 py-6 text-center text-sm text-muted">
              Chọn tối đa {MAX_SEATS} ghế.
            </p>
          ) : (
            <ul className="space-y-2 text-sm">
              {validSelected.map((id) => {
                const seat = seatsById.get(id);
                return (
                  seat && (
                    <li
                      key={id}
                      className="flex animate-fade-up items-center justify-between rounded-xl border border-smoke bg-field px-3.5 py-2.5"
                    >
                      <span className="flex items-center gap-2">
                        <span className="font-mono font-semibold">{seat.label}</span>
                        {seat.seat_type !== "standard" && (
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                              seat.seat_type === "vip" ? "bg-gold/15 text-gold" : "bg-sweet/15 text-sweet"
                            }`}
                          >
                            {seat.seat_type === "vip" ? "VIP" : "Đôi"}
                          </span>
                        )}
                      </span>
                      <span className="font-mono text-muted">{formatVnd(seat.price)}</span>
                    </li>
                  )
                );
              })}
            </ul>
          )}
          {lostLabels.length > 0 && (
            <p role="alert" className="animate-shake rounded-xl border border-amber-500/30 bg-amber-950/30 px-3.5 py-2.5 text-sm text-amber-300">
              ⚠️ Ghế {lostLabels.join(", ")} vừa có người khác chọn.
            </p>
          )}
          <div className="flex items-end justify-between border-t border-smoke pt-4">
            <span className="text-sm text-muted">Tạm tính</span>
            <span key={total} className="animate-fade-up font-display text-3xl font-bold tabular-nums">
              {formatVnd(total)}
            </span>
          </div>
          {hold.isError && (
            <p role="alert" className={styles.error}>
              {hold.error.message}
            </p>
          )}
          <button
            type="button"
            onClick={handleContinue}
            disabled={
              closed || hold.isPending || pending !== undefined || validSelected.length === 0
            }
            className={`${styles.button} w-full py-3.5 text-base uppercase tracking-wider`}
          >
            {hold.isPending
              ? "Đang giữ ghế…"
              : authStatus === "authenticated"
                ? "Tiếp tục →"
                : "Đăng nhập để tiếp tục"}
          </button>
          <p className="text-center text-xs leading-relaxed text-dim">
            Ghế chỉ được giữ (10 phút) khi bạn bấm "Tiếp tục". Giá tính lại ở máy chủ.
          </p>
        </aside>
      </div>
    </div>
  );
}
