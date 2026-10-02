import type { BookingCombo } from "@/api/types";
import { styles } from "@/components/styles";
import { ErrorBox, Spinner } from "@/components/ui";
import { formatVnd } from "@/lib/format";
import { buildRows, MAX_LINES, MAX_QUANTITY } from "./comboDraft";
import { isConflict } from "./errors";
import { useCombos } from "./queries";
import type { ComboEditor } from "./useComboEditor";

const STEP =
  "flex h-8 w-8 items-center justify-center rounded-full text-lg leading-none transition hover:bg-brand hover:text-white active:scale-90 disabled:opacity-30 disabled:hover:bg-transparent";

interface ComboPickerProps {
  editor: ComboEditor;
  lines: BookingCombo[]; // combo hiện có trong đơn (từ server)
  locked: boolean; // đang áp/gỡ mã: tạm khóa để hai việc không đè lên nhau
}

export function ComboPicker({ editor, lines, locked }: ComboPickerProps) {
  const combos = useCombos();

  if (combos.isPending) return <Spinner />;
  if (combos.isError) return <ErrorBox error={combos.error} onRetry={() => void combos.refetch()} />;

  const rows = buildRows(combos.data, lines);
  if (rows.length === 0) return <p className="text-sm text-muted">Hiện chưa có combo nào.</p>;

  const lineCount = Object.keys(editor.quantities).length;
  // Lỗi 409 hiển thị ở khung "Tiếp tục thanh toán" của trang, không lặp lại ở đây
  const error = editor.error && !isConflict(editor.error) ? editor.error : null;

  return (
    <div className="space-y-3">
      <ul className="space-y-2">
        {rows.map((row) => {
          const qty = editor.quantities[row.id] ?? 0;
          const cannotAdd =
            row.retired || qty >= MAX_QUANTITY || (qty === 0 && lineCount >= MAX_LINES);
          return (
            <li
              key={row.id}
              className={`flex items-center justify-between gap-3 rounded-xl border p-3 transition ${
                qty > 0 ? "border-brand/40 bg-brand/5" : "border-smoke bg-field"
              }`}
            >
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-xl" aria-hidden>
                {/nước/i.test(row.name) && !/bắp/i.test(row.name) ? "🥤" : "🍿"}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-medium">{row.name}</p>
                {row.retired ? (
                  <p className="text-xs text-red-400">Đã ngừng bán. Hãy bỏ khỏi đơn.</p>
                ) : (
                  row.description && <p className="truncate text-xs text-muted">{row.description}</p>
                )}
                <p className="mt-0.5 font-mono text-sm font-semibold text-brand-hover">{formatVnd(row.price)}</p>
              </div>
              <div className="flex shrink-0 items-center gap-1 rounded-full border border-smoke bg-ink p-1">
                <button
                  type="button"
                  aria-label={`Giảm ${row.name}`}
                  disabled={qty === 0 || locked}
                  onClick={() => editor.adjust(row.id, -1)}
                  className={STEP}
                >
                  −
                </button>
                <span key={qty} className="w-6 animate-seat-pop text-center font-mono tabular-nums" aria-live="polite">
                  {qty}
                </span>
                <button
                  type="button"
                  aria-label={`Tăng ${row.name}`}
                  disabled={cannotAdd || locked}
                  onClick={() => editor.adjust(row.id, 1)}
                  className={STEP}
                >
                  +
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      {error && (
        <p role="alert" className={styles.error}>
          {error.message}
        </p>
      )}
    </div>
  );
}