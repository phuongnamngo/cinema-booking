import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { refreshAccessToken } from "@/api/client";
import { tokens } from "@/auth/tokens";
import { backoffDelay, SeatSocket, type ConnectionStatus } from "./seatSocket";
import type { SeatServerMessage } from "./seatState";

vi.mock("@/api/client", () => ({ refreshAccessToken: vi.fn() }));

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  url: string;
  readyState = 0;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.readyState = 3;
  }
  // --- phía "server" ---
  open() {
    this.readyState = 1;
    this.onopen?.();
  }
  receive(message: unknown) {
    this.onmessage?.({ data: JSON.stringify(message) });
  }
  serverClose(code: number) {
    this.readyState = 3;
    this.onclose?.({ code });
  }
}

const SNAPSHOT = { type: "snapshot", showtime_id: 7, held: [], mine: [], sold: [] };
const instances = () => FakeWebSocket.instances;
const last = () => FakeWebSocket.instances[FakeWebSocket.instances.length - 1];

function setup() {
  const messages: SeatServerMessage[] = [];
  const statuses: ConnectionStatus[] = [];
  const socket = new SeatSocket({
    showtimeId: 7,
    onMessage: (m) => messages.push(m),
    onStatus: (s) => statuses.push(s),
    random: () => 0, // độ trễ cố định = một nửa mức trần
  });
  socket.start();
  return { socket, messages, statuses };
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("WebSocket", FakeWebSocket);
  FakeWebSocket.instances = [];
  tokens.clear();
  vi.mocked(refreshAccessToken).mockReset();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("backoffDelay", () => {
  it("tăng gấp đôi, có jitter, chặn ở 30 giây", () => {
    expect(backoffDelay(0, () => 0)).toBe(500);
    expect(backoffDelay(0, () => 1)).toBe(1_000);
    expect(backoffDelay(3, () => 1)).toBe(8_000);
    expect(backoffDelay(20, () => 1)).toBe(30_000);
    expect(backoffDelay(20, () => 0)).toBe(15_000);
  });
});

describe("SeatSocket", () => {
  it("gắn access token vào URL, không có token thì không gắn", () => {
    tokens.set("access-1", "refresh-1");
    setup();
    expect(last().url).toMatch(/^ws:\/\/[^/]+\/ws\/showtimes\/7\/seats\/\?token=access-1$/);

    tokens.clear();
    setup();
    expect(last().url).not.toContain("token=");
  });

  it("snapshot: chuyển sang open và chuyển message ra ngoài", () => {
    const { messages, statuses } = setup();
    last().open();
    last().receive(SNAPSHOT);
    expect(statuses).toEqual(["open"]);
    expect(messages).toEqual([SNAPSHOT]);
  });

  it("bỏ qua message rác mà không sập", () => {
    const { messages } = setup();
    last().open();
    last().onmessage?.({ data: "đây không phải JSON" });
    last().receive({ khong: "co type" });
    expect(messages).toEqual([]);
  });

  it("đứt kết nối: nối lại theo backoff, và reset khi nhận snapshot", async () => {
    const { statuses } = setup();
    last().open();
    last().serverClose(1006);
    expect(statuses.at(-1)).toBe("reconnecting");

    await vi.advanceTimersByTimeAsync(499);
    expect(instances()).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(instances()).toHaveLength(2); // lần 1: 500ms

    last().serverClose(1006); // thất bại tiếp, chưa có snapshot
    await vi.advanceTimersByTimeAsync(999);
    expect(instances()).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(1);
    expect(instances()).toHaveLength(3); // lần 2: 1000ms

    last().open();
    last().receive(SNAPSHOT); // kết nối tốt: backoff về đầu
    last().serverClose(1006);
    await vi.advanceTimersByTimeAsync(500);
    expect(instances()).toHaveLength(4);
  });

  it("4404: báo unavailable và không bao giờ nối lại", async () => {
    const { statuses } = setup();
    last().open();
    last().serverClose(4404);
    expect(statuses.at(-1)).toBe("unavailable");
    await vi.advanceTimersByTimeAsync(120_000);
    expect(instances()).toHaveLength(1);
  });

  it("4401: refresh token rồi nối lại; bị từ chối lần hai thì nối như khách", async () => {
    tokens.set("access-1", "refresh-1");
    vi.mocked(refreshAccessToken).mockImplementation(async () => {
      tokens.set("access-2", "refresh-2");
      return "access-2";
    });
    setup();

    last().serverClose(4401);
    await vi.advanceTimersByTimeAsync(0);
    expect(refreshAccessToken).toHaveBeenCalledTimes(1);
    expect(instances()).toHaveLength(2);
    expect(last().url).toContain("token=access-2");

    last().serverClose(4401); // token mới vẫn bị từ chối
    await vi.advanceTimersByTimeAsync(0);
    expect(refreshAccessToken).toHaveBeenCalledTimes(1); // không refresh lần nữa
    expect(instances()).toHaveLength(3);
    expect(last().url).not.toContain("token=");
  });

  it("heartbeat: ping định kỳ, không có phản hồi thì bỏ socket và nối lại", async () => {
    const { statuses } = setup();
    const first = last();
    first.open();

    await vi.advanceTimersByTimeAsync(25_000);
    expect(first.sent).toEqual([JSON.stringify({ type: "ping" })]);
    first.receive({ type: "pong" });
    await vi.advanceTimersByTimeAsync(10_000);
    expect(instances()).toHaveLength(1); // có pong nên vẫn sống

    await vi.advanceTimersByTimeAsync(15_000); // t=50s: ping thứ hai, lần này không có pong
    await vi.advanceTimersByTimeAsync(10_000); // quá hạn chờ pong
    expect(statuses.at(-1)).toBe("reconnecting");
    expect(first.readyState).toBe(3);
    await vi.advanceTimersByTimeAsync(500);
    expect(instances()).toHaveLength(2);
  });

  it("có mạng lại: nối ngay khi đang chờ backoff, hoặc gửi resync khi đang mở", async () => {
    setup();
    last().open();
    window.dispatchEvent(new Event("online"));
    expect(last().sent).toContain(JSON.stringify({ type: "resync" }));

    last().serverClose(1006);
    window.dispatchEvent(new Event("online"));
    expect(instances()).toHaveLength(2); // không chờ hết 500ms
  });

  it("stop(): đóng socket và không nối lại nữa", async () => {
    const { socket } = setup();
    last().open();
    socket.stop();
    expect(last().readyState).toBe(3);
    await vi.advanceTimersByTimeAsync(120_000);
    expect(instances()).toHaveLength(1);

    const second = setup();
    last().serverClose(1006);
    second.socket.stop(); // dừng lúc đang chờ backoff
    await vi.advanceTimersByTimeAsync(120_000);
    expect(instances()).toHaveLength(2);
  });
});