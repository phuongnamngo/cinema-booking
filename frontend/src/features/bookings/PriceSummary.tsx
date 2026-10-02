import type { Booking } from "@/api/types";
import { formatVnd } from "@/lib/format";

/** Mọi con số ở đây đều do server tính. FE không cộng trừ gì cả */
export function PriceSummary({ booking, stale }: { booking: Booking; stale: boolean }) {
  return (
    <div aria-busy={stale}>
      <div className={`transition-opacity ${stale ? "opacity-50" : ""}`}>
        <ul className="divide-y divide-slate-800 text-sm">
          {booking.seats.map((s) => (
            <li key={s.seat} className="flex justify-between py-2">
              <span>Ghế {s.label}</span>
              <span className="text-slate-400">{formatVnd(s.price)}</span>
            </li>
          ))}
          {booking.combos.map((c) => (
            <li key={c.combo} className="flex justify-between py-2">
              <span>
                {c.quantity}× {c.name}
              </span>
              <span className="text-slate-400">{formatVnd(c.line_total)}</span>
            </li>
          ))}
          {booking.discount_amount > 0 && (
            <li className="flex justify-between py-2 text-green-400">
              <span>Giảm giá{booking.voucher_code && ` (${booking.voucher_code})`}</span>
              <span>−{formatVnd(booking.discount_amount)}</span>
            </li>
          )}
        </ul>
        <div className="flex justify-between border-t border-slate-800 pt-3 font-semibold">
          <span>Tổng cộng</span>
          <span>{formatVnd(booking.total_amount)}</span>
        </div>
      </div>
      {stale && (
        <p role="status" className="mt-2 text-xs text-slate-500">
          Đang cập nhật giá…
        </p>
      )}
    </div>
  );
}