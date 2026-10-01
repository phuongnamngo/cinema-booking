import { describe, expect, it } from "vitest";
import { initialSeatState, seatReducer, type SeatMapState, type SeatServerMessage } from "./seatState";

const snapshot = (
  over: Partial<{ held: number[]; mine: number[]; sold: number[] }> = {},
): SeatServerMessage => ({
  type: "snapshot", showtime_id: 1, held: [1, 2], mine: [3], sold: [4], ...over,
});

const start = () => seatReducer(initialSeatState, snapshot());

describe("seatReducer", () => {
  it("snapshot thay toàn bộ state và đánh dấu đã đồng bộ", () => {
    const state = seatReducer(start(), snapshot({ held: [9], mine: [], sold: [] }));
    expect(state).toEqual({ synced: true, statuses: { 9: "held" } });
  });

  it("seats_held không hạ cấp ghế của mình hoặc ghế đã bán", () => {
    const state = seatReducer(start(), { type: "seats_held", seat_ids: [3, 4, 5] });
    expect(state.statuses).toEqual({ 1: "held", 2: "held", 3: "mine", 4: "sold", 5: "held" });
  });

  it("seats_released nhả ghế bị giữ và ghế của mình nhưng không bao giờ nhả ghế đã bán", () => {
    const state = seatReducer(start(), { type: "seats_released", seat_ids: [1, 3, 4] });
    expect(state.statuses).toEqual({ 2: "held", 4: "sold" });
  });

  it("seats_sold ghi đè mọi trạng thái", () => {
    const state = seatReducer(start(), { type: "seats_sold", seat_ids: [1, 3, 7] });
    expect(state.statuses).toEqual({ 1: "sold", 2: "held", 3: "sold", 4: "sold", 7: "sold" });
  });

  it("áp dụng cùng một sự kiện hai lần cho kết quả như một lần (idempotent)", () => {
    const events: SeatServerMessage[] = [
      { type: "seats_held", seat_ids: [5] },
      { type: "seats_released", seat_ids: [1] },
      { type: "seats_sold", seat_ids: [2] },
    ];
    for (const event of events) {
      const once = seatReducer(start(), event);
      expect(seatReducer(once, event)).toEqual(once);
    }
  });

  it("không sửa state cũ (immutable)", () => {
    const before = start();
    const frozen: SeatMapState = structuredClone(before);
    seatReducer(before, { type: "seats_sold", seat_ids: [1] });
    expect(before).toEqual(frozen);
  });

  it("pong trả về đúng state cũ", () => {
    const before = start();
    expect(seatReducer(before, { type: "pong" })).toBe(before);
  });
});