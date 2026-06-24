import React from "react";
import { Link, useSearchParams } from "react-router";
import {
  ClipboardList,
  Building2,
  Clock,
  RefreshCw,
  Lock,
  Target,
  Sparkles,
} from "lucide-react";
import { useInterviewReviews } from "../lib/interview-reviews";
import { useMockInterviews } from "../lib/mock-interviews";
import { useGoals } from "../lib/goals";
import {
  getPartnerPipelineStage,
  isTerminalManualStatus,
  JobApplication,
  MANUAL_STATUS_LABELS,
  ManualApplicationStatus,
  PARTNER_STATUS_LABELS,
  useJobApplications,
} from "../lib/job-applications";

function computeSummary(apps: JobApplication[]) {
  let partner = 0;
  let standard = 0;
  let active = 0;
  let offers = 0;
  for (const a of apps) {
    if (a.kind === "partner") {
      partner += 1;
      const stage = a.partnerStatus ?? getPartnerPipelineStage(a.submittedAt);
      if (stage !== "offer_extended") active += 1;
      if (stage === "offer_extended") offers += 1;
    } else {
      standard += 1;
      if (!a.manualStatus || !isTerminalManualStatus(a.manualStatus)) active += 1;
      if (a.manualStatus === "offer") offers += 1;
    }
  }
  return { total: apps.length, partner, standard, active, offers };
}

