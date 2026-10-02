import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DebouncedSaver } from "./debouncedSaver";

function deferred() {
  let resolve!: () => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<void>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("DebouncedSaver", () => {
  it("gộp các lần sửa liên tiếp thành MỘT lần lưu với giá trị mới nhất", async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const statuses: string[] = [];
    const saver = new DebouncedSaver<number>({
      delayMs: 500, save, onError: vi.fn(), onStatus: (s) => statuses.push(s),
    });

    saver.schedule(1);
    await vi.advanceTimersByTimeAsync(300);
    saver.schedule(2); // đặt lại bộ đếm
    await vi.advanceTimersByTimeAsync(300);
    expect(save).not.toHaveBeenCalled(); // đã 600ms từ lần đầu, nhưng mới 300ms từ lần sửa cuối

    await vi.advanceTimersByTimeAsync(200);
    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith(2);
    expect(statuses).toEqual(["waiting", "saving", "idle"]);
  });

  it("không bao giờ chạy hai lần lưu chồng nhau, và gộp các thay đổi xảy ra trong lúc đang lưu", async () => {
    const gates: ReturnType<typeof deferred>[] = [];
    const saved: number[] = [];
    let running = 0;
    let maxRunning = 0;
    const saver = new DebouncedSaver<number>({
      delayMs: 100,
      save: async (value) => {
        running++;
        maxRunning = Math.max(maxRunning, running);
        saved.push(value);
        const gate = deferred();
        gates.push(gate);
        await gate.promise;
        running--;
      },
      onError: vi.fn(),
      onStatus: vi.fn(),
    });

    saver.schedule(1);
    await vi.advanceTimersByTimeAsync(100); // save(1) bắt đầu
    expect(saved).toEqual([1]);

    saver.schedule(2);
    await vi.advanceTimersByTimeAsync(50);
    saver.schedule(3); // gộp: giá trị 2 không bao giờ được gửi
    await vi.advanceTimersByTimeAsync(100); // bộ đếm nổ nhưng save(1) chưa xong
    expect(saved).toEqual([1]);

    gates[0].resolve();
    await vi.advanceTimersByTimeAsync(0);
    expect(saved).toEqual([1, 3]);

    gates[1].resolve();
    await vi.advanceTimersByTimeAsync(0);
    expect(maxRunning).toBe(1);
  });

  it("sửa tiếp khi đang lưu mà bộ đếm chưa nổ: vẫn chờ đủ thời gian rồi mới lưu lần kế", async () => {
    const gates: ReturnType<typeof deferred>[] = [];
    const saved: number[] = [];
    const saver = new DebouncedSaver<number>({
      delayMs: 100,
      save: async (value) => {
        saved.push(value);
        const gate = deferred();
        gates.push(gate);
        await gate.promise;
      },
      onError: vi.fn(),
      onStatus: vi.fn(),
    });

    saver.schedule(1);
    await vi.advanceTimersByTimeAsync(100); // save(1) đang chạy
    saver.schedule(2); // bộ đếm sẽ nổ sau 100ms
    gates[0].resolve();
    await vi.advanceTimersByTimeAsync(0); // save(1) xong, nhưng chưa đến giờ gửi giá trị 2

    await vi.advanceTimersByTimeAsync(99);
    expect(saved).toEqual([1]);
    await vi.advanceTimersByTimeAsync(1);
    expect(saved).toEqual([1, 2]);
  });

  it("lưu lỗi: báo đúng một lần và bỏ mọi thay đổi đang chờ", async () => {
    const gate = deferred();
    const save = vi.fn(() => gate.promise);
    const onError = vi.fn();
    const saver = new DebouncedSaver<number>({
      delayMs: 100, save, onError, onStatus: vi.fn(),
    });

    saver.schedule(1);
    await vi.advanceTimersByTimeAsync(100);
    saver.schedule(2); // sửa tiếp khi lần lưu đầu còn đang chạy
    gate.reject(new Error("boom"));
    await vi.advanceTimersByTimeAsync(1_000);

    expect(onError).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledTimes(1); // giá trị 2 dựa trên trạng thái server vừa từ chối: bỏ
  });

  it("dispose gửi ngay thay đổi còn chờ và không gọi callback nữa", async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const onStatus = vi.fn();
    const saver = new DebouncedSaver<number>({
      delayMs: 500, save, onError: vi.fn(), onStatus,
    });

    saver.schedule(7);
    onStatus.mockClear();
    saver.dispose(); // vd: người dùng rời trang khi đang chờ debounce
    expect(save).toHaveBeenCalledWith(7);

    await vi.advanceTimersByTimeAsync(1_000);
    expect(save).toHaveBeenCalledTimes(1);
    expect(onStatus).not.toHaveBeenCalled(); // component đã unmount: không đụng đến state nữa
  });
});