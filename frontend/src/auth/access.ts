import type { Role } from "@/api/types";

export type AccessDecision = "loading" | "login" | "forbidden" | "allow";

/** Hàm thuần: dễ test. Nhớ rằng đây chỉ là UX, backend mới là nơi chặn thật. */
export function accessDecision(
  status: "loading" | "authenticated" | "anonymous",
  role: Role | null | undefined,
  allowed: readonly Role[],
): AccessDecision {
  if (status === "loading") return "loading";
  if (status === "anonymous") return "login";
  return role && allowed.includes(role) ? "allow" : "forbidden";
}