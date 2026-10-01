import type { DateRange } from "@/api/types";
import { toDateParam } from "@/lib/format";

/** n ngày gần nhất tính đến `today`, đã gồm cả hai đầu (khớp quy ước của backend) */
export function rangeParams(days: number, today: Date): DateRange {
  const from = new Date(today);
  from.setDate(from.getDate() - (days - 1));
  return { date_from: toDateParam(from), date_to: toDateParam(today) };
}

/** "2026-10-05" -> "05/10". Tách chuỗi thay vì new Date() để không bị lệch ngày do múi giờ */
export function shortDate(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${day}/${month}`;
}

/** Chiều cao cột theo %: cột lớn nhất = 100%, giá trị dương nhỏ vẫn thấy được (tối thiểu 2%) */
export function barPercents(values: number[]): number[] {
  const max = Math.max(0, ...values);
  if (max === 0) return values.map(() => 0);
  return values.map((v) => (v <= 0 ? 0 : Math.max(2, Math.round((v / max) * 100))));
}