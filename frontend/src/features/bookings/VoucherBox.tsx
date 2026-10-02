import { useState, type FormEvent } from "react";
import type { Booking } from "@/api/types";
import { styles } from "@/components/styles";
import { formatVnd } from "@/lib/format";
import { isConflict } from "./errors";
import type { VoucherActions } from "./useVoucherActions";

interface VoucherBoxProps {
  booking: Booking;
  actions: VoucherActions;
  locked: boolean; // đang lưu combo: tạm khóa để hai việc không đè lên nhau
}

export function VoucherBox({ booking, actions, locked }: VoucherBoxProps) {
  const [input, setInput] = useState("");
  const busy = locked || actions.isPending;
  // Lỗi 409 hiển thị ở khung "Tiếp tục thanh toán" của trang, không lặp lại ở đây
  const error = actions.error && !isConflict(actions.error) ? actions.error : null;

  function submit(event: FormEvent) {
    event.preventDefault();
    const code = input.trim().toUpperCase(); // server cũng chuẩn hóa, đây chỉ để gửi gọn
    if (!code) return;
    actions.mutate({ kind: "apply", code }, { onSuccess: () => setInput("") });
  }

  return (
    <div className="space-y-3">
      {booking.voucher_code && (
        <div className="ticket-notch flex animate-fade-up items-center justify-between gap-3 rounded-xl border border-dashed border-green-500/50 bg-green-950/40 px-5 py-3 text-sm">
          <span className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-green-500/15 font-bold text-green-300" aria-hidden>
              %
            </span>
            <span>
              <span className="font-mono font-semibold tracking-wider text-green-300">{booking.voucher_code}</span>
              <span className="text-muted"> · giảm </span>
              <span className="font-mono">{formatVnd(booking.discount_amount)}</span>
            </span>
          </span>
          <button
            type="button"
            disabled={busy}
            onClick={() => actions.mutate({ kind: "remove" })}
            className="text-xs font-semibold text-green-300 underline-offset-2 hover:underline disabled:opacity-50"
          >
            Gỡ
          </button>
        </div>
      )}
      {/* Luôn hiện ô nhập: nhập mã khác sẽ ĐỔI mã. Nếu mã mới bị từ chối, mã cũ vẫn được giữ (Bước 14) */}
      <form onSubmit={submit} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            if (actions.isError) actions.reset(); // gõ lại thì xóa lỗi cũ
          }}
          aria-label="Mã giảm giá"
          placeholder="Nhập mã giảm giá"
          maxLength={32}
          autoCapitalize="characters"
          autoComplete="off"
          className={`${styles.input} font-mono uppercase tracking-wider`}
        />
        <button type="submit" disabled={busy || !input.trim()} className={styles.buttonGhost}>
          {actions.isPending ? "Đang áp…" : "Áp dụng"}
        </button>
      </form>
      {error && (
        <p role="alert" className="animate-shake text-sm text-red-400">
          {error.message}
        </p>
      )}
    </div>
  );
}