export function JobTracking() {
  const [searchParams, setSearchParams] = useSearchParams();
  const goalFilter = searchParams.get("goal") ?? "all";

  const { goals } = useGoals();
  const { applications, setManualStatus } = useJobApplications();
  const { reviews } = useInterviewReviews();
  const { sessions } = useMockInterviews();
  const [now, setNow] = React.useState(() => Date.now());

  React.useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => window.clearInterval(id);
  }, []);

  const goalTitleById = React.useMemo(() => {
    const map = new Map<string, string>();
    for (const g of goals) map.set(g.id, g.title);
    return map;
  }, [goals]);

  const filteredApps = React.useMemo(() => {
    if (goalFilter === "all") return applications;
    return applications.filter((a) => a.goalId === goalFilter);
  }, [applications, goalFilter]);

  const sorted = React.useMemo(
    () => [...filteredApps].sort((a, b) => b.submittedAt - a.submittedAt),
    [filteredApps]
  );

  const summary = React.useMemo(
    () => computeSummary(filteredApps),
    [filteredApps]
  );

  const goalIdsWithApps = React.useMemo(() => {
    const ids = new Set(applications.map((a) => a.goalId));
    return [...ids].sort((a, b) =>
      (goalTitleById.get(a) ?? a).localeCompare(goalTitleById.get(b) ?? b)
    );
  }, [applications, goalTitleById]);

  const firstGoalForEmptyLink = goals[0]?.id ?? goalIdsWithApps[0] ?? "1";

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-blue-100 bg-blue-50/70 p-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-medium text-blue-700">Applications</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">
              Job application tracking
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-600">
              All roles you applied to across career goals. Use{" "}
              <Link
                to="/ai-coaching"
                className="font-medium text-indigo-700 underline-offset-2 hover:underline"
              >
                AI Coaching
              </Link>{" "}
              for interview review and voice mock practice per role.{" "}
              <span className="font-medium text-slate-800">Partner / exclusive</span> roles update
              automatically; <span className="font-medium text-slate-800">other roles</span> use
              the status you set.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setNow(Date.now())}
            className="inline-flex shrink-0 items-center gap-2 self-start rounded-xl border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-800 shadow-sm transition-colors hover:bg-blue-50"
            title="Refresh status display"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <div className="rounded-xl bg-white px-4 py-3 ring-1 ring-blue-100">
            <p className="text-xs font-medium uppercase tracking-wide text-blue-700">Total</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-slate-950">{summary.total}</p>
          </div>
          <div className="rounded-xl bg-white px-4 py-3 ring-1 ring-blue-100">
            <p className="text-xs font-medium uppercase tracking-wide text-blue-700">Partner</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-slate-950">{summary.partner}</p>
          </div>
          <div className="rounded-xl bg-white px-4 py-3 ring-1 ring-blue-100">
            <p className="text-xs font-medium uppercase tracking-wide text-blue-700">Self-tracked</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-slate-950">{summary.standard}</p>
          </div>
          <div className="rounded-xl bg-white px-4 py-3 ring-1 ring-blue-100">
            <p className="text-xs font-medium uppercase tracking-wide text-blue-700">In progress</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-slate-950">{summary.active}</p>
          </div>
          <div className="col-span-2 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 px-4 py-3 text-white shadow-sm sm:col-span-1">
            <p className="text-xs font-medium uppercase tracking-wide text-blue-100">Offers</p>
            <p className="mt-1 text-xl font-bold tracking-tight">{summary.offers}</p>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-blue-700" />
            <h2 className="text-lg font-semibold tracking-tight text-slate-950">
              Application details
            </h2>
            <span className="text-sm text-slate-500">({sorted.length})</span>
          </div>
          {goalIdsWithApps.length > 0 && (
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <span className="shrink-0 font-medium">Career goal</span>
              <select
                value={goalFilter}
                onChange={(e) => {
                  const next = e.target.value;
                  if (next === "all") {
                    setSearchParams({});
                  } else {
                    setSearchParams({ goal: next });
                  }
                }}
                className="min-w-[10rem] rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="all">All goals</option>
                {goalIdsWithApps.map((id) => (
                  <option key={id} value={id}>
                    {goalTitleById.get(id) ?? id}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>

        {sorted.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-10 text-center">
            <p className="text-sm font-medium text-slate-800">No applications yet</p>
            <p className="mt-2 text-sm text-slate-600">
              Open a career goal&apos;s{" "}
              <Link
                to={`/jobs?goal=${firstGoalForEmptyLink}`}
                className="font-medium text-blue-700 underline-offset-2 hover:underline"
              >
                Jobs
              </Link>{" "}
              and use <span className="font-medium text-slate-900">Apply</span> or{" "}
              <span className="font-medium text-slate-900">Apply with referral</span>.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {sorted.map((app) => {
              const goalTitle = goalTitleById.get(app.goalId);
              const partnerStage =
                app.kind === "partner"
                  ? app.partnerStatus ?? getPartnerPipelineStage(app.submittedAt)
                  : null;

              return (
                <li
                  key={app.id}
                  className="rounded-xl border border-slate-200 bg-slate-50/40 p-4 transition-colors hover:border-blue-200"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-semibold tracking-tight text-slate-950">
                          {app.title}
                        </h3>
                        {app.kind === "partner" ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-900 ring-1 ring-blue-200">
                            <Lock className="h-3 w-3" />
                            Exclusive · auto
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-slate-200/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-700">
                            Self-tracked
                          </span>
                        )}
                      </div>
                      <p className="mt-0.5 flex flex-wrap items-center gap-2 text-sm text-slate-600">
                        <span className="inline-flex items-center gap-1">
                          <Building2 className="h-3.5 w-3.5" />
                          {app.company}
                        </span>
                      </p>
                      {goalTitle && (
                        <p className="mt-1.5">
                          <Link
                            to={`/jobs?goal=${app.goalId}`}
                            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 transition-colors hover:bg-blue-50 hover:text-blue-800"
                          >
                            <Target className="h-3 w-3" />
                            {goalTitle}
                          </Link>
                        </p>
                      )}
                      <p className="mt-2 text-xs text-slate-500">
                        <span className="inline-flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Applied {new Date(app.submittedAt).toLocaleString()}
                        </span>
                      </p>
                    </div>

                    <div className="w-full shrink-0 sm:w-64">
                      {app.kind === "partner" && partnerStage ? (
                        <div className="rounded-xl border border-blue-100 bg-blue-50/80 p-3">
                          <p className="text-xs font-semibold uppercase tracking-wide text-blue-800">
                            Status (auto)
                          </p>
                          <p className="mt-1 text-sm font-semibold text-slate-900">
                            {PARTNER_STATUS_LABELS[partnerStage]}
                          </p>
                          <p className="mt-2 text-xs leading-relaxed text-slate-600">
                            Status advances from your apply time (referral → review → interviews →
                            offer). Timing is simulated from hours since apply; use Refresh if the
                            page has been open a while.
                          </p>
                        </div>
                      ) : app.kind === "standard" ? (
                        <div className="rounded-xl border border-slate-200 bg-white p-3">
                          <label
                            htmlFor={`status-${app.id}`}
                            className="text-xs font-semibold uppercase tracking-wide text-slate-600"
                          >
                            Your status
                          </label>
                          <select
                            id={`status-${app.id}`}
                            value={app.manualStatus}
                            onChange={(e) =>
                              setManualStatus(
                                app.id,
                                e.target.value as ManualApplicationStatus
                              )
                            }
                            className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                          >
                            {(Object.keys(MANUAL_STATUS_LABELS) as ManualApplicationStatus[]).map(
                              (key) => (
                                <option key={key} value={key}>
                                  {MANUAL_STATUS_LABELS[key]}
                                </option>
                              )
                            )}
                          </select>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  {(() => {
                    const reviewCount = reviews.filter(
                      (r) => r.applicationId === app.id
                    ).length;
                    const mockCount = sessions.filter(
                      (s) => s.applicationId === app.id
                    ).length;
                    if (reviewCount === 0 && mockCount === 0) return null;
                    return (
                      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-200 pt-3">
                        <span className="text-xs text-slate-500">
                          {reviewCount > 0 && `${reviewCount} review${reviewCount !== 1 ? "s" : ""}`}
                          {reviewCount > 0 && mockCount > 0 && " · "}
                          {mockCount > 0 && `${mockCount} mock${mockCount !== 1 ? "s" : ""}`}
                        </span>
                        <Link
                          to="/ai-coaching"
                          className="inline-flex items-center gap-1 rounded-lg bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-800 transition-colors hover:bg-indigo-100"
                        >
                          <Sparkles className="h-3 w-3" />
                          Open in AI Coaching
                        </Link>
                      </div>
                    );
                  })()}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
