import { describe, expect, it } from "vitest";
import { accessDecision } from "./access";

describe("accessDecision", () => {
  it("chờ khôi phục phiên trước khi quyết định", () => {
    expect(accessDecision("loading", undefined, ["admin"])).toBe("loading");
  });

  it("khách chưa đăng nhập thì được đưa đến trang đăng nhập", () => {
    expect(accessDecision("anonymous", undefined, ["staff", "admin"])).toBe("login");
  });

  it("đúng vai trò thì cho qua, sai vai trò thì báo 403 (không redirect)", () => {
    expect(accessDecision("authenticated", "staff", ["staff", "admin"])).toBe("allow");
    expect(accessDecision("authenticated", "admin", ["admin"])).toBe("allow");
    expect(accessDecision("authenticated", "customer", ["staff", "admin"])).toBe("forbidden");
    expect(accessDecision("authenticated", "staff", ["admin"])).toBe("forbidden");
  });

  it("đã đăng nhập nhưng chưa có thông tin vai trò thì từ chối", () => {
    expect(accessDecision("authenticated", undefined, ["admin"])).toBe("forbidden");
  });
});