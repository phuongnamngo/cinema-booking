import { describe, expect, it } from "vitest";
import { editsLockedByPendingPayment } from "./pendingPayment";

describe("editsLockedByPendingPayment", () => {
  it("khóa sửa đơn khi server báo payment pending", () => {
    expect(editsLockedByPendingPayment(true)).toBe(true);
  });

  it("không khóa khi không có payment pending", () => {
    expect(editsLockedByPendingPayment(false)).toBe(false);
  });
});
