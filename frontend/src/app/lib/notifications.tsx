import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "./api";
import { useAuth } from "./auth";
import { queryClient } from "./query-client";

export const notificationsKey = ["notifications"] as const;

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

function setNotificationsCache(updater: (prev: AppNotification[]) => AppNotification[]): void {
  queryClient.setQueryData<AppNotification[]>(notificationsKey, (prev) => updater(prev ?? []));
}

export function useNotifications() {
  const { currentUser } = useAuth();

  const query = useQuery({
    queryKey: notificationsKey,
    queryFn: async () => (await apiRequest<NotificationListResponse>("/notifications?limit=50")).items,
    enabled: Boolean(currentUser),
  });
  const notifications = query.data ?? [];

  return {
    notifications,
    unreadCount: notifications.filter((n) => !n.read).length,
    refreshNotifications: async () => {
      await query.refetch();
    },
    // Client-only ephemeral notification (no server round-trip). Deduped against
    // the live cache; a later refetch replaces it with the server list (as before).
    notify: (input: NotifyInput): AppNotification | null => {
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
      let inserted = false;
      setNotificationsCache((prev) => {
        if (input.dedupKey && prev.some((n) => n.dedupKey === input.dedupKey)) return prev;
        inserted = true;
        return [local, ...prev].slice(0, 50);
      });
      return inserted ? local : null;
    },
    markRead: (id: string) => {
      setNotificationsCache((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      if (!id.startsWith("local_")) {
        void apiRequest<NotificationListResponse>("/notifications/read", {
          method: "POST",
          body: { ids: [id] },
        }).then((response) => setNotificationsCache(() => response.items));
      }
    },
    markAllRead: () => {
      setNotificationsCache((prev) => prev.map((n) => ({ ...n, read: true })));
      void apiRequest<NotificationListResponse>("/notifications/read", {
        method: "POST",
        body: {},
      }).then((response) => setNotificationsCache(() => response.items));
    },
    dismiss: (id: string) => {
      setNotificationsCache((prev) => prev.filter((n) => n.id !== id));
      if (!id.startsWith("local_")) {
        void apiRequest<void>(`/notifications/${id}`, { method: "DELETE" });
      }
    },
    clear: () => setNotificationsCache(() => []),
    hasDedupKey: (key: string) => notifications.some((n) => n.dedupKey === key),
  };
}

// Accepts the `notifications`-namespace translator so relative labels localize.
type RelativeTimeTranslate = (key: string, options?: { count?: number }) => string;

export function formatNotificationTime(ts: number, t: RelativeTimeTranslate): string {
  const diff = Date.now() - ts;
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return t("relativeTime.justNow");
  const min = Math.floor(sec / 60);
  if (min < 60) return t("relativeTime.minutes", { count: min });
  const hr = Math.floor(min / 60);
  if (hr < 24) return t("relativeTime.hours", { count: hr });
  const days = Math.floor(hr / 24);
  if (days < 7) return t("relativeTime.days", { count: days });
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return t("relativeTime.weeks", { count: weeks });
  const months = Math.floor(days / 30);
  return t("relativeTime.months", { count: months });
}
