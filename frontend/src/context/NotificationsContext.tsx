import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api } from "../lib/api";
import { useAuth } from "./AuthContext";

export interface AppNotification {
  id: string;
  request_id: string | null;
  message: string;
  read_at: string | null;
  created_at: string;
}

interface NotificationsValue {
  items: AppNotification[];
  unread: number;
  refresh: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
}

const POLL_MS = 60_000;

const NotificationsContext = createContext<NotificationsValue | null>(null);

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [items, setItems] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);

  const refresh = useCallback(async () => {
    const data = await api.get<{ unread: number; items: AppNotification[] }>("/notifications");
    setItems(data.items);
    setUnread(data.unread);
  }, []);

  useEffect(() => {
    if (!user) {
      setItems([]);
      setUnread(0);
      return;
    }
    void refresh().catch(() => undefined);
    const timer = window.setInterval(() => void refresh().catch(() => undefined), POLL_MS);
    return () => window.clearInterval(timer);
  }, [user?.id, refresh]);

  const markRead = async (id: string) => {
    const target = items.find((n) => n.id === id);
    if (!target || target.read_at) return;
    // Update immediately so the badge reacts without waiting for the network.
    setItems((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n)),
    );
    setUnread((count) => Math.max(0, count - 1));
    await api.post(`/notifications/${id}/read`).catch(() => undefined);
  };

  const markAllRead = async () => {
    const now = new Date().toISOString();
    setItems((prev) => prev.map((n) => ({ ...n, read_at: n.read_at ?? now })));
    setUnread(0);
    await api.post("/notifications/read-all").catch(() => undefined);
  };

  return (
    <NotificationsContext.Provider value={{ items, unread, refresh, markRead, markAllRead }}>
      {children}
    </NotificationsContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationsContext);
  if (!context) throw new Error("useNotifications must be used inside NotificationsProvider");
  return context;
}
