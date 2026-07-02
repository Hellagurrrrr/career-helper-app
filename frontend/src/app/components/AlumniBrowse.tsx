import React from "react";
import { Link, useSearchParams } from "react-router";
import {
  Users,
  Search,
  Shield,
  Sparkles,
  Building2,
  GraduationCap,
  Clock,
  ChevronRight,
  CheckCircle2,
  X,
  ExternalLink,
} from "lucide-react";
import { useGoals } from "../lib/goals";
import {
  ALUMNI_CATALOG,
  AlumniProfile,
  formatRelativeDate,
  getAlumni,
  rankAlumniForUser,
  useMeetings,
} from "../lib/alumni";
import { useNotifications } from "../lib/notifications";

type Tab = "browse" | "requests";

export function AlumniBrowse() {
  const { goals } = useGoals();
  const { meetings, withdrawRequest, completeRequest } = useMeetings();
  const { notify } = useNotifications();
  const [searchParams, setSearchParams] = useSearchParams();

  const handleCompleteWithNotify = React.useCallback(
    (id: string) => {
      const meeting = meetings.find((m) => m.id === id);
      completeRequest(id);
      if (meeting) {
        const alumni = ALUMNI_CATALOG.find((a) => a.id === meeting.alumniId);
        if (alumni) {
          notify({
            type: "meeting",
            severity: "success",
            title: `Coffee chat with ${alumni.firstName} ${alumni.lastInitial} completed`,
            body:
              "Nice work — log any takeaways while it's fresh. Want to chat with someone else?",
            link: "/alumni",
            dedupKey: `meeting-completed:${id}`,
          });
        }
      }
    },
    [meetings, completeRequest, notify]
  );

  const initialTab: Tab = searchParams.get("tab") === "requests" ? "requests" : "browse";
  const initialQuery = searchParams.get("expertise") ?? searchParams.get("q") ?? "";

  const [tab, setTab] = React.useState<Tab>(initialTab);
  const [query, setQuery] = React.useState(initialQuery);
  const [industry, setIndustry] = React.useState<string>("all");

  React.useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (tab === "requests") next.set("tab", "requests");
    else next.delete("tab");
    if (query.trim()) next.set("q", query.trim());
    else next.delete("q");
    next.delete("expertise");
    setSearchParams(next, { replace: true });
    // Sync URL only on tab/query changes; depending on searchParams/setSearchParams
    // would loop, since this effect itself writes them.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, query]);

  const userGoalIds = React.useMemo(() => goals.map((g) => g.catalogId), [goals]);

  const ranked = React.useMemo(
    () => rankAlumniForUser(userGoalIds, query),
    [userGoalIds, query]
  );

  const industries = React.useMemo(() => {
    const set = new Set(ALUMNI_CATALOG.map((a) => a.industry));
    return ["all", ...Array.from(set).sort()];
  }, []);

  const filtered = React.useMemo(() => {
    if (industry === "all") return ranked;
    return ranked.filter((r) => r.alumni.industry === industry);
  }, [ranked, industry]);

  const pendingCount = meetings.filter((m) => m.status === "pending").length;
  const completedCount = meetings.filter((m) => m.status === "completed").length;
  const totalCount = meetings.length;

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-sm font-medium text-blue-700">
          <Users className="h-4 w-4" />
          Alumni network
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
          Connect with alumni working in your target roles
        </h1>
        <p className="max-w-2xl text-slate-600">
          Browse alumni profiles and request a coffee chat. Profiles are
          anonymized to first name + last initial. Personal contact info is
          never shared on this platform.
        </p>
      </header>

      <section className="flex items-start gap-3 rounded-xl border border-blue-100 bg-blue-50/60 p-4">
        <Shield className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-700" />
        <div className="text-sm text-blue-900">
          <p className="font-semibold">Your privacy and theirs.</p>
          <p className="mt-0.5 text-blue-800">
            Names appear as "First name + last initial" only. Alumni opt in to
            specific chat topics and response cadences. Email is never shown —
            once an alumnus accepts your request, the platform will introduce
            you via a private channel.
          </p>
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200">
        <TabButton
          active={tab === "browse"}
          onClick={() => setTab("browse")}
          label="Browse"
          count={ALUMNI_CATALOG.length}
        />
        <TabButton
          active={tab === "requests"}
          onClick={() => setTab("requests")}
          label="My requests"
          count={totalCount}
        />
      </div>

      {tab === "browse" && (
        <BrowsePanel
          filtered={filtered}
          query={query}
          setQuery={setQuery}
          industry={industry}
          setIndustry={setIndustry}
          industries={industries}
          hasGoals={userGoalIds.length > 0}
        />
      )}

      {tab === "requests" && (
        <RequestsPanel
          meetings={meetings}
          pendingCount={pendingCount}
          completedCount={completedCount}
          onWithdraw={withdrawRequest}
          onComplete={handleCompleteWithNotify}
        />
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`-mb-px inline-flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
        active
          ? "border-blue-600 text-blue-700"
          : "border-transparent text-slate-600 hover:text-slate-900"
      }`}
    >
      {label}
      <span
        className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
          active ? "bg-blue-100 text-blue-800" : "bg-slate-100 text-slate-600"
        }`}
      >
        {count}
      </span>
    </button>
  );
}

function BrowsePanel({
  filtered,
  query,
  setQuery,
  industry,
  setIndustry,
  industries,
  hasGoals,
}: {
  filtered: { alumni: AlumniProfile; score: number; matched: boolean }[];
  query: string;
  setQuery: (v: string) => void;
  industry: string;
  setIndustry: (v: string) => void;
  industries: string[];
  hasGoals: boolean;
}) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search role, company, topic..."
            className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {industries.map((i) => (
            <button
              key={i}
              onClick={() => setIndustry(i)}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                industry === i
                  ? "border-blue-300 bg-blue-50 text-blue-800"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {i === "all" ? "All industries" : i}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <p className="text-sm text-slate-600">
            No alumni matched your search. Try different keywords or clear the
            filter.
          </p>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {filtered.map(({ alumni, matched }) => (
            <AlumniCard
              key={alumni.id}
              alumni={alumni}
              recommended={hasGoals && matched}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function AlumniCard({
  alumni,
  recommended,
}: {
  alumni: AlumniProfile;
  recommended?: boolean;
}) {
  const { getRequestForAlumni } = useMeetings();
  const existing = getRequestForAlumni(alumni.id);

  return (
    <article className="group flex h-full flex-col rounded-xl border border-slate-200 bg-white p-5 transition-colors hover:border-blue-200 hover:bg-blue-50/20">
      <Link
        to={`/alumni/${alumni.id}`}
        className="flex min-h-0 flex-1 flex-col gap-4 rounded-xl outline-none ring-offset-2 focus-visible:ring-2 focus-visible:ring-blue-400"
      >
        <div className="flex items-start gap-4">
          <div
            className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${alumni.avatarGradient} text-lg font-semibold text-white`}
            aria-hidden="true"
          >
            {alumni.firstName[0]}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold tracking-tight text-slate-950 transition-colors group-hover:text-blue-700">
                {alumni.firstName} {alumni.lastInitial}
              </h3>
              {recommended && (
                <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-800">
                  <Sparkles className="h-3 w-3" />
                  Match
                </span>
              )}
              {existing && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">
                  <Clock className="h-3 w-3" />
                  Request sent
                </span>
              )}
            </div>
            <p className="mt-0.5 text-sm font-medium text-slate-700">
              {alumni.role}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
              <span className="inline-flex items-center gap-1">
                <Building2 className="h-3.5 w-3.5" />
                {alumni.company}
              </span>
              <span className="inline-flex items-center gap-1">
                <GraduationCap className="h-3.5 w-3.5" />
                Class of {alumni.graduationYear}
              </span>
            </div>
          </div>
        </div>

        <p className="line-clamp-2 text-sm text-slate-600">{alumni.bio}</p>

        <div className="flex flex-wrap gap-1.5">
          {alumni.expertise.slice(0, 4).map((tag) => (
            <span
              key={tag}
              className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700"
            >
              {tag}
            </span>
          ))}
          {alumni.expertise.length > 4 && (
            <span className="rounded-md bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-500">
              +{alumni.expertise.length - 4}
            </span>
          )}
        </div>
      </Link>

      <div className="mt-auto flex flex-wrap items-center justify-between gap-x-2 gap-y-2 border-t border-slate-100 pt-3 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1">
          <Shield className="h-3.5 w-3.5" />
          Privacy protected
        </span>
        <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
          <a
            href={alumni.linkedinUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#0A66C2]/35 bg-sky-50 px-2.5 py-1.5 text-xs font-semibold text-[#0A66C2] transition-colors hover:bg-sky-100"
            aria-label={`View ${alumni.firstName}'s LinkedIn profile (opens in a new tab)`}
          >
            <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden />
            LinkedIn
          </a>
          <Link
            to={`/alumni/${alumni.id}`}
            className="inline-flex items-center gap-1 font-medium text-blue-700 transition-transform group-hover:translate-x-0.5"
          >
            View profile
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </article>
  );
}

