import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { APP_INITIALS, APP_NAME } from "../config/brand";
import { useAuth, type Role } from "../context/AuthContext";
import NotificationBell from "./NotificationBell";

interface NavItem {
  to: string;
  label: string;
  description?: string;
  /** When set, only shown to this role. */
  role?: Role;
}

interface NavGroup {
  label: string;
  role?: Role;
  items: NavItem[];
}

type NavEntry = NavItem | NavGroup;

const isGroup = (entry: NavEntry): entry is NavGroup => "items" in entry;

// The logo links home and Profile sits beside the notification bell.
const navEntries: NavEntry[] = [
  { to: "/customers", label: "My Customers", role: "coach" },
  {
    label: "Plans",
    role: "customer",
    items: [
      { to: "/workout-plan", label: "Workout Plans", description: "Your weekly training split" },
      { to: "/diet-plan", label: "Diet Plans", description: "Meals, macros and meal requests" },
    ],
  },
  {
    label: "Tracking",
    role: "customer",
    items: [
      { to: "/progress", label: "Progress Tracking", description: "Daily workouts, meals and how you feel" },
      { to: "/monitoring", label: "Monitoring", description: "Body measurement trends" },
    ],
  },
  { to: "/my-coach", label: "My Coach", role: "customer" },
  { to: "/requests", label: "Requests" },
  { to: "/chat", label: "Chat Assistant" },
];

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
      fill="none"
      stroke="currentColor"
      strokeWidth={2.2}
      aria-hidden
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 9l6 6 6-6" />
    </svg>
  );
}

function NavDropdown({ group, pathname }: { group: NavGroup; pathname: string }) {
  const [open, setOpen] = useState(false);
  const wrapper = useRef<HTMLDivElement>(null);
  const active = group.items.some((item) => pathname.startsWith(item.to));

  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (!wrapper.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={wrapper} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        className={`flex items-center gap-1 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition lg:px-2.5 xl:px-3 ${
          active || open ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100"
        }`}
      >
        {group.label}
        <Chevron open={open} />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute left-0 top-full z-30 mt-2 w-64 overflow-hidden rounded-2xl border border-slate-200 bg-white p-1.5 shadow-xl"
        >
          {group.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              role="menuitem"
              className={({ isActive }) =>
                `block rounded-xl px-3 py-2.5 transition ${
                  isActive ? "bg-indigo-50" : "hover:bg-slate-50"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={`block text-sm font-medium ${
                      isActive ? "text-indigo-700" : "text-slate-800"
                    }`}
                  >
                    {item.label}
                  </span>
                  {item.description && (
                    <span className="block text-xs text-slate-500">{item.description}</span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

function Logo() {
  return (
    <Link to="/" className="flex shrink-0 items-center gap-2 text-lg font-bold text-slate-900">
      <span className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-sm text-white">
        {APP_INITIALS}
      </span>
      {APP_NAME}
    </Link>
  );
}

export default function Navbar() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const handleLogout = async () => {
    await logout();
    setMenuOpen(false);
    navigate("/");
  };

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition lg:px-2.5 xl:px-3 ${
      isActive ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100"
    }`;

  const shell = "sticky top-0 z-20 border-b border-slate-200 bg-white/80 backdrop-blur";
  const bar = "mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8";

  if (loading) {
    return (
      <header className={shell}>
        <nav className={bar}>
          <Logo />
        </nav>
      </header>
    );
  }

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

  const visibleEntries = navEntries.filter((entry) => !entry.role || entry.role === user.role);
  const initials =
    `${user.first_name[0] ?? ""}${user.last_name[0] ?? ""}`.toUpperCase() || "?";

  return (
    <header className={shell}>
      <nav className={bar}>
        <Logo />

        <div className="hidden items-center gap-1 lg:flex">
          {visibleEntries.map((entry) =>
            isGroup(entry) ? (
              <NavDropdown key={entry.label} group={entry} pathname={location.pathname} />
            ) : (
              <NavLink key={entry.to} to={entry.to} className={linkClass}>
                {entry.label}
              </NavLink>
            ),
          )}
        </div>

        <div className="flex min-w-0 items-center gap-2 lg:gap-3">
          <NotificationBell />
          <NavLink
            to="/profile"
            title="Profile"
            aria-label={`Profile: ${user.full_name}`}
            className={({ isActive }) =>
              `flex min-w-0 items-center gap-2 rounded-full border py-1 pl-1 pr-1 transition xl:pr-3 ${
                isActive
                  ? "border-indigo-300 bg-indigo-50"
                  : "border-slate-200 bg-white hover:border-indigo-200 hover:bg-slate-50"
              }`
            }
          >
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-indigo-600 text-xs font-bold text-white">
              {initials}
            </span>
            <span className="hidden min-w-0 flex-col leading-tight xl:flex">
              <span className="truncate text-sm font-medium text-slate-800">{user.full_name}</span>
              <span className="text-[11px] capitalize text-slate-500">{user.role}</span>
            </span>
          </NavLink>
          <button onClick={handleLogout} className="btn-secondary hidden lg:inline-flex">
            Log out
          </button>

          <button
            onClick={() => setMenuOpen((open) => !open)}
            className="btn-secondary px-3 lg:hidden"
            aria-label="Toggle menu"
            aria-expanded={menuOpen}
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
              {menuOpen ? (
                <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
              ) : (
                <path strokeLinecap="round" d="M4 7h16M4 12h16M4 17h16" />
              )}
            </svg>
          </button>
        </div>
      </nav>

      {menuOpen && (
        <div className="flex max-h-[calc(100dvh-4rem)] flex-col gap-1 overflow-y-auto border-t border-slate-200 bg-white px-4 py-3 sm:px-6 lg:hidden">
          <p className="mb-2 flex items-center gap-2 px-3 text-sm text-slate-600">
            <span className="truncate">{user.full_name}</span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs capitalize">
              {user.role}
            </span>
          </p>
          {visibleEntries.map((entry) =>
            isGroup(entry) ? (
              <div key={entry.label} className="mt-1">
                <p className="px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {entry.label}
                </p>
                <div className="flex flex-col gap-1 border-l-2 border-slate-100 pl-2">
                  {entry.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={linkClass}
                      onClick={() => setMenuOpen(false)}
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              </div>
            ) : (
              <NavLink
                key={entry.to}
                to={entry.to}
                className={linkClass}
                onClick={() => setMenuOpen(false)}
              >
                {entry.label}
              </NavLink>
            ),
          )}
          <button onClick={handleLogout} className="btn-secondary mt-2">
            Log out
          </button>
        </div>
      )}
    </header>
  );
}
