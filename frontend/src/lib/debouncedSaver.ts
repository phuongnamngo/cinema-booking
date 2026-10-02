export type SaverStatus = "idle" | "waiting" | "saving";

export interface DebouncedSaverOptions<T> {
  delayMs: number;
  /** Lưu một giá trị. Được gọi TUẦN TỰ: không bao giờ có hai lần lưu chạy chồng nhau */
  save: (value: T) => Promise<void>;
  /** Một lần lưu thất bại. Mọi thay đổi đang chờ đã bị bỏ */
  onError: (error: unknown) => void;
  onStatus: (status: SaverStatus) => void;
}

export class DebouncedSaver<T> {
  private readonly options: DebouncedSaverOptions<T>;
  private latest: T | undefined;
  private hasPending = false;
  private saving = false;
  private disposed = false;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private status: SaverStatus = "idle";

  constructor(options: DebouncedSaverOptions<T>) {
    this.options = options;
  }

  /** Ghi nhớ giá trị mới nhất và (đặt lại) bộ đếm. Nhiều lần gọi liên tiếp = một lần lưu */
  schedule(value: T) {
    this.latest = value;
    this.hasPending = true;
    clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      this.timer = undefined;
      void this.run();
    }, this.options.delayMs);
    this.setStatus(this.saving ? "saving" : "waiting");
  }

  /** Tháo bỏ: còn thay đổi chưa gửi thì gửi ngay thay vì làm mất (vd rời trang lúc đang chờ) */
  dispose() {
    this.disposed = true;
    if (!this.hasPending) return;
    clearTimeout(this.timer);
    this.timer = undefined;
    void this.run(); // đang có lần lưu chạy thì run() tự bỏ qua, lần lưu đó xong sẽ gửi tiếp
  }

  private async run() {
    if (this.saving || !this.hasPending) return;
    const value = this.latest as T;
    this.hasPending = false;
    this.latest = undefined;
    this.saving = true;
    this.setStatus("saving");

    try {
      await this.options.save(value);
    } catch (error) {
      // Các thay đổi sau đó dựa trên trạng thái mà server vừa từ chối: bỏ hết
      this.saving = false;
      this.hasPending = false;
      this.latest = undefined;
      clearTimeout(this.timer);
      this.timer = undefined;
      this.setStatus("idle");
      if (!this.disposed) this.options.onError(error);
      return;
    }

    this.saving = false;
    if (!this.hasPending) {
      this.setStatus("idle");
    } else if (this.timer === undefined) {
      void this.run(); // bộ đếm đã nổ trong lúc đang lưu (và bị bỏ qua): gửi tiếp ngay
    } else {
      this.setStatus("waiting"); // bộ đếm chưa nổ: chờ đủ thời gian rồi mới gửi
    }
  }

  private setStatus(next: SaverStatus) {
    if (next === this.status) return;
    this.status = next;
    if (!this.disposed) this.options.onStatus(next); // sau dispose không đụng đến state của React nữa
  }
}