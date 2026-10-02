import { Link, useSearchParams } from "react-router";
import { styles } from "@/components/styles";
import { ErrorBox, Spinner } from "@/components/ui";
import { formatDateTime, formatVnd } from "@/lib/format";
import { useBookings } from "./queries";
import { StatusBadge } from "./StatusBadge";

export function MyBookingsPage() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const query = useBookings({ page });

  if (query.isPending) return <Spinner />;
  if (query.isError) return <ErrorBox error={query.error} onRetry={() => query.refetch()} />;

  const { results, previous, next } = query.data;

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">Vé của tôi</h1>
      {results.length === 0 ? (
        <p className="py-12 text-center text-slate-400">
          Bạn chưa có đơn nào.{" "}
          <Link to="/" className="text-red-400 hover:underline">
            Xem phim đang chiếu
          </Link>
        </p>
      ) : (
        <ul className="space-y-3">
          {results.map((b) => (
            <li key={b.code}>
              <Link
                to={`/bookings/${b.code}`}
                className={`${styles.card} block space-y-2 transition hover:border-slate-600`}
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="font-semibold">{b.movie_title}</p>
                  <StatusBadge status={b.status} />
                </div>
                <p className="text-sm text-slate-400">
                  {b.cinema_name} · {b.room_name} · {formatDateTime(b.start_time)}
                </p>
                <p className="text-sm text-slate-400">
                  Ghế {b.seats.map((s) => s.label).join(", ")} · {formatVnd(b.total_amount)} ·{" "}
                  <span className="font-mono">{b.code}</span>
                </p>
                {b.combos.length > 0 && (
                  <p className="text-sm text-slate-400">
                    Combo: {b.combos.map((c) => `${c.quantity}× ${c.name}`).join(", ")}
                  </p>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
      <div className="flex items-center justify-center gap-4">
        <button
          type="button"
          className={styles.buttonGhost}
          disabled={!previous}
          onClick={() => setParams({ page: String(page - 1) })}
        >
          ← Trước
        </button>
        <span className="text-sm text-slate-400">Trang {page}</span>
        <button
          type="button"
          className={styles.buttonGhost}
          disabled={!next}
          onClick={() => setParams({ page: String(page + 1) })}
        >
          Sau →
        </button>
      </div>
    </div>
  );
}