import { refreshAccessToken } from "@/api/client";
import { tokens } from "@/auth/tokens";
import type { SeatServerMessage } from "./seatState";

export type ConnectionStatus = "connecting" | "open" | "reconnecting" | "unavailable";

export const CLOSE_UNAUTHORIZED = 4401; // token sai/hết hạn: refresh rồi nối lại
export const CLOSE_NOT_FOUND = 4404; // suất chiếu đã đóng: đừng nối lại

const PING_INTERVAL_MS = 25_000;
const PONG_TIMEOUT_MS = 10_000;
const WS_OPEN = 1;

/** Exponential backoff với "equal jitter": nằm trong [ceiling/2, ceiling] */
export function backoffDelay(attempt: number, random: () => number = Math.random): number {
  const ceiling = Math.min(30_000, 1_000 * 2 ** attempt);
  return ceiling / 2 + random() * (ceiling / 2);
}

export interface SeatSocketOptions {
  showtimeId: number;
  onMessage: (message: SeatServerMessage) => void;
  onStatus: (status: ConnectionStatus) => void;
  random?: () => number; // để test cố định độ trễ
}

export class SeatSocket {
  private readonly options: SeatSocketOptions;
  private ws: WebSocket | null = null;
  private stopped = false;
  private attempt = 0;
  private unauthorizedCount = 0;
  private skipToken = false;
  private retryTimer: ReturnType<typeof setTimeout> | undefined;
  private pingTimer: ReturnType<typeof setInterval> | undefined;
  private pongTimer: ReturnType<typeof setTimeout> | undefined;

  constructor(options: SeatSocketOptions) {
    this.options = options;
  }

  start() {
    window.addEventListener("online", this.wakeUp);
    document.addEventListener("visibilitychange", this.onVisibility);
    this.connect();
  }

  stop() {
    this.stopped = true;
    window.removeEventListener("online", this.wakeUp);
    document.removeEventListener("visibilitychange", this.onVisibility);
    clearTimeout(this.retryTimer);
    this.retryTimer = undefined;
    this.detach();
  }

  private connect() {
    if (this.stopped) return;
    this.retryTimer = undefined;

    const token = this.skipToken ? null : tokens.getAccess();
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    const query = token ? `?token=${encodeURIComponent(token)}` : "";
    const ws = new WebSocket(
      `${scheme}://${location.host}/ws/showtimes/${this.options.showtimeId}/seats/${query}`,
    );
    this.ws = ws;

    ws.onopen = () => this.startHeartbeat();
    ws.onmessage = (event) => this.handleMessage(event.data);
    ws.onclose = (event) => this.handleClose(ws, event.code);
  }

  private handleMessage(raw: unknown) {
    // Có bất kỳ message nào tới nghĩa là kết nối còn sống
    clearTimeout(this.pongTimer);
    this.pongTimer = undefined;

    let message: SeatServerMessage;
    try {
      message = JSON.parse(String(raw)) as SeatServerMessage;
    } catch {
      return; // dữ liệu rác: bỏ qua, không làm sập kết nối
    }
    if (typeof message?.type !== "string") return;

    if (message.type === "snapshot") {
      // Snapshot mới là lúc kết nối thật sự dùng được
      this.attempt = 0;
      this.unauthorizedCount = 0;
      this.options.onStatus("open");
    }
    this.options.onMessage(message);
  }

  private handleClose(ws: WebSocket, code: number) {
    if (this.stopped || this.ws !== ws) return; // socket cũ đã bị bỏ
    this.clearHeartbeat();
    this.ws = null;

    if (code === CLOSE_NOT_FOUND) {
      this.options.onStatus("unavailable");
      return;
    }
    if (code === CLOSE_UNAUTHORIZED) {
      void this.recoverFromUnauthorized();
      return;
    }
    this.scheduleReconnect();
  }

  private async recoverFromUnauthorized() {
    this.unauthorizedCount += 1;
    this.options.onStatus("reconnecting");
    if (this.unauthorizedCount === 1) {
      try {
        await refreshAccessToken();
      } catch {
        /* lỗi mạng: cứ nối lại, lần sau sẽ biết */
      }
    } else {
      this.skipToken = true; // đã refresh mà vẫn bị từ chối: xem như khách
    }
    this.connect();
  }

  private scheduleReconnect() {
    this.options.onStatus("reconnecting");
    const delay = backoffDelay(this.attempt++, this.options.random);
    this.retryTimer = setTimeout(() => this.connect(), delay);
  }

  private startHeartbeat() {
    this.clearHeartbeat();
    this.pingTimer = setInterval(() => {
      this.send({ type: "ping" });
      this.pongTimer ??= setTimeout(() => this.dropAndReconnect(), PONG_TIMEOUT_MS);
    }, PING_INTERVAL_MS);
  }

  private clearHeartbeat() {
    clearInterval(this.pingTimer);
    clearTimeout(this.pongTimer);
    this.pingTimer = undefined;
    this.pongTimer = undefined;
  }

  /** Kết nối "chết" (half-open) có thể không bao giờ phát onclose: tự bỏ và nối lại */
  private dropAndReconnect() {
    this.detach();
    this.scheduleReconnect();
  }

  private detach() {
    this.clearHeartbeat();
    const ws = this.ws;
    this.ws = null;
    if (!ws) return;
    ws.onopen = null;
    ws.onmessage = null;
    ws.onclose = null;
    ws.onerror = null;
    try {
      ws.close();
    } catch {
      /* đã đóng */
    }
  }

  private send(payload: object) {
    if (this.ws?.readyState === WS_OPEN) this.ws.send(JSON.stringify(payload));
  }

  /** Có mạng lại / quay về tab: đang chờ backoff thì nối ngay, còn không thì đồng bộ lại */
  private wakeUp = () => {
    if (this.stopped) return;
    if (this.retryTimer !== undefined) {
      clearTimeout(this.retryTimer);
      this.connect();
    } else {
      this.send({ type: "resync" });
    }
  };

  private onVisibility = () => {
    if (document.visibilityState === "visible") this.wakeUp();
  };
}