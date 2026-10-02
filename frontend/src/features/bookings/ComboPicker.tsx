import type { BookingCombo } from "@/api/types";
import { styles } from "@/components/styles";
import { ErrorBox, Spinner } from "@/components/ui";
import { formatVnd } from "@/lib/format";
import { buildRows, MAX_LINES, MAX_QUANTITY } from "./comboDraft";
import { isConflict } from "./errors";
import { useCombos } from "./queries";
import type { ComboEditor } from "./useComboEditor";

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
  if (rows.length === 0) return <p className="text-sm text-slate-400">Hiện chưa có combo nào.</p>;

  const lineCount = Object.keys(editor.quantities).length;
  // Lỗi 409 hiển thị ở khung "Tiếp tục thanh toán" của trang, không lặp lại ở đây
  const error = editor.error && !isConflict(editor.error) ? editor.error : null;

  return (
    <div className="space-y-3">
      <ul className="divide-y divide-slate-800">
        {rows.map((row) => {
          const qty = editor.quantities[row.id] ?? 0;
          const cannotAdd =
            row.retired || qty >= MAX_QUANTITY || (qty === 0 && lineCount >= MAX_LINES);
          return (
            <li key={row.id} className="flex items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="font-medium">{row.name}</p>
                {row.retired ? (
                  <p className="text-xs text-red-400">Đã ngừng bán. Hãy bỏ khỏi đơn.</p>
                ) : (
                  row.description && <p className="text-xs text-slate-400">{row.description}</p>
                )}
                <p className="text-sm text-slate-300">{formatVnd(row.price)}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  aria-label={`Giảm ${row.name}`}
                  disabled={qty === 0 || locked}
                  onClick={() => editor.adjust(row.id, -1)}
                  className={styles.buttonGhost}
                >
                  −
                </button>
                <span className="w-6 text-center tabular-nums" aria-live="polite">
                  {qty}
                </span>
                <button
                  type="button"
                  aria-label={`Tăng ${row.name}`}
                  disabled={cannotAdd || locked}
                  onClick={() => editor.adjust(row.id, 1)}
                  className={styles.buttonGhost}
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