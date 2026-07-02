import React from "react";
import { useNavigate } from "react-router";
import {
  Bell,
  X,
  Sparkles,
  Briefcase,
  Users,
  Coffee,
  Trophy,
  Calendar,
  Check,
  Inbox,
} from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import {
  AppNotification,
  formatNotificationTime,
  NotificationType,
  useNotifications,
} from "../lib/notifications";

const typeConfig: Record<
  NotificationType,
  { icon: React.ComponentType<{ className?: string }>; color: string }
> = {
  system: { icon: Sparkles, color: "bg-blue-50 text-blue-700" },
  job: { icon: Briefcase, color: "bg-blue-50 text-blue-700" },
  alumni: { icon: Users, color: "bg-indigo-50 text-indigo-700" },
  meeting: { icon: Coffee, color: "bg-amber-50 text-amber-700" },
  milestone: { icon: Trophy, color: "bg-green-50 text-green-700" },
  week: { icon: Calendar, color: "bg-sky-50 text-sky-700" },
};

export function NotificationsButton({
  variant = "desktop",
}: {
  variant?: "desktop" | "mobile";
}) {
  const {
    notifications,
    unreadCount,
    markRead,
    markAllRead,
    dismiss,
    clear,
  } = useNotifications();
  const [open, setOpen] = React.useState(false);
  const navigate = useNavigate();

  const handleClick = (n: AppNotification) => {
    markRead(n.id);
    if (n.link) {
      setOpen(false);
      navigate(n.link);
    }
  };

  const trigger = (
    <button
      type="button"
      aria-label={
        unreadCount > 0
          ? `Notifications (${unreadCount} unread)`
          : "Notifications"
      }
      className={`relative flex items-center justify-center rounded-lg text-slate-700 transition-colors hover:bg-slate-100 hover:text-slate-900 ${
        variant === "mobile"
          ? "h-10 w-full justify-start gap-3 px-3 text-sm font-medium"
          : "h-10 w-10"
      }`}
    >
      <Bell className={variant === "mobile" ? "h-4 w-4" : "h-5 w-5"} />
      {variant === "mobile" && "Notifications"}
      {unreadCount > 0 && (
        <span
          className={`absolute flex min-w-[18px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white ring-2 ring-white ${
            variant === "mobile"
              ? "right-3 top-1/2 -translate-y-1/2 ml-auto"
              : "right-1 top-1"
          }`}
        >
          {unreadCount > 9 ? "9+" : unreadCount}
        </span>
      )}
    </button>
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>{trigger}</PopoverTrigger>
      <PopoverContent
        align={variant === "mobile" ? "start" : "end"}
        sideOffset={8}
        className="w-[min(380px,calc(100vw-2rem))] p-0"
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold tracking-tight text-slate-950">
              Notifications
            </h3>
            <p className="text-xs text-slate-500">
              {unreadCount > 0
                ? `${unreadCount} unread`
                : "Nothing new — you're all caught up"}
            </p>
          </div>
          {notifications.length > 0 && (
            <button
              type="button"
              onClick={markAllRead}
              disabled={unreadCount === 0}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:text-slate-400 disabled:hover:bg-transparent"
            >
              <Check className="h-3.5 w-3.5" />
              Mark all read
            </button>
          )}
        </div>

        <div className="max-h-[min(440px,60vh)] overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 px-4 py-10 text-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-500">
                <Inbox className="h-5 w-5" />
              </div>
              <p className="text-sm font-medium text-slate-700">
                No notifications yet
              </p>
              <p className="max-w-[260px] text-xs text-slate-500">
                We'll let you know when there are new job matches, alumni
                updates, or progress milestones.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {notifications.map((n) => {
                const cfg = typeConfig[n.type];
                const Icon = cfg.icon;
                return (
                  <li key={n.id}>
                    <div
                      role={n.link ? "button" : undefined}
                      tabIndex={n.link ? 0 : undefined}
                      onClick={() => handleClick(n)}
                      onKeyDown={(e) => {
                        if (n.link && (e.key === "Enter" || e.key === " ")) {
                          e.preventDefault();
                          handleClick(n);
                        }
                      }}
                      className={`group flex items-start gap-3 px-4 py-3 transition-colors ${
                        n.link
                          ? "cursor-pointer hover:bg-blue-50/40"
                          : ""
                      } ${!n.read ? "bg-blue-50/30" : ""}`}
                    >
                      <div
                        className={`mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${cfg.color}`}
                      >
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start gap-2">
                          <div className="min-w-0 flex-1">
                            <p
                              className={`text-sm leading-snug ${
                                n.read
                                  ? "font-medium text-slate-700"
                                  : "font-semibold text-slate-950"
                              }`}
                            >
                              {n.title}
                            </p>
                            <p className="mt-0.5 text-xs leading-snug text-slate-600">
                              {n.body}
                            </p>
                            <p className="mt-1 text-[11px] text-slate-400">
                              {formatNotificationTime(n.createdAt)}
                            </p>
                          </div>
                          {!n.read && (
                            <span
                              className="mt-1 inline-block h-2 w-2 flex-shrink-0 rounded-full bg-blue-600"
                              aria-label="Unread"
                            />
                          )}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          dismiss(n.id);
                        }}
                        className="invisible mt-0.5 flex h-6 w-6 items-center justify-center rounded text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 group-hover:visible"
                        aria-label="Dismiss notification"
                        title="Dismiss"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {notifications.length > 0 && (
          <div className="border-t border-slate-100 px-4 py-2">
            <button
              type="button"
              onClick={clear}
              className="w-full rounded-md py-1 text-xs font-medium text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-800"
            >
              Clear all
            </button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
