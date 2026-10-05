import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function PublicOnlyRoute() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="boot">Loading session…</div>;
  if (user) return <Navigate to="/app" replace />;
  return <Outlet />;
}
