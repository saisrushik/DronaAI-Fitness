import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <p className="py-20 text-center text-slate-500">Loading…</p>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  // First-time users must complete their profile before anything else.
  if (!user.profile_completed && location.pathname !== "/profile") {
    return <Navigate to="/profile" replace />;
  }
  return <Outlet />;
}
