import { describe, expect, it } from "vitest";
import { formatTime, formatVnd, toDateParam, formatCountdown, formatDateTime } from "./format";

describe("format", () => {
    it("toDateParam dùng ngày theo giờ máy, không lệch sang UTC", () => {
        // 00:30 ngày 5/10 theo giờ máy. toISOString() sẽ ra ngày 4/10 ở múi giờ +07
        expect(toDateParam(new Date(2026, 9, 5, 0, 30))).toBe("2026-10-05");
    });

    it("formatTime luôn hiển thị giờ Việt Nam", () => {
        expect(formatTime("2026-10-05T12:30:00Z")).toBe("19:30");
    });

    it("formatVnd", () => {
        expect(formatVnd(80000)).toMatch(/^80\.000\s?₫$/);
    });

    it("formatCountdown", () => {
        expect(formatCountdown(600)).toBe("10:00");
        expect(formatCountdown(65)).toBe("01:05");
        expect(formatCountdown(0)).toBe("00:00");
        expect(formatCountdown(-5)).toBe("00:00");
    });

    it("formatDateTime luôn theo giờ Việt Nam", () => {
        const text = formatDateTime("2026-10-05T12:30:00Z");
        expect(text).toContain("19:30");
        expect(text).toContain("05/10/2026");
    });
});