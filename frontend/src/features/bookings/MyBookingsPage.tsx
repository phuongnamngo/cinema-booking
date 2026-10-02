import type { CSSProperties } from "react";
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
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className={styles.heading}>Vé của tôi</h1>
      {results.length === 0 ? (
        <div className={`${styles.card} flex flex-col items-center gap-3 py-14 text-center`}>
          <span className="animate-breathe text-5xl" aria-hidden>🎟️</span>
          <p className="text-muted">Bạn chưa có đơn nào.</p>
          <Link to="/" className={styles.button}>
            Xem phim đang chiếu
          </Link>
        </div>
      ) : (
        <ul className="stagger space-y-4">
          {results.map((b, i) => (
            <li key={b.code} style={{ "--i": i } as CSSProperties}>
              <Link
                to={`/bookings/${b.code}`}
                className="group flex overflow-hidden rounded-2xl border border-smoke bg-surface/70 backdrop-blur transition duration-300 hover:-translate-y-1 hover:border-brand/60 hover:shadow-lift"
              >
                <div className="min-w-0 flex-1 space-y-2 p-5">
                  <p className="font-display text-xl font-semibold uppercase tracking-wide transition group-hover:text-brand-hover">
                    {b.movie_title}
                  </p>
                  <p className="text-sm text-muted">
                    {b.cinema_name} · {b.room_name} · <span className="font-mono">{formatDateTime(b.start_time)}</span>
                  </p>
                  <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                    <span>
                      Ghế <span className="font-mono font-semibold">{b.seats.map((s) => s.label).join(", ")}</span>
                    </span>
                    <span className="font-mono text-brand-hover">{formatVnd(b.total_amount)}</span>
                  </p>
                  {b.combos.length > 0 && (
                    <p className="text-xs text-muted">
                      🍿 {b.combos.map((c) => `${c.quantity}× ${c.name}`).join(", ")}
                    </p>
                  )}
                </div>
                <div className="ticket-notch flex w-40 shrink-0 flex-col items-center justify-center gap-3 border-l-2 border-dashed border-smoke bg-field/60 p-4 text-center">
                  <StatusBadge status={b.status} />
                  <span className="font-mono text-xs tracking-widest text-muted">{b.code}</span>
                </div>
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
        <span className="flex h-9 min-w-9 items-center justify-center rounded-full bg-brand px-3 text-sm font-semibold shadow-glow-sm">
          {page}
        </span>
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
