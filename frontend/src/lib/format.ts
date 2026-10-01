const TZ = "Asia/Ho_Chi_Minh";

const timeFmt = new Intl.DateTimeFormat("vi-VN", {
  hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: TZ,
});
const dayFmt = new Intl.DateTimeFormat("vi-VN", { weekday: "short", day: "2-digit", month: "2-digit" });
// release_date chỉ có ngày (không giờ): format theo UTC để không lệch ngày ở múi giờ khác
const releaseFmt = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit", month: "2-digit", year: "numeric", timeZone: "UTC",
});
const vndFmt = new Intl.NumberFormat("vi-VN", {
  style: "currency", currency: "VND", maximumFractionDigits: 0,
});

export const formatTime = (iso: string) => timeFmt.format(new Date(iso));
export const formatDayLabel = (date: Date) => dayFmt.format(date);
export const formatReleaseDate = (date: string) => releaseFmt.format(new Date(date));
export const formatVnd = (amount: number) => vndFmt.format(amount);

/** "YYYY-MM-DD" theo giờ máy. KHÔNG dùng toISOString(): nó trả ngày theo UTC. */
export function toDateParam(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function nextDays(count: number): Date[] {
  return Array.from({ length: count }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    return d;
  });
}

const dateTimeFmt = new Intl.DateTimeFormat("vi-VN", {
  hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  day: "2-digit", month: "2-digit", year: "numeric", timeZone: TZ,
});

export const formatDateTime = (iso: string) => dateTimeFmt.format(new Date(iso));

export function formatCountdown(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}