import { Suspense } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
import type { Role } from "@/api/types";
import { Forbidden, Spinner } from "@/components/ui";
import { accessDecision } from "./access";
import { useAuth } from "./store";

export function RequireRole({ roles }: { roles: readonly Role[] }) {
  const status = useAuth((s) => s.status);
  const role = useAuth((s) => s.user?.role);
  const location = useLocation();

  switch (accessDecision(status, role, roles)) {
    case "loading":
      return <Spinner />;
    case "login":
      return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
    case "forbidden":
      return <Forbidden />;
    case "allow":
      // Suspense cho các trang tải lười (lazy) bên dưới
      return (
        <Suspense fallback={<Spinner />}>
          <Outlet />
        </Suspense>
      );
  }
}