import { formatCountdown, formatDateTime } from "./format";

describe("format (bước 11)", () => {
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