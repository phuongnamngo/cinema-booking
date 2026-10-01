export type SeatStatus = "held" | "mine" | "sold";
export type SeatStatusMap = Record<number, SeatStatus>;

/** Hợp đồng WebSocket của Bước 7 */
export type SeatServerMessage =
  | { type: "snapshot"; showtime_id: number; held: number[]; mine: number[]; sold: number[] }
  | { type: "seats_held" | "seats_released" | "seats_sold"; seat_ids: number[] }
  | { type: "pong" };

export interface SeatMapState {
  synced: boolean; // đã nhận snapshot đầu tiên chưa
  statuses: SeatStatusMap; // ghế không có trong map = còn trống
}

export const initialSeatState: SeatMapState = { synced: false, statuses: {} };

export function seatReducer(state: SeatMapState, message: SeatServerMessage): SeatMapState {
  switch (message.type) {
    case "snapshot": {
      const statuses: SeatStatusMap = {};
      for (const id of message.held) statuses[id] = "held";
      for (const id of message.mine) statuses[id] = "mine";
      for (const id of message.sold) statuses[id] = "sold";
      return { synced: true, statuses };
    }
    case "seats_held": {
      const statuses = { ...state.statuses };
      for (const id of message.seat_ids) {
        // Không hạ cấp ghế của mình hay ghế đã bán
        if (statuses[id] !== "mine" && statuses[id] !== "sold") statuses[id] = "held";
      }
      return { ...state, statuses };
    }
    case "seats_released": {
      const statuses = { ...state.statuses };
      for (const id of message.seat_ids) {
        if (statuses[id] !== "sold") delete statuses[id]; // ghế đã bán thì không bao giờ được nhả
      }
      return { ...state, statuses };
    }
    case "seats_sold": {
      const statuses = { ...state.statuses };
      for (const id of message.seat_ids) statuses[id] = "sold";
      return { ...state, statuses };
    }
    case "pong":
      return state;
  }
}