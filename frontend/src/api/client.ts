import { tokens } from "@/auth/tokens";

const BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, data: unknown) {
    super(extractMessage(data) ?? `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

/** Lấy 1 câu thông báo từ các dạng lỗi của DRF: {detail}, {field: [msg]}, [msg] */
function extractMessage(data: unknown): string | null {
  if (Array.isArray(data)) return typeof data[0] === "string" ? data[0] : null;
  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;
    if (typeof obj.detail === "string") return obj.detail;
    for (const value of Object.values(obj)) {
      const first = Array.isArray(value) ? value[0] : value;
      if (typeof first === "string") return first;
    }
  }
  return null;
}

/** Lỗi theo từng field ({password: "..."}) để gắn vào form */
export function getFieldErrors(error: unknown): Record<string, string> {
  if (
    !(error instanceof ApiError) ||
    typeof error.data !== "object" ||
    error.data === null ||
    Array.isArray(error.data)
  ) {
    return {};
  }
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(error.data)) {
    const messages = (Array.isArray(value) ? value : [value]).filter(
      (m): m is string => typeof m === "string",
    );
    if (messages.length) result[key] = messages.join(" ");
  }
  return result;
}

// ---- Refresh token ----

let onSessionExpired: (() => void) | null = null;

/** Store đăng ký callback này để chuyển sang trạng thái khách khi phiên hết hạn */
export function setSessionExpiredHandler(handler: (() => void) | null) {
  onSessionExpired = handler;
}

/** Trả access mới, hoặc null nếu server TỪ CHỐI refresh token. Lỗi mạng/5xx thì ném lỗi. */
async function requestNewTokens(refresh: string): Promise<string | null> {
  const res = await fetch(`${BASE}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (res.status === 401) return null;
  const data = await parseBody(res);
  if (!res.ok) throw new ApiError(res.status, data);
  const pair = data as { access: string; refresh?: string };
  tokens.set(pair.access, pair.refresh ?? refresh); // rotation: luôn lưu refresh token mới
  return pair.access;
}

async function doRefresh(): Promise<string | null> {
  const used = tokens.getRefresh();
  if (!used) return null;

  let access = await requestNewTokens(used);
  if (!access) {
    // Tab khác có thể vừa xoay refresh token: thử lại bằng token mới nhất trong storage
    const latest = tokens.getRefresh();
    if (latest && latest !== used) access = await requestNewTokens(latest);
  }
  if (!access) {
    tokens.clear();
    onSessionExpired?.();
  }
  return access;
}

let inflight: Promise<string | null> | null = null;

/** Single-flight: mọi nơi cần refresh cùng chờ MỘT lần gọi */
export function refreshAccessToken(): Promise<string | null> {
  inflight ??= doRefresh().finally(() => {
    inflight = null;
  });
  return inflight;
}

// ---- Request ----

type Params = Record<string, string | number | boolean | null | undefined>;

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  params?: Params;
  /** false: không gửi token và không tự refresh (login, register, logout) */
  auth?: boolean;
  signal?: AbortSignal;
}

function buildUrl(path: string, params?: Params): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const qs = query.toString();
  return `${BASE}${path}${qs ? `?${qs}` : ""}`;
}

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null; // vd: trang HTML lỗi 502 từ proxy
  }
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, params, auth = true, signal } = options;
  const url = buildUrl(path, params);

  const send = (token: string | null) => {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (token) headers.Authorization = `Bearer ${token}`;
    return fetch(url, {
      method,
      headers,
      signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  };

  const sentToken = auth ? tokens.getAccess() : null;
  let res = await send(sentToken);

  if (res.status === 401 && auth && sentToken) {
    // Nếu request khác vừa refresh xong (token đã đổi) thì dùng luôn, không refresh nữa
    const current = tokens.getAccess();
    const fresh = current && current !== sentToken ? current : await refreshAccessToken();
    if (fresh) res = await send(fresh);
  }

  const data = await parseBody(res);
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}