import { describe, expect, it } from "vitest";
import { ApiError } from "@/api/client";
import { getTicketRejection, normalizeTicketCode } from "./ticketCode";

describe("normalizeTicketCode", () => {
  it("cắt khoảng trắng và viết hoa", () => {
    expect(normalizeTicketCode("  ab3cd4ef \n")).toBe("AB3CD4EF");
  });

  it("từ chối nội dung không phải mã vé", () => {
    for (const bad of ["", "ABC", "https://evil.example/x", "AB CD EF GH", "ABCDEFGHIJKLM", "AB-3CD4E"]) {
      expect(normalizeTicketCode(bad)).toBeNull();
    }
  });
});

describe("getTicketRejection", () => {
  it("đọc lỗi 409 có reason, kèm người quét và giờ quét", () => {
    const error = new ApiError(409, {
      detail: "Vé này đã được sử dụng.",
      reason: "already_checked_in",
      checked_in_by: "staff1",
      checked_in_at: "2026-10-05T19:00:00+07:00",
    });
    expect(getTicketRejection(error)).toEqual({
      reason: "already_checked_in",
      message: "Vé này đã được sử dụng.",
      checkedInBy: "staff1",
      checkedInAt: "2026-10-05T19:00:00+07:00",
    });
  });

  it("lỗi khác (không phải 409 có reason) trả về null", () => {
    expect(getTicketRejection(new ApiError(409, { detail: "Chỉ có thể thao tác với đơn đang chờ." }))).toBeNull();
    expect(getTicketRejection(new ApiError(403, { detail: "Vé này thuộc rạp khác." }))).toBeNull();
    expect(getTicketRejection(new Error("mạng lỗi"))).toBeNull();
    expect(getTicketRejection(null)).toBeNull();
  });
});