import React from "react";
import { Link } from "react-router";
import {
  Sparkles,
  Building2,
  Target,
  FileAudio,
  Mic,
  ChevronDown,
  ChevronUp,
  ClipboardList,
} from "lucide-react";
import { InterviewReviewPanel } from "./InterviewReviewPanel";
import { MockInterviewPanel } from "./MockInterviewPanel";
import { useGoals } from "../lib/goals";
import { useJobApplications } from "../lib/job-applications";
import { useInterviewReviews } from "../lib/interview-reviews";
import { useMockInterviews } from "../lib/mock-interviews";

type CoachingTab = "review" | "mock";

export function AiCoaching() {
  const { goals } = useGoals();
  const { applications } = useJobApplications();
  const { reviews } = useInterviewReviews();
  const { sessions } = useMockInterviews();

  const [tabByApp, setTabByApp] = React.useState<Record<string, CoachingTab>>({});
  const [expandedAppId, setExpandedAppId] = React.useState<string | null>(null);

  const getTab = (appId: string): CoachingTab => tabByApp[appId] ?? "review";
  const setTab = (appId: string, tab: CoachingTab) =>
    setTabByApp((prev) => ({ ...prev, [appId]: tab }));

  const goalTitleById = React.useMemo(() => {
    const map = new Map<string, string>();
    for (const g of goals) map.set(g.id, g.title);
    return map;
  }, [goals]);

  const sortedApps = React.useMemo(
    () => [...applications].sort((a, b) => b.submittedAt - a.submittedAt),
    [applications]
  );

  const reviewCountByApp = React.useMemo(() => {
    const map = new Map<string, number>();
    for (const r of reviews) {
      map.set(r.applicationId, (map.get(r.applicationId) ?? 0) + 1);
    }
    return map;
  }, [reviews]);

  const mockCountByApp = React.useMemo(() => {
    const map = new Map<string, number>();
    for (const s of sessions) {
      map.set(s.applicationId, (map.get(s.applicationId) ?? 0) + 1);
    }
    return map;
  }, [sessions]);

  const firstGoalForEmptyLink = goals[0]?.id ?? "1";

  React.useEffect(() => {
    if (expandedAppId || sortedApps.length === 0) return;
    setExpandedAppId(sortedApps[0].id);
  }, [expandedAppId, sortedApps]);

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-blue-50/50 p-5">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white">
            <Sparkles className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-indigo-700">AI Coaching</p>
            <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-slate-950">
              Interview coaching workspace
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-600">
              Review past interviews or run voice mock sessions for roles you&apos;ve applied to.
              Every session is archived per application so you can track improvement over time.
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl bg-white px-4 py-3 ring-1 ring-indigo-100">
            <p className="text-xs font-medium uppercase tracking-wide text-indigo-700">
              Applications
            </p>
            <p className="mt-1 text-xl font-bold text-slate-950">{sortedApps.length}</p>
          </div>
          <div className="rounded-xl bg-white px-4 py-3 ring-1 ring-indigo-100">
            <p className="text-xs font-medium uppercase tracking-wide text-indigo-700">
              Reviews archived
            </p>
            <p className="mt-1 text-xl font-bold text-slate-950">{reviews.length}</p>
          </div>
          <div className="rounded-xl bg-white px-4 py-3 ring-1 ring-indigo-100">
            <p className="text-xs font-medium uppercase tracking-wide text-indigo-700">
              Mocks archived
            </p>
            <p className="mt-1 text-xl font-bold text-slate-950">{sessions.length}</p>
          </div>
          <div className="col-span-2 rounded-xl bg-indigo-600 px-4 py-3 text-white sm:col-span-1">
            <p className="text-xs font-medium uppercase tracking-wide text-indigo-100">
              Demo mode
            </p>
            <p className="mt-1 text-sm font-medium">Browser speech APIs</p>
          </div>
        </div>
      </section>

      {sortedApps.length === 0 ? (
        <section className="rounded-xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-12 text-center">
          <p className="text-sm font-medium text-slate-800">No applications to coach yet</p>
          <p className="mt-2 text-sm text-slate-600">
            Apply to roles from{" "}
            <Link
              to={`/jobs?goal=${firstGoalForEmptyLink}`}
              className="font-medium text-blue-700 underline-offset-2 hover:underline"
            >
              Jobs
            </Link>{" "}
            first, then return here for interview review and mock practice.
          </p>
        </section>
      ) : (
        <section className="space-y-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold tracking-tight text-slate-950">
            <ClipboardList className="h-5 w-5 text-indigo-600" />
            Coaching by application
          </h2>

          <ul className="space-y-3">
            {sortedApps.map((app) => {
              const goalTitle = goalTitleById.get(app.goalId);
              const expanded = expandedAppId === app.id;
              const reviewCount = app.reviewCount ?? reviewCountByApp.get(app.id) ?? 0;
              const mockCount = app.mockCount ?? mockCountByApp.get(app.id) ?? 0;

              const coachingContext = {
                applicationId: app.id,
                jobTitle: app.title,
                company: app.company,
                goalTitle,
                skills: [],
              };

              return (
                <li
                  key={app.id}
                  className="overflow-hidden rounded-xl border border-slate-200 bg-white"
                >
                  <button
                    type="button"
                    onClick={() => setExpandedAppId(expanded ? null : app.id)}
                    className="flex w-full items-start justify-between gap-3 p-4 text-left transition-colors hover:bg-slate-50/80"
                  >
                    <div className="min-w-0 flex-1">
                      <h3 className="text-base font-semibold tracking-tight text-slate-950">
                        {app.title}
                      </h3>
                      <p className="mt-0.5 flex flex-wrap items-center gap-2 text-sm text-slate-600">
                        <span className="inline-flex items-center gap-1">
                          <Building2 className="h-3.5 w-3.5" />
                          {app.company}
                        </span>
                        {goalTitle && (
                          <span className="inline-flex items-center gap-1 text-slate-500">
                            <Target className="h-3 w-3" />
                            {goalTitle}
                          </span>
                        )}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {reviewCount > 0 && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-800">
                            <FileAudio className="h-3 w-3" />
                            {reviewCount} review{reviewCount !== 1 ? "s" : ""}
                          </span>
                        )}
                        {mockCount > 0 && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-800">
                            <Mic className="h-3 w-3" />
                            {mockCount} mock{mockCount !== 1 ? "s" : ""}
                          </span>
                        )}
                      </div>
                    </div>
                    {expanded ? (
                      <ChevronUp className="h-5 w-5 shrink-0 text-slate-400" />
                    ) : (
                      <ChevronDown className="h-5 w-5 shrink-0 text-slate-400" />
                    )}
                  </button>

                  {expanded && (
                    <div className="border-t border-slate-100 p-4">
                      <div className="mb-4 flex gap-1 rounded-lg bg-slate-100 p-1">
                        <button
                          type="button"
                          onClick={() => setTab(app.id, "review")}
                          className={`flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                            getTab(app.id) === "review"
                              ? "bg-white text-indigo-900 shadow-sm"
                              : "text-slate-600 hover:text-slate-900"
                          }`}
                        >
                          <FileAudio className="h-4 w-4" />
                          Interview review
                        </button>
                        <button
                          type="button"
                          onClick={() => setTab(app.id, "mock")}
                          className={`flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                            getTab(app.id) === "mock"
                              ? "bg-white text-indigo-900 shadow-sm"
                              : "text-slate-600 hover:text-slate-900"
                          }`}
                        >
                          <Mic className="h-4 w-4" />
                          Mock interview
                        </button>
                      </div>

                      {getTab(app.id) === "review" ? (
                        <InterviewReviewPanel context={coachingContext} />
                      ) : (
                        <MockInterviewPanel context={coachingContext} />
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}
