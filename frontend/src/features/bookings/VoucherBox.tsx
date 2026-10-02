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
        <div className="flex items-center justify-between rounded-md border border-green-800 bg-green-950 px-3 py-2 text-sm">
          <span>
            <span className="font-mono font-semibold">{booking.voucher_code}</span> · giảm{" "}
            {formatVnd(booking.discount_amount)}
          </span>
          <button
            type="button"
            disabled={busy}
            onClick={() => actions.mutate({ kind: "remove" })}
            className="text-green-300 underline disabled:opacity-50"
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
          className={`${styles.input} font-mono uppercase`}
        />
        <button type="submit" disabled={busy || !input.trim()} className={styles.buttonGhost}>
          {actions.isPending ? "Đang áp…" : "Áp dụng"}
        </button>
      </form>
      {error && (
        <p role="alert" className="text-sm text-red-400">
          {error.message}
        </p>
      )}
    </div>
  );
}