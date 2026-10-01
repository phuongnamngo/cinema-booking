import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { REFRESH_KEY, tokens } from "@/auth/tokens";
import { apiBlob, ApiError, apiFetch, setSessionExpiredHandler } from "./client";

interface Req {
    url: string;
    auth?: string;
    body?: Record<string, unknown>;
}

const json = (status: number, body: unknown) =>
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

/** Thay fetch toàn cục, ghi lại các request đã gửi */
function mockFetch(handler: (req: Req) => Response) {
    const requests: Req[] = [];
    vi.stubGlobal("fetch", async (url: string, init?: RequestInit) => {
        const req: Req = {
            url,
            auth: (init?.headers as Record<string, string> | undefined)?.Authorization,
            body: typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
        };
        requests.push(req);
        return handler(req);
    });
    return requests;
}

const isRefresh = (req: Req) => req.url.endsWith("/auth/refresh/");
const onExpired = vi.fn();

// Server giả: chỉ chấp nhận access-2; refresh luôn thành công và cấp access-2
function serverWithExpiredToken(req: Req) {
    if (isRefresh(req)) return json(200, { access: "access-2", refresh: "refresh-2" });
    return req.auth === "Bearer access-2" ? json(200, { ok: true }) : json(401, { detail: "expired" });
}

beforeEach(() => {
    tokens.clear();
    onExpired.mockClear();
    setSessionExpiredHandler(onExpired);
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("apiFetch", () => {
    it("gửi access token trong header Authorization", async () => {
        tokens.set("access-1", "refresh-1");
        const requests = mockFetch(() => json(200, { ok: true }));
        await apiFetch("/movies/");
        expect(requests).toHaveLength(1);
        expect(requests[0].auth).toBe("Bearer access-1");
    });

    it("401: refresh rồi gửi lại với token mới, lưu refresh token đã xoay", async () => {
        tokens.set("access-1", "refresh-1");
        const requests = mockFetch(serverWithExpiredToken);

        await expect(apiFetch("/auth/me/")).resolves.toEqual({ ok: true });

        expect(requests.map((r) => r.url)).toEqual([
            "/api/v1/auth/me/",
            "/api/v1/auth/refresh/",
            "/api/v1/auth/me/",
        ]);
        expect(tokens.getAccess()).toBe("access-2");
        expect(tokens.getRefresh()).toBe("refresh-2");
    });

    it("nhiều request cùng bị 401 chỉ refresh MỘT lần", async () => {
        tokens.set("access-1", "refresh-1");
        const requests = mockFetch(serverWithExpiredToken);

        const results = await Promise.all([apiFetch("/a/"), apiFetch("/b/"), apiFetch("/c/")]);

        expect(results).toEqual([{ ok: true }, { ok: true }, { ok: true }]);
        expect(requests.filter(isRefresh)).toHaveLength(1);
    });

    it("login sai mật khẩu (401) KHÔNG kích hoạt refresh", async () => {
        tokens.set("access-1", "refresh-1");
        const requests = mockFetch(() => json(401, { detail: "No active account" }));

        await expect(
            apiFetch("/auth/login/", { method: "POST", body: {}, auth: false }),
        ).rejects.toMatchObject({ status: 401 });

        expect(requests).toHaveLength(1);
        expect(requests[0].auth).toBeUndefined();
        expect(onExpired).not.toHaveBeenCalled();
        expect(tokens.getAccess()).toBe("access-1");
    });

    it("refresh token bị từ chối: xóa phiên, báo hết hạn, ném ApiError 401", async () => {
        tokens.set("access-1", "refresh-1");
        mockFetch(() => json(401, { detail: "invalid" }));

        await expect(apiFetch("/auth/me/")).rejects.toBeInstanceOf(ApiError);

        expect(tokens.getAccess()).toBeNull();
        expect(tokens.getRefresh()).toBeNull();
        expect(onExpired).toHaveBeenCalledTimes(1);
    });

    it("lỗi mạng khi refresh KHÔNG đăng xuất", async () => {
        tokens.set("access-1", "refresh-1");
        vi.stubGlobal("fetch", async (url: string) => {
            if (url.endsWith("/auth/refresh/")) throw new TypeError("Failed to fetch");
            return json(401, { detail: "expired" });
        });

        await expect(apiFetch("/auth/me/")).rejects.toBeInstanceOf(TypeError);

        expect(tokens.getRefresh()).toBe("refresh-1");
        expect(onExpired).not.toHaveBeenCalled();
    });

    it("tab khác đã xoay refresh token: thử lại bằng token mới nhất", async () => {
        tokens.set("access-1", "refresh-old");
        mockFetch((req) => {
            if (isRefresh(req)) {
                if (req.body?.refresh === "refresh-old") {
                    localStorage.setItem(REFRESH_KEY, "refresh-new"); // tab khác vừa xoay xong
                    return json(401, { detail: "blacklisted" });
                }
                return json(200, { access: "access-2", refresh: "refresh-3" });
            }
            return req.auth === "Bearer access-2" ? json(200, { ok: true }) : json(401, { detail: "expired" });
        });

        await expect(apiFetch("/auth/me/")).resolves.toEqual({ ok: true });

        expect(tokens.getRefresh()).toBe("refresh-3");
        expect(onExpired).not.toHaveBeenCalled();
    });

    it("apiBlob cũng tự refresh khi gặp 401", async () => {
        tokens.set("access-1", "refresh-1");
        mockFetch((req) => {
            if (isRefresh(req)) return json(200, { access: "access-2", refresh: "refresh-2" });
            return req.auth === "Bearer access-2"
                ? new Response("<svg></svg>", { status: 200 })
                : json(401, { detail: "expired" });
        });
        const blob = await apiBlob("/bookings/ABC/qr/");
        expect(await blob.text()).toBe("<svg></svg>");
    });
});