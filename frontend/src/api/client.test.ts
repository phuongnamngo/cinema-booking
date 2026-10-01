import { apiBlob } from "./client";

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