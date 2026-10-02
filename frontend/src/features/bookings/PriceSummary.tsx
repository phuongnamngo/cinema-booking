import type { Booking } from "@/api/types";
import { formatVnd } from "@/lib/format";

/** Mọi con số ở đây đều do server tính. FE không cộng trừ gì cả */
export function PriceSummary({ booking, stale }: { booking: Booking; stale: boolean }) {
  return (
    <div aria-busy={stale}>
      <div className={`transition-opacity duration-300 ${stale ? "opacity-50" : ""}`}>
        <ul className="divide-y divide-smoke text-sm">
          {booking.seats.map((s) => (
            <li key={s.seat} className="flex justify-between py-2.5">
              <span>
                Ghế <span className="font-mono font-semibold">{s.label}</span>
              </span>
              <span className="font-mono text-muted">{formatVnd(s.price)}</span>
            </li>
          ))}
          {booking.combos.map((c) => (
            <li key={c.combo} className="flex justify-between py-2.5">
              <span>
                {c.quantity}× {c.name}
              </span>
              <span className="font-mono text-muted">{formatVnd(c.line_total)}</span>
            </li>
          ))}
          {booking.discount_amount > 0 && (
            <li className="flex justify-between py-2.5 text-green-400">
              <span>Giảm giá{booking.voucher_code && ` (${booking.voucher_code})`}</span>
              <span className="font-mono">−{formatVnd(booking.discount_amount)}</span>
            </li>
          )}
        </ul>
        <div className="mt-2 flex items-end justify-between border-t border-smoke pt-4">
          <span className="text-sm uppercase tracking-wider text-muted">Tổng cộng</span>
          <span className="font-display text-3xl font-bold tabular-nums text-brand-hover">
            {formatVnd(booking.total_amount)}
          </span>
        </div>
      </div>
      {stale && (
        <p role="status" className="mt-2 text-xs text-dim">
          Đang cập nhật giá…
        </p>
      )}
    </div>
  );
}
