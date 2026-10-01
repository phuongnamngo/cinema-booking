import type { RevenuePoint } from "@/api/types";
import { formatVnd } from "@/lib/format";
import { barPercents, shortDate } from "./range";

export function RevenueChart({ days }: { days: RevenuePoint[] }) {
  const heights = barPercents(days.map((d) => d.revenue));
  const max = Math.max(0, ...days.map((d) => d.revenue));
  const labelEvery = Math.max(1, Math.ceil(days.length / 7)); // 30 ngày: chỉ in nhãn mỗi 5 ngày

  return (
    <div>
      <p className="mb-2 text-xs text-slate-500">Cao nhất: {formatVnd(max)}</p>
      <div
        role="img"
        aria-label={`Biểu đồ doanh thu ${days.length} ngày, cao nhất ${formatVnd(max)}`}
        className="flex h-48 items-end gap-1"
      >
        {days.map((d, i) => (
          <div
            key={d.date}
            className="flex h-full min-w-0 flex-1 flex-col justify-end"
            title={`${shortDate(d.date)}: ${formatVnd(d.revenue)} (${d.orders} đơn)`}
          >
            <div className="w-full rounded-t bg-red-600" style={{ height: `${heights[i]}%` }} />
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-1 text-[10px] text-slate-500" aria-hidden>
        {days.map((d, i) => (
          <span key={d.date} className="min-w-0 flex-1 text-center">
            {i % labelEvery === 0 ? shortDate(d.date) : ""}
          </span>
        ))}
      </div>
    </div>
  );
}

export function ProgressBar({ ratio, barClass }: { ratio: number; barClass: string }) {
  return (
    <div className="h-2 w-full rounded bg-slate-800">
      <div
        className={`h-2 rounded ${barClass}`}
        style={{ width: `${Math.min(100, Math.round(ratio * 100))}%` }}
      />
    </div>
  );
}