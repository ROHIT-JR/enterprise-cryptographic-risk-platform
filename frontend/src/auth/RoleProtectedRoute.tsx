import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { hasAnyRole } from "./permissions";
import type { UserRole } from "../types/api";

/** Guards a route by role, independent of whether it happens to appear in
 * the sidebar — closes the gap where a lower-privileged user could still
 * reach a restricted page by typing its URL directly. */
export function RoleProtectedRoute({ allowed }: { allowed: UserRole[] }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return hasAnyRole(user.role, allowed) ? <Outlet /> : <Navigate to="/" replace />;
}
