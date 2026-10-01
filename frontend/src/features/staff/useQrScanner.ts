import { useEffect, useRef, useState } from "react";

export type ScannerStatus = "starting" | "scanning" | "denied" | "unsupported" | "error";

type Decoder = (video: HTMLVideoElement, canvas: HTMLCanvasElement) => Promise<string | null>;

async function createDecoder(): Promise<Decoder> {
  // Ưu tiên API gốc của trình duyệt (nhanh). Chrome Linux/Windows và Firefox chưa có
  if ("BarcodeDetector" in window) {
    try {
      const detector = new BarcodeDetector({ formats: ["qr_code"] });
      return async (video) => (await detector.detect(video))[0]?.rawValue ?? null;
    } catch {
      /* khai báo có nhưng không dùng được: rơi xuống jsQR */
    }
  }

  const { default: jsQR } = await import("jsqr"); // chỉ tải khi cần
  return async (video, canvas) => {
    if (!video.videoWidth || !video.videoHeight) return null;
    const scale = Math.min(1, 640 / video.videoWidth); // thu nhỏ cho nhanh
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
    return jsQR(image.data, image.width, image.height)?.data ?? null;
  };
}

const isPermissionError = (error: unknown) =>
  error instanceof DOMException && (error.name === "NotAllowedError" || error.name === "SecurityError");

interface Options {
  onScan: (value: string) => void;
  /** true: camera vẫn bật nhưng không giải mã (đang hiển thị kết quả) */
  paused: boolean;
}

export function useQrScanner({ onScan, paused }: Options) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [status, setStatus] = useState<ScannerStatus>("starting");

  // Giữ giá trị mới nhất trong ref để effect bên dưới chỉ chạy MỘT lần (không bật tắt camera mỗi lần render)
  const onScanRef = useRef(onScan);
  const pausedRef = useRef(paused);
  useEffect(() => {
    onScanRef.current = onScan;
    pausedRef.current = paused;
  });

  useEffect(() => {
    let cancelled = false;
    let stream: MediaStream | null = null;
    let timer: number | undefined;

    async function start() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setStatus("unsupported"); // thường do không phải HTTPS/localhost
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } }, // ưu tiên camera sau trên điện thoại
          audio: false,
        });
      } catch (error) {
        if (!cancelled) setStatus(isPermissionError(error) ? "denied" : "error");
        return;
      }
      const video = videoRef.current;
      if (cancelled || !video) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }

      video.srcObject = stream;
      await video.play().catch(() => {}); // bị ngắt bởi cleanup (StrictMode): bỏ qua
      const decode = await createDecoder();
      if (cancelled) return;
      setStatus("scanning");

      const canvas = document.createElement("canvas");
      let busy = false;
      timer = window.setInterval(async () => {
        if (busy || pausedRef.current || video.readyState < 2) return;
        busy = true;
        try {
          const value = await decode(video, canvas);
          if (value) onScanRef.current(value);
        } catch {
          /* khung hình lỗi: thử lại ở lần sau */
        } finally {
          busy = false;
        }
      }, 250);
    }

    void start();
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      stream?.getTracks().forEach((t) => t.stop()); // tắt đèn camera
    };
  }, []);

  return { videoRef, status };
}