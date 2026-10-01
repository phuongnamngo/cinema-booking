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
  connecting: { label: "Đang kết nối…", dot: "bg-slate-500" },
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
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to={`/movies/${showtime.movie}`} className="text-2xl font-bold hover:underline">
            {showtime.movie_title}
          </Link>
          <p className="mt-1 text-sm text-slate-400">
            {showtime.cinema_name} · {showtime.room_name} · {formatDateTime(showtime.start_time)}
          </p>
        </div>
        <span
          className="flex items-center gap-2 rounded-full bg-slate-900 px-3 py-1 text-xs text-slate-300"
          role="status"
        >
          <span className={`h-2 w-2 rounded-full ${conn.dot}`} />
          {conn.label}
        </span>
      </div>

      {pending && (
        <div className="rounded-lg border border-sky-800 bg-sky-950 p-4 text-sm">
          Bạn đang giữ ghế cho suất chiếu này.{" "}
          <Link to={`/bookings/${pending.code}`} className="font-semibold text-sky-300 underline">
            Đến trang thanh toán
          </Link>
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          {seatsQuery.isPending ? (
            <Spinner />
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

        <aside className={`${styles.card} h-fit space-y-4 lg:sticky lg:top-6`}>
          <h2 className="font-semibold">Ghế đã chọn</h2>
          {validSelected.length === 0 ? (
            <p className="text-sm text-slate-400">Chọn tối đa {MAX_SEATS} ghế.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {validSelected.map((id) => {
                const seat = seatsById.get(id);
                return (
                  seat && (
                    <li key={id} className="flex justify-between">
                      <span>{seat.label}</span>
                      <span className="text-slate-400">{formatVnd(seat.price)}</span>
                    </li>
                  )
                );
              })}
            </ul>
          )}
          {lostLabels.length > 0 && (
            <p role="alert" className="text-sm text-amber-400">
              Ghế {lostLabels.join(", ")} vừa có người khác chọn.
            </p>
          )}
          <div className="flex justify-between border-t border-slate-800 pt-3 font-semibold">
            <span>Tạm tính</span>
            <span>{formatVnd(total)}</span>
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
            className={`${styles.button} w-full`}
          >
            {hold.isPending
              ? "Đang giữ ghế…"
              : authStatus === "authenticated"
                ? "Tiếp tục"
                : "Đăng nhập để tiếp tục"}
          </button>
          <p className="text-xs text-slate-500">
            Ghế chỉ được giữ (10 phút) khi bạn bấm "Tiếp tục". Giá tính lại ở máy chủ.
          </p>
        </aside>
      </div>
    </div>
  );
}