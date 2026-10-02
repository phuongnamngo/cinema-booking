import { describe, expect, it } from "vitest";
import type { BookingCombo, Combo } from "@/api/types";
import {
  adjustQuantity, buildRows, draftFromBooking, MAX_LINES, MAX_QUANTITY, toItems, totalCount,
} from "./comboDraft";

const line = (combo: number, quantity: number, name = `Combo ${combo}`): BookingCombo => ({
  combo, name, quantity, unit_price: 50000, line_total: 50000 * quantity,
});
const combo = (id: number): Combo => ({
  id, name: `Combo ${id}`, description: "", price: 50000, is_active: true, sort_order: id,
});

describe("draftFromBooking", () => {
  it("đổi danh sách dòng combo của đơn thành {comboId: số lượng}", () => {
    expect(draftFromBooking([line(1, 2), line(3, 1)])).toEqual({ 1: 2, 3: 1 });
    expect(draftFromBooking([])).toEqual({});
  });
});

describe("adjustQuantity", () => {
  it("tăng, giảm và xóa khỏi draft khi về 0", () => {
    let draft = adjustQuantity({}, 1, 1);
    draft = adjustQuantity(draft, 1, 1);
    expect(draft).toEqual({ 1: 2 });
    draft = adjustQuantity(adjustQuantity(draft, 1, -1), 1, -1);
    expect(draft).toEqual({}); // không để lại { 1: 0 }
  });

  it("không giảm dưới 0, không vượt MAX_QUANTITY, và trả về đúng object cũ khi không có gì đổi", () => {
    const empty = {};
    expect(adjustQuantity(empty, 1, -1)).toBe(empty);
    const full = { 1: MAX_QUANTITY };
    expect(adjustQuantity(full, 1, 1)).toBe(full);
  });

  it("không thêm quá MAX_LINES loại combo, nhưng vẫn tăng được loại đã có", () => {
    const full = Object.fromEntries(Array.from({ length: MAX_LINES }, (_, i) => [i + 1, 1]));
    expect(adjustQuantity(full, 99, 1)).toBe(full);
    expect(adjustQuantity(full, 1, 1)[1]).toBe(2);
  });

  it("không sửa object cũ (immutable)", () => {
    const before = { 1: 1 };
    adjustQuantity(before, 1, 1);
    expect(before).toEqual({ 1: 1 });
  });
});

describe("toItems / totalCount", () => {
  it("sắp theo id để payload ổn định", () => {
    expect(toItems({ 3: 1, 1: 2 })).toEqual([
      { combo: 1, quantity: 2 },
      { combo: 3, quantity: 1 },
    ]);
    expect(totalCount({ 3: 1, 1: 2 })).toBe(3);
    expect(toItems({})).toEqual([]);
  });
});

describe("buildRows", () => {
  it("thêm combo đã ngừng bán mà đơn vẫn chứa, lấy tên và giá chốt từ đơn", () => {
    const rows = buildRows([combo(1), combo(2)], [line(2, 1), line(9, 3, "Combo cũ")]);
    expect(rows.map((r) => [r.id, r.retired])).toEqual([[1, false], [2, false], [9, true]]);
    expect(rows[2]).toMatchObject({ name: "Combo cũ", price: 50000 });
  });
});