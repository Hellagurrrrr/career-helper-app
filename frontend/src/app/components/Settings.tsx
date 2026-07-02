import React from "react";
import { Link, useNavigate } from "react-router";
import { ChevronRight, LogOut, Check, AlertTriangle } from "lucide-react";
import { useAuth } from "../lib/auth";
import { Switch } from "./ui/switch";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./ui/alert-dialog";

const DEMO_DATA_KEYS = [
  "aichh:profile",
  "aichh:goals",
  "aichh:tracking",
  "aichh:job-applications-v1",
  "aichh:interview-reviews-v1",
  "aichh:interview-reviews-v2",
  "aichh:mock-interviews-v1",
  "aichh:saved-jobs-by-goal",
  "aichh:notifications",
  "aichh:meetings",
];

const NOTIF_PREF_KEY = "aichh:settings-notifications";

function Row({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-900">{title}</p>
        {description && (
          <p className="mt-0.5 text-sm text-slate-500">{description}</p>
        )}
      </div>
      {children && <div className="shrink-0">{children}</div>}
    </div>
  );
}

export function Settings() {
  const navigate = useNavigate();
  const { currentUser, logout, changePassword, deleteAccount, resetDemoData, updateNotificationPreference } = useAuth();

  const [notifEnabled, setNotifEnabled] = React.useState(() => {
    if (typeof window === "undefined") return true;
    return window.localStorage.getItem(NOTIF_PREF_KEY) !== "off";
  });

  const [currentPw, setCurrentPw] = React.useState("");
  const [nextPw, setNextPw] = React.useState("");
  const [pwError, setPwError] = React.useState<string | null>(null);
  const [pwSaved, setPwSaved] = React.useState(false);

  const [confirmReset, setConfirmReset] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState(false);

  const toggleNotif = (value: boolean) => {
    setNotifEnabled(value);
    window.localStorage.setItem(NOTIF_PREF_KEY, value ? "on" : "off");
    void updateNotificationPreference(value);
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError(null);
    setPwSaved(false);
    const result = await changePassword(currentPw, nextPw);
    if (!result.ok) {
      setPwError(result.error);
      return;
    }
    setCurrentPw("");
    setNextPw("");
    setPwSaved(true);
    window.setTimeout(() => setPwSaved(false), 2500);
  };

  const handleReset = async () => {
    DEMO_DATA_KEYS.forEach((key) => window.localStorage.removeItem(key));
    await resetDemoData();
    setConfirmReset(false);
    navigate("/onboarding", { replace: true });
    window.location.reload();
  };

  const handleDelete = async () => {
    DEMO_DATA_KEYS.forEach((key) => window.localStorage.removeItem(key));
    await deleteAccount();
    setConfirmDelete(false);
    navigate("/login", { replace: true });
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <nav aria-label="breadcrumb">
        <ol className="flex flex-wrap items-center gap-1.5 text-sm text-slate-500">
          <li>
            <Link
              to="/"
              className="rounded-md px-1 transition-colors hover:bg-slate-100 hover:text-slate-900"
            >
              Dashboard
            </Link>
          </li>
          <li aria-hidden="true">
            <ChevronRight className="h-4 w-4 text-slate-400" />
          </li>
          <li className="font-medium text-slate-900">Settings</li>
        </ol>
      </nav>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Settings
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Manage your account, preferences, and demo data.
        </p>
      </div>

      <section className="space-y-1">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Account
        </h2>
        <div className="divide-y divide-slate-200/70">
          <Row title="Signed in as" description={currentUser?.email}>
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              <LogOut className="h-4 w-4" />
              Log out
            </button>
          </Row>
          <div className="py-4">
            <p className="text-sm font-medium text-slate-900">Change password</p>
            <form
              onSubmit={handleChangePassword}
              className="mt-3 grid gap-3 sm:grid-cols-2"
            >
              <input
                type="password"
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
                placeholder="Current password"
                autoComplete="current-password"
                className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              />
              <input
                type="password"
                value={nextPw}
                onChange={(e) => setNextPw(e.target.value)}
                placeholder="New password"
                autoComplete="new-password"
                className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              />
              {pwError && (
                <p className="sm:col-span-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                  {pwError}
                </p>
              )}
              <div className="flex items-center gap-3 sm:col-span-2">
                <button
                  type="submit"
                  className="inline-flex h-10 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                >
                  Update password
                </button>
                {pwSaved && (
                  <span className="inline-flex items-center gap-1.5 text-sm font-medium text-green-700">
                    <Check className="h-4 w-4" />
                    Updated
                  </span>
                )}
              </div>
            </form>
          </div>
        </div>
      </section>

      <section className="space-y-1">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Preferences
        </h2>
        <div className="divide-y divide-slate-200/70">
          <Row
            title="In-app notifications"
            description="Show partner role alerts and reminders in the notification bell."
          >
            <Switch checked={notifEnabled} onCheckedChange={toggleNotif} />
          </Row>
        </div>
      </section>

      <section className="space-y-1">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Data
        </h2>
        <div className="divide-y divide-slate-200/70">
          <Row
            title="Reset demo data"
            description="Clear goals, plans, applications, and profile. Your account is kept."
          >
            <button
              onClick={() => setConfirmReset(true)}
              className="inline-flex items-center justify-center rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              Reset data
            </button>
          </Row>
          <Row
            title="Delete account"
            description="Permanently remove your account and all associated demo data."
          >
            <button
              onClick={() => setConfirmDelete(true)}
              className="inline-flex items-center justify-center rounded-lg border border-red-200 px-3 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-50"
            >
              Delete account
            </button>
          </Row>
        </div>
      </section>

      <AlertDialog open={confirmReset} onOpenChange={setConfirmReset}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-amber-50 text-amber-700">
                <AlertTriangle className="h-5 w-5" />
              </span>
              Reset demo data?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This clears your profile, goals, plans, and applications, then
              restarts onboarding. Your login is kept. This can't be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleReset}>
              Reset data
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-red-50 text-red-700">
                <AlertTriangle className="h-5 w-5" />
              </span>
              Delete your account?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes your account and all demo data. You'll be
              returned to the sign-in page. This can't be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep account</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-red-600 text-white hover:bg-red-700 focus:ring-red-200"
            >
              Yes, delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
