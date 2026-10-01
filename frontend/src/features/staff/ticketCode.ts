import { ApiError } from "@/api/client";

const CODE_PATTERN = /^[A-Z0-9]{6,12}$/;

/** Dữ liệu từ QR hoặc ô nhập đều là input không tin cậy: chuẩn hóa và kiểm tra trước khi gọi API */
export function normalizeTicketCode(raw: string): string | null {
  const code = raw.trim().toUpperCase();
  return CODE_PATTERN.test(code) ? code : null;
}

export interface TicketRejection {
  reason: string;
  message: string;
  checkedInBy?: string;
  checkedInAt?: string;
}

/** Đọc lỗi 409 của check-in (backend gửi kèm `reason`). Lỗi khác trả về null */
export function getTicketRejection(error: unknown): TicketRejection | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null;
  if (!error.data || typeof error.data !== "object") return null;
  const data = error.data as Record<string, unknown>;
  if (typeof data.reason !== "string") return null;
  return {
    reason: data.reason,
    message: typeof data.detail === "string" ? data.detail : error.message,
    checkedInBy: typeof data.checked_in_by === "string" ? data.checked_in_by : undefined,
    checkedInAt: typeof data.checked_in_at === "string" ? data.checked_in_at : undefined,
  };
}