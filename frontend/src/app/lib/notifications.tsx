import React from "react";
import { apiRequest } from "./api";
import { useAuth } from "./auth";

export type NotificationType = "system" | "job" | "alumni" | "meeting" | "milestone" | "week";
export type NotificationSeverity = "info" | "success" | "warning";

export type AppNotification = {
  id: string;
  type: NotificationType;
  severity: NotificationSeverity;
  title: string;
  body: string;
  link?: string;
  createdAt: number;
  read: boolean;
  dedupKey?: string;
};

export type NotifyInput = {
  type: NotificationType;
  severity?: NotificationSeverity;
  title: string;
  body: string;
  link?: string;
  dedupKey?: string;
};

type NotificationListResponse = {
  items: AppNotification[];
  nextCursor: string | null;
  total: number;
};

type NotificationsContextValue = {
  notifications: AppNotification[];
  unreadCount: number;
  refreshNotifications: () => Promise<void>;
  notify: (input: NotifyInput) => AppNotification | null;
  markRead: (id: string) => void;
  markAllRead: () => void;
  dismiss: (id: string) => void;
  clear: () => void;
  hasDedupKey: (key: string) => boolean;
};

const NotificationsContext = React.createContext<NotificationsContextValue | null>(null);

export function NotificationsProvider({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth();
  const [notifications, setNotifications] = React.useState<AppNotification[]>([]);

  const refreshNotifications = React.useCallback(async () => {
    if (!currentUser) {
      setNotifications([]);
      return;
    }
    const response = await apiRequest<NotificationListResponse>("/notifications?limit=50");
    setNotifications(response.items);
  }, [currentUser]);

  React.useEffect(() => {
    void refreshNotifications();
  }, [refreshNotifications]);

  const notify = React.useCallback<NotificationsContextValue["notify"]>(
    (input) => {
      if (input.dedupKey && notifications.some((n) => n.dedupKey === input.dedupKey)) return null;
      const local: AppNotification = {
        id: `local_${Date.now().toString(36)}`,
        type: input.type,
        severity: input.severity ?? "info",
        title: input.title,
        body: input.body,
        link: input.link,
        createdAt: Date.now(),
        read: false,
        dedupKey: input.dedupKey,
      };
      setNotifications((prev) => [local, ...prev].slice(0, 50));
      return local;
    },
    [notifications]
  );

  const markRead = React.useCallback((id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    if (!id.startsWith("local_")) {
      void apiRequest<NotificationListResponse>("/notifications/read", {
        method: "POST",
        body: { ids: [id] },
      }).then((response) => setNotifications(response.items));
    }
  }, []);

  const markAllRead = React.useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    void apiRequest<NotificationListResponse>("/notifications/read", {
      method: "POST",
      body: {},
    }).then((response) => setNotifications(response.items));
  }, []);

  const dismiss = React.useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    if (!id.startsWith("local_")) {
      void apiRequest<void>(`/notifications/${id}`, { method: "DELETE" });
    }
  }, []);

  const clear = React.useCallback(() => {
    setNotifications([]);
  }, []);

  const hasDedupKey = React.useCallback(
    (key: string) => notifications.some((n) => n.dedupKey === key),
    [notifications]
  );

  const unreadCount = React.useMemo(() => notifications.filter((n) => !n.read).length, [notifications]);

  const value = React.useMemo(
    () => ({ notifications, unreadCount, refreshNotifications, notify, markRead, markAllRead, dismiss, clear, hasDedupKey }),
    [notifications, unreadCount, refreshNotifications, notify, markRead, markAllRead, dismiss, clear, hasDedupKey]
  );

  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

export function useNotifications(): NotificationsContextValue {
  const ctx = React.useContext(NotificationsContext);
  if (!ctx) {
    throw new Error("useNotifications must be used inside a NotificationsProvider");
  }
  return ctx;
}

export function formatNotificationTime(ts: number): string {
  const diff = Date.now() - ts;
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} min ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.floor(hr / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks}w ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}
