import type { RevenuePoint } from "@/api/types";
import { formatVnd } from "@/lib/format";
import { barPercents, shortDate } from "./range";

export function RevenueChart({ days }: { days: RevenuePoint[] }) {
  const heights = barPercents(days.map((d) => d.revenue));
  const max = Math.max(0, ...days.map((d) => d.revenue));
  const labelEvery = Math.max(1, Math.ceil(days.length / 7)); // 30 ngày: chỉ in nhãn mỗi 5 ngày

  return (
    <div>
      <p className="mb-3 text-xs text-dim">
        Cao nhất: <span className="font-mono text-muted">{formatVnd(max)}</span>
      </p>
      <div
        role="img"
        aria-label={`Biểu đồ doanh thu ${days.length} ngày, cao nhất ${formatVnd(max)}`}
        className="relative flex h-56 items-end gap-1.5 border-b border-smoke bg-[repeating-linear-gradient(to_top,transparent_0,transparent_calc(25%-1px),rgba(255,255,255,0.05)_calc(25%-1px),rgba(255,255,255,0.05)_25%)]"
      >
        {days.map((d, i) => (
          <div
            key={d.date}
            className="group relative flex h-full min-w-0 flex-1 flex-col justify-end"
            title={`${shortDate(d.date)}: ${formatVnd(d.revenue)} (${d.orders} đơn)`}
          >
            <span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-lg border border-smoke bg-ink/95 px-2.5 py-1.5 text-[11px] shadow-glow-sm group-hover:block">
              {shortDate(d.date)} · {formatVnd(d.revenue)} · {d.orders} đơn
            </span>
            <div
              className="w-full origin-bottom animate-grow-up rounded-t-md bg-gradient-to-t from-rose-800 to-brand transition group-hover:from-brand group-hover:to-brand-hover group-hover:shadow-glow-sm"
              style={{ height: `${heights[i]}%`, animationDelay: `${i * 40}ms` }}
            />
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-1.5 text-[10px] text-dim" aria-hidden>
        {days.map((d, i) => (
          <span key={d.date} className="min-w-0 flex-1 text-center font-mono">
            {i % labelEvery === 0 ? shortDate(d.date) : ""}
          </span>
        ))}
      </div>
    </div>
  );
}

export function ProgressBar({ ratio, barClass }: { ratio: number; barClass: string }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-smoke">
      <div
        className={`h-2 origin-left animate-grow-x rounded-full ${barClass}`}
        style={{ width: `${Math.min(100, Math.round(ratio * 100))}%` }}
      />
    </div>
  );
}
