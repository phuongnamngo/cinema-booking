import type { BookingCombo, Combo, ComboItem } from "@/api/types";

/** comboId -> số lượng (luôn > 0). Combo không có trong object = 0 phần */
export type Draft = Record<number, number>;

// Khớp MAX_COMBO_QUANTITY / MAX_COMBO_LINES ở backend (Bước 14).
// Ở đây chỉ để chặn sớm cho UX, server vẫn kiểm tra thật
export const MAX_QUANTITY = 10;
export const MAX_LINES = 10;

export function draftFromBooking(lines: BookingCombo[]): Draft {
  const draft: Draft = {};
  for (const line of lines) draft[line.combo] = line.quantity;
  return draft;
}

/** Trả về CHÍNH draft cũ nếu không có gì thay đổi, để nơi gọi so sánh bằng === */
export function adjustQuantity(draft: Draft, comboId: number, delta: number): Draft {
  const current = draft[comboId] ?? 0;
  const next = Math.min(MAX_QUANTITY, Math.max(0, current + delta));
  if (next === current) return draft;
  if (current === 0 && Object.keys(draft).length >= MAX_LINES) return draft;

  const copy = { ...draft };
  if (next === 0) delete copy[comboId];
  else copy[comboId] = next;
  return copy;
}

/** Sắp theo id để payload ổn định */
export function toItems(draft: Draft): ComboItem[] {
  return Object.entries(draft)
    .map(([id, quantity]) => ({ combo: Number(id), quantity }))
    .sort((a, b) => a.combo - b.combo);
}

export const totalCount = (draft: Draft) => Object.values(draft).reduce((sum, q) => sum + q, 0);

export interface ComboRow {
  id: number;
  name: string;
  description: string;
  price: number;
  retired: boolean; // đã ngừng bán nhưng vẫn nằm trong đơn
}

/** Combo đang bán, cộng thêm những combo đã ngừng bán mà đơn này vẫn đang chứa */
export function buildRows(active: Combo[], lines: BookingCombo[]): ComboRow[] {
  const rows: ComboRow[] = active.map((c) => ({
    id: c.id, name: c.name, description: c.description, price: c.price, retired: false,
  }));
  const known = new Set(active.map((c) => c.id));
  for (const line of lines) {
    if (!known.has(line.combo)) {
      rows.push({ id: line.combo, name: line.name, description: "", price: line.unit_price, retired: true });
    }
  }
  return rows;
}