function RequestsPanel({
  meetings,
  pendingCount,
  completedCount,
  onWithdraw,
  onComplete,
}: {
  meetings: ReturnType<typeof useMeetings>["meetings"];
  pendingCount: number;
  completedCount: number;
  onWithdraw: (id: string) => void;
  onComplete: (id: string) => void;
}) {
  const sorted = React.useMemo(
    () => [...meetings].sort((a, b) => b.submittedAt - a.submittedAt),
    [meetings]
  );

  return (
    <div className="space-y-4">
      <section className="grid gap-3 sm:grid-cols-3">
        <StatCard
          label="Total requests"
          value={meetings.length}
          tone="slate"
        />
        <StatCard label="Pending" value={pendingCount} tone="amber" />
        <StatCard label="Completed" value={completedCount} tone="green" />
      </section>

      {sorted.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <p className="text-sm font-medium text-slate-700">
            You haven't requested any coffee chats yet.
          </p>
          <p className="mt-1 text-sm text-slate-500">
            Browse alumni profiles and tap "Request a coffee chat" to get
            started.
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {sorted.map((req) => {
            const alumni = getAlumni(req.alumniId);
            if (!alumni) return null;
            return (
              <li
                key={req.id}
                className="rounded-xl border border-slate-200 bg-white p-5"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <Link
                    to={`/alumni/${alumni.id}`}
                    className="flex flex-1 items-start gap-3"
                  >
                    <div
                      className={`flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${alumni.avatarGradient} text-base font-semibold text-white`}
                      aria-hidden="true"
                    >
                      {alumni.firstName[0]}
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="text-base font-semibold tracking-tight text-slate-950">
                          {alumni.firstName} {alumni.lastInitial}
                        </h4>
                        <StatusBadge status={req.status} />
                      </div>
                      <p className="text-sm text-slate-600">
                        {alumni.role} · {alumni.company}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Topic: <span className="text-slate-700">{req.topic}</span>
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        Sent {formatRelativeDate(req.submittedAt)}
                      </p>
                    </div>
                  </Link>
                  <div className="flex flex-wrap gap-2">
                    {req.status === "pending" && (
                      <>
                        <button
                          onClick={() => onComplete(req.id)}
                          className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                        >
                          <CheckCircle2 className="h-4 w-4" />
                          Mark completed
                        </button>
                        <button
                          onClick={() => onWithdraw(req.id)}
                          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                        >
                          <X className="h-4 w-4" />
                          Withdraw
                        </button>
                      </>
                    )}
                    {req.status === "completed" && (
                      <span className="inline-flex items-center gap-1.5 rounded-xl bg-green-50 px-3 py-2 text-sm font-medium text-green-800">
                        <CheckCircle2 className="h-4 w-4" />
                        Chat completed
                      </span>
                    )}
                  </div>
                </div>
                {req.message && (
                  <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-700">
                    "{req.message}"
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "slate" | "amber" | "green";
}) {
  const tones: Record<typeof tone, string> = {
    slate: "border-slate-200 bg-white",
    amber: "border-amber-100 bg-amber-50",
    green: "border-green-100 bg-green-50",
  };
  return (
    <div className={`rounded-xl border p-4 ${tones[tone]}`}>
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <p className="mt-1 text-2xl font-bold tracking-tight text-slate-950">
        {value}
      </p>
    </div>
  );
}

function StatusBadge({ status }: { status: "pending" | "completed" | "withdrawn" }) {
  if (status === "pending") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">
        <Clock className="h-3 w-3" />
        Awaiting response
      </span>
    );
  }
  if (status === "completed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-800">
        <CheckCircle2 className="h-3 w-3" />
        Completed
      </span>
    );
  }
  return null;
}
