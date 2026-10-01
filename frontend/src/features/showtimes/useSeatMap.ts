import { useEffect, useReducer, useState } from "react";
import { useAuth } from "@/auth/store";
import { SeatSocket, type ConnectionStatus } from "./seatSocket";
import { initialSeatState, seatReducer } from "./seatState";

export function useSeatMap(showtimeId: number) {
  const authStatus = useAuth((s) => s.status);
  const userId = useAuth((s) => s.user?.id ?? null);
  const [state, dispatch] = useReducer(seatReducer, initialSeatState);
  const [connection, setConnection] = useState<ConnectionStatus>("connecting");

  useEffect(() => {
    // Chờ khôi phục phiên xong. Nếu kết nối quá sớm, socket đi không kèm token và
    // ghế của chính mình sẽ hiện là "đang bị giữ" thay vì "của bạn"
    if (authStatus === "loading") return;

    const socket = new SeatSocket({ showtimeId, onMessage: dispatch, onStatus: setConnection });
    socket.start();
    return () => socket.stop();
    // Đổi người dùng (đăng nhập/đăng xuất) thì phải nối lại với danh tính mới.
    // Token tự refresh thì KHÔNG cần: userId không đổi
  }, [showtimeId, authStatus, userId]);

  return { ...state, connection };
}