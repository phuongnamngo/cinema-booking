import type { BookingStatus } from "@/api/types";

const BADGE: Record<BookingStatus, { label: string; className: string }> = {
  pending: { label: "Chờ thanh toán", className: "border-amber-500/40 bg-amber-500/10 text-amber-300" },
  confirmed: { label: "Đã xác nhận", className: "border-green-500/40 bg-green-500/10 text-green-300" },
  expired: { label: "Hết hạn giữ ghế", className: "border-zinc-600/60 bg-zinc-500/10 text-zinc-400" },
  cancelled: { label: "Đã hủy", className: "border-red-500/40 bg-red-500/10 text-red-300" },
};

export function StatusBadge({ status }: { status: BookingStatus }) {
  const { label, className } = BADGE[status];
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${className}`}>
      <span className={`h-1.5 w-1.5 rounded-full bg-current ${status === "pending" ? "animate-pulse" : ""}`} />
      {label}
    </span>
  );
}
