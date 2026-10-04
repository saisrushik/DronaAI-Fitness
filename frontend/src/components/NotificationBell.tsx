import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useNotifications, type AppNotification } from "../context/NotificationsContext";
import { formatDateTime, requestLink } from "../lib/requests";

function timeAgo(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return days < 7 ? `${days}d ago` : formatDateTime(iso);
}

export default function NotificationBell() {
  const { items, unread, refresh, markRead, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const wrapper = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname, location.search]);

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

  const toggle = () => {
    if (!open) void refresh().catch(() => undefined);
    setOpen((o) => !o);
  };

  const openNotification = (notification: AppNotification) => {
    void markRead(notification.id);
    setOpen(false);
    navigate(notification.request_id ? requestLink(notification.request_id) : "/requests");
  };

  return (
    <div ref={wrapper} className="relative">
      <button
        type="button"
        onClick={toggle}
        className="relative grid h-10 w-10 place-items-center rounded-lg text-slate-600 transition hover:bg-slate-100"
        aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
        aria-expanded={open}
      >
        <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2a2 2 0 01-.6 1.4L4 17h5m6 0a3 3 0 11-6 0m6 0H9"
          />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 grid h-5 min-w-5 place-items-center rounded-full bg-red-600 px-1 text-[11px] font-bold leading-none text-white ring-2 ring-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="fixed inset-x-2 top-16 z-30 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl sm:absolute sm:inset-x-auto sm:right-0 sm:top-full sm:mt-2 sm:w-96">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <h2 className="font-semibold text-slate-900">Notifications</h2>
            {unread > 0 && (
              <button
                type="button"
                onClick={() => void markAllRead()}
                className="btn-soft btn-sm"
              >
                Mark all as read
              </button>
            )}
          </div>

          {items.length === 0 ? (
            <p className="px-4 py-10 text-center text-sm text-slate-500">You&apos;re all caught up.</p>
          ) : (
            <ul className="max-h-[60dvh] divide-y divide-slate-100 overflow-y-auto">
              {items.map((notification) => (
                <li key={notification.id}>
                  <button
                    type="button"
                    onClick={() => openNotification(notification)}
                    className={`flex w-full gap-3 px-4 py-3 text-left transition hover:bg-slate-50 ${
                      notification.read_at ? "" : "bg-indigo-50/60"
                    }`}
                  >
                    <span
                      className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                        notification.read_at ? "bg-transparent" : "bg-red-600"
                      }`}
                      aria-hidden
                    />
                    <span className="min-w-0">
                      <span
                        className={`block text-sm ${
                          notification.read_at ? "text-slate-600" : "font-medium text-slate-900"
                        }`}
                      >
                        {notification.message}
                      </span>
                      <span
                        className="text-xs text-slate-500"
                        title={formatDateTime(notification.created_at)}
                      >
                        {timeAgo(notification.created_at)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          <button
            type="button"
            onClick={() => {
              setOpen(false);
              navigate("/requests");
            }}
            className="block w-full border-t border-slate-100 px-4 py-3 text-center text-sm font-medium text-indigo-600 hover:bg-slate-50"
          >
            View all requests
          </button>
        </div>
      )}
    </div>
  );
}
