import { Navigate, Outlet, useLocation } from "react-router";
import { Spinner } from "@/components/ui";
import { useAuth } from "./store";

export function RequireAuth() {
  const status = useAuth((s) => s.status);
  const location = useLocation();

  if (status === "loading") return <Spinner />;
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return <Outlet />;
}