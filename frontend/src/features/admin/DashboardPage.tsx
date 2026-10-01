import { useState, type ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { styles } from "@/components/styles";
import { ErrorBox, Spinner } from "@/components/ui";
import { formatDateTime, formatPercent, formatVnd } from "@/lib/format";
import { ProgressBar, RevenueChart } from "./charts";
import { useOccupancy, useRevenue, useTopMovies } from "./queries";
import { rangeParams } from "./range";

const RANGES = [7, 14, 30] as const; // occupancy của backend giới hạn 31 ngày

function occupancyTone(ratio: number): string {
  if (ratio < 0.3) return "bg-red-600";
  if (ratio < 0.6) return "bg-amber-500";
  return "bg-green-500";
}

export function DashboardPage() {
  const [params, setParams] = useSearchParams();
  const days = RANGES.find((r) => r === Number(params.get("days"))) ?? 7;
  const [today] = useState(() => new Date());
  const range = rangeParams(days, today);

  const revenue = useRevenue(range);
  const topMovies = useTopMovies(range);
  const occupancy = useOccupancy(range);

  const totalRevenue = revenue.data?.total_revenue;
  const totalOrders = revenue.data?.total_orders;
  const average = totalOrders ? Math.round((totalRevenue ?? 0) / totalOrders) : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Báo cáo</h1>
        <div role="tablist" className="flex gap-1 rounded-lg bg-slate-900 p-1">
          {RANGES.map((r) => (
            <button
              key={r}
              type="button"
              role="tab"
              aria-selected={days === r}
              onClick={() => setParams(r === 7 ? {} : { days: String(r) })}
              className={`rounded-md px-3 py-1.5 text-sm transition ${
                days === r ? "bg-red-600 text-white" : "text-slate-300 hover:text-white"
              }`}
            >
              {r} ngày
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Doanh thu" value={totalRevenue === undefined ? "—" : formatVnd(totalRevenue)} />
        <Kpi label="Số đơn" value={totalOrders === undefined ? "—" : String(totalOrders)} />
        <Kpi label="Giá trị TB / đơn" value={totalOrders === undefined ? "—" : formatVnd(average)} />
        <Kpi
          label="Lấp đầy TB"
          value={occupancy.data ? formatPercent(occupancy.data.overall_occupancy) : "—"}
        />
      </div>

      <Section title="Doanh thu theo ngày" query={revenue}>
        {(data) => <RevenueChart days={data.days} />}
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Phim bán chạy" query={topMovies}>
          {(data) => {
            const max = Math.max(1, ...data.movies.map((m) => m.tickets));
            return data.movies.length === 0 ? (
              <p className="text-sm text-slate-400">Chưa có vé bán trong khoảng này.</p>
            ) : (
              <ol className="space-y-3">
                {data.movies.map((m, i) => (
                  <li key={m.movie_id} className="space-y-1">
                    <div className="flex justify-between gap-3 text-sm">
                      <span className="font-medium">
                        {i + 1}. {m.title}
                      </span>
                      <span className="shrink-0 text-slate-400">
                        {m.tickets} vé · {formatVnd(m.revenue)}
                      </span>
                    </div>
                    <ProgressBar ratio={m.tickets / max} barClass="bg-red-600" />
                  </li>
                ))}
              </ol>
            );
          }}
        </Section>

        <Section title="Tỉ lệ lấp đầy từng suất" query={occupancy}>
          {(data) =>
            data.showtimes.length === 0 ? (
              <p className="text-sm text-slate-400">Không có suất chiếu trong khoảng này.</p>
            ) : (
              <div className="max-h-96 overflow-auto">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 bg-slate-900 text-xs text-slate-400">
                    <tr>
                      <th className="py-2 pr-2 font-medium">Suất chiếu</th>
                      <th className="py-2 pr-2 text-right font-medium">Đã bán</th>
                      <th className="w-24 py-2 font-medium">Lấp đầy</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {data.showtimes.map((s) => (
                      <tr key={s.showtime_id}>
                        <td className="py-2 pr-2">
                          <div className="font-medium">{s.movie_title}</div>
                          <div className="text-xs text-slate-500">
                            {s.cinema_name} · {s.room_name} · {formatDateTime(s.start_time)}
                          </div>
                        </td>
                        <td className="py-2 pr-2 text-right tabular-nums">
                          {s.seats_sold}/{s.seats_total}
                        </td>
                        <td className="py-2">
                          <ProgressBar ratio={s.occupancy} barClass={occupancyTone(s.occupancy)} />
                          <span className="text-xs text-slate-400">{formatPercent(s.occupancy)}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }
        </Section>
      </div>

      <p className="text-xs text-slate-500">
        Doanh thu tính theo ngày thanh toán. Phim bán chạy và tỉ lệ lấp đầy tính theo ngày chiếu, nên
        hai nhóm số liệu này không cần khớp từng ngày.
      </p>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.card}>
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
    </div>
  );
}

/** Mỗi khối có trạng thái tải/lỗi riêng: một báo cáo lỗi không làm trắng cả trang */
function Section<T>({
  title,
  query,
  children,
}: {
  title: string;
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
}) {
  return (
    <section className={`${styles.card} space-y-4`}>
      <h2 className="font-semibold">{title}</h2>
      {query.isPending ? (
        <Spinner />
      ) : query.isError ? (
        <ErrorBox error={query.error} onRetry={() => query.refetch()} />
      ) : (
        <div className={query.isPlaceholderData ? "opacity-60" : ""}>{children(query.data)}</div>
      )}
    </section>
  );
}