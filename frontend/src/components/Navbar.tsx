import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { APP_INITIALS, APP_NAME } from "../config/brand";
import { useAuth, type Role } from "../context/AuthContext";

interface NavItem {
  to: string;
  label: string;
  /** When set, only shown to this role. */
  role?: Role;
}

const navItems: NavItem[] = [
  { to: "/", label: "Home" },
  { to: "/profile", label: "Profile" },
  { to: "/chat", label: "Chat Assistant" },
  { to: "/customers", label: "My Customers", role: "coach" },
  { to: "/workout-plan", label: "Workout Plan", role: "customer" },
  { to: "/diet-plan", label: "Diet Plan", role: "customer" },
];

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 text-lg font-bold text-slate-900">
      <span className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-white">
        {APP_INITIALS}
      </span>
      {APP_NAME}
    </Link>
  );
}

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    setMenuOpen(false);
    navigate("/");
  };

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-2 text-sm font-medium transition ${
      isActive ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100"
    }`;

  const shell = "sticky top-0 z-20 border-b border-slate-200 bg-white/80 backdrop-blur";
  const bar = "mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3";

  if (!user) {
    return (
      <header className={shell}>
        <nav className={bar}>
          <Logo />
          <div className="flex items-center gap-2">
            <Link to="/login" className="btn-secondary">
              Log in
            </Link>
            <Link to="/register" className="btn-primary">
              Sign up
            </Link>
          </div>
        </nav>
      </header>
    );
  }

  const visibleItems = navItems.filter((item) => !item.role || item.role === user.role);

  return (
    <header className={shell}>
      <nav className={bar}>
        <Logo />

        <div className="hidden items-center gap-1 md:flex">
          {visibleItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={linkClass}>
              {item.label}
            </NavLink>
          ))}
        </div>

        <div className="hidden items-center gap-3 md:flex">
          <span className="text-sm text-slate-600">
            {user.full_name}
            <span className="ml-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs capitalize">
              {user.role}
            </span>
          </span>
          <button onClick={handleLogout} className="btn-secondary">
            Log out
          </button>
        </div>

        <button
          onClick={() => setMenuOpen((open) => !open)}
          className="btn-secondary md:hidden"
          aria-label="Toggle menu"
        >
          Menu
        </button>
      </nav>

      {menuOpen && (
        <div className="flex flex-col gap-1 border-t border-slate-200 px-4 py-3 md:hidden">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={linkClass}
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
          <button onClick={handleLogout} className="btn-secondary mt-2">
            Log out
          </button>
        </div>
      )}
    </header>
  );
}
