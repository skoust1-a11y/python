import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import type { Role } from "../api/types";

export function RoleRoute({ allow }: { allow: Role[] }) {
  const { user } = useAuth();
  if (!user || !allow.includes(user.role)) return <Navigate to="/app" replace />;
  return <Outlet />;
}
