import type { BookingStatus } from "@/api/types";

const BADGE: Record<BookingStatus, { label: string; className: string }> = {
  pending: { label: "Chờ thanh toán", className: "bg-amber-900 text-amber-200" },
  confirmed: { label: "Đã xác nhận", className: "bg-green-900 text-green-200" },
  expired: { label: "Hết hạn giữ ghế", className: "bg-slate-800 text-slate-400" },
  cancelled: { label: "Đã hủy", className: "bg-slate-800 text-slate-400" },
};

export function StatusBadge({ status }: { status: BookingStatus }) {
  const { label, className } = BADGE[status];
  return <span className={`rounded-full px-3 py-1 text-xs font-medium ${className}`}>{label}</span>;
}