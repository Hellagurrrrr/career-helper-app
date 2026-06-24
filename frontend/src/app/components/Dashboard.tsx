import React from "react";
import { Link } from "react-router";
import {
  Plus,
  Sparkles,
  User,
  GraduationCap,
  Code,
  Award,
  ArrowRight,
  Target,
  BookOpen,
  Pencil,
  Users,
  Shield,
  Clock,
  CheckCircle2,
  ClipboardList,
} from "lucide-react";
import { formatPeriod, latestEducation, useProfile } from "../lib/profile";
import { getCatalogGoal, useGoals } from "../lib/goals";
import { rankAlumniForUser, useMeetings } from "../lib/alumni";
import {
  computeGoalProgress,
  parseWeekFocusKey,
  useTracking,
} from "../lib/tracking";
import {
  getPartnerPipelineStage,
  isTerminalManualStatus,
  useJobApplications,
} from "../lib/job-applications";

function AnimatedProgress({ value, gradient }: { value: number; gradient: string }) {
  const [width, setWidth] = React.useState(0);

  React.useEffect(() => {
    const id = requestAnimationFrame(() => setWidth(value));
    return () => cancelAnimationFrame(id);
  }, [value]);

  return (
    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
      <div
        className={`h-full rounded-full bg-gradient-to-r ${gradient} transition-[width] duration-700 ease-out`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

export function Dashboard() {
  const { profile } = useProfile();
  const { goals } = useGoals();
  const { meetings } = useMeetings();
  const { state: trackingState, getGoalTracking } = useTracking();
  const { applications } = useJobApplications();

  const userGoalIds = React.useMemo(() => goals.map((g) => g.catalogId), [goals]);
  const recommendedAlumni = React.useMemo(
    () => rankAlumniForUser(userGoalIds).slice(0, 3),
    [userGoalIds]
  );
  const pendingMeetingCount = meetings.filter((m) => m.status === "pending").length;
  const completedMeetingCount = meetings.filter(
    (m) => m.status === "completed"
  ).length;

  const edu = latestEducation(profile);
  const userInfo = {
    name: profile?.name?.trim() || "Friend",
    degree: edu?.degree || "",
    major: edu?.major || "",
    school: edu?.school || "",
    period: edu ? formatPeriod(edu.start, edu.end) : "",
  };

  const careerGoals = goals;

  const quickStats = {
    skills: profile?.skills ?? [],
    projects: profile?.projects ?? [],
    coursework: profile?.coursework ?? [],
    internships: profile?.internships ?? [],
  };

  const todaysFocus = React.useMemo(() => {
    const dots = ["bg-blue-500", "bg-indigo-500", "bg-sky-500"];
    const items: Array<{
      goalId: string;
      goalTitle: string;
      title: string;
      description: string;
      dot: string;
    }> = [];

    for (const goal of careerGoals) {
      const catalog = getCatalogGoal(goal.catalogId);
      if (!catalog) continue;
      const tracked = getGoalTracking(goal.id);

      for (const key of tracked.weekFocus) {
        if (items.length >= 3) break;
        const { moduleId, stepIdx } = parseWeekFocusKey(key);
        const moduleItem = catalog.coreSkills.find((m) => m.id === moduleId);
        const step = moduleItem?.whatToDo[stepIdx];
        if (!moduleItem || !step) continue;
        const done = tracked.modules[moduleId]?.completedSteps.includes(stepIdx);
        if (done) continue;
        items.push({
          goalId: goal.id,
          goalTitle: goal.title,
          title: step,
          description: moduleItem.name,
          dot: dots[items.length % dots.length],
        });
      }

      if (items.length >= 3) break;

      if (tracked.weekFocus.length === 0) {
        const skillsByConfidence = catalog.coreSkills
          .map((s) => ({ skill: s, confidence: goal.confidence?.[s.id] ?? 3 }))
          .sort((a, b) => a.confidence - b.confidence);
        const focusSkill = skillsByConfidence[0];
        if (focusSkill) {
          items.push({
            goalId: goal.id,
            goalTitle: goal.title,
            title: `Strengthen ${focusSkill.skill.name}`,
            description: focusSkill.skill.description,
            dot: dots[items.length % dots.length],
          });
        }
      }
    }

    return items;
  }, [careerGoals, getGoalTracking, trackingState]);

  const applicationSummary = React.useMemo(() => {
    const now = Date.now();
    let active = 0;
    let offers = 0;
    for (const a of applications) {
      if (a.kind === "partner") {
        const stage = getPartnerPipelineStage(a.submittedAt, now);
        if (stage !== "offer_extended") active += 1;
        else offers += 1;
      } else {
        if (!isTerminalManualStatus(a.manualStatus)) active += 1;
        if (a.manualStatus === "offer") offers += 1;
      }
    }
    return { total: applications.length, active, offers };
  }, [applications]);

  return (
    <div className="space-y-12">
      <div>
        <p className="mb-2 text-sm font-medium text-blue-700">Career planning workspace</p>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Welcome back, {userInfo.name}
        </h1>
        <p className="mt-2 text-slate-600">
          Track your goals, close skill gaps, and move toward your next role.
        </p>
      </div>

      <Link
        to="/applications"
        className="group flex flex-col gap-4 rounded-xl border border-slate-200/70 bg-white p-5 transition-colors hover:border-slate-300 sm:flex-row sm:items-center sm:justify-between"
      >
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <ClipboardList className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-medium text-blue-700">Job applications</p>
            <h2 className="text-lg font-semibold tracking-tight text-slate-950">
              Application tracking
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              {applicationSummary.total === 0
                ? "View and update all applications across your career goals."
                : `${applicationSummary.total} total · ${applicationSummary.active} in progress · ${applicationSummary.offers} offer${applicationSummary.offers === 1 ? "" : "s"}`}
            </p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1 self-start text-sm font-medium text-blue-800 sm:self-center">
          Open tracker
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </span>
      </Link>

      {todaysFocus.length > 0 && (
        <section>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Target className="h-5 w-5 text-blue-600" />
              <h2 className="text-lg font-semibold tracking-tight text-slate-950">
                Today's focus
              </h2>
            </div>
            <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
              {todaysFocus.length} actions
            </span>
          </div>

          <ul className="space-y-0.5">
            {todaysFocus.map((item, idx) => (
              <li key={idx}>
                <Link
                  to={`/career-goal/${item.goalId}/plan-tracking`}
                  className="group flex items-start justify-between gap-3 rounded-lg px-3 py-3 transition-colors hover:bg-slate-50"
                >
                  <div className="flex flex-1 gap-3">
                    <span
                      className={`mt-1.5 inline-block h-2 w-2 flex-shrink-0 rounded-full ${item.dot}`}
                    />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-950">{item.title}</p>
                      <p className="mt-0.5 text-sm text-slate-600">{item.description}</p>
                      <p className="mt-1 text-xs font-medium text-blue-700">{item.goalTitle}</p>
                    </div>
                  </div>
                  <ArrowRight className="mt-1 h-4 w-4 flex-shrink-0 text-slate-400 transition-colors group-hover:text-blue-700" />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight text-slate-950">
              <Sparkles className="h-5 w-5 text-blue-600" />
              My Career Explorations
            </h2>
            <span className="text-sm text-slate-500">{careerGoals.length} goals</span>
          </div>

          {careerGoals.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50">
                <Sparkles className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="text-base font-semibold text-slate-950">No goals yet</h3>
              <p className="max-w-sm text-sm text-slate-600">
                Add your first career goal to get a personalized learning plan and matching job
                recommendations.
              </p>
              <Link
                to="/new-goal"
                className="mt-1 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                Add your first goal
              </Link>
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-200/70">
              <div className="divide-y divide-slate-200/70">
              {careerGoals.map((goal) => {
                const catalog = getCatalogGoal(goal.catalogId);
                const computedProgress = computeGoalProgress(
                  getGoalTracking(goal.id),
                  catalog
                );
                return (
                  <Link
                    key={goal.id}
                    to={`/career-goal/${goal.id}/plan-tracking`}
                    className="group block p-5 transition-colors hover:bg-slate-50"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex flex-1 items-start gap-4">
                        <div
                          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${goal.color}`}
                        >
                          <Sparkles className="h-5 w-5 text-white" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-lg font-semibold tracking-tight text-slate-950 transition-colors group-hover:text-blue-700">
                              {goal.title}
                            </h3>
                            <span
                              className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                                goal.status === "active"
                                  ? "bg-green-50 text-green-800"
                                  : "bg-blue-50 text-blue-800"
                              }`}
                            >
                              {goal.status === "active" ? "Active" : "Exploring"}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-slate-600">{goal.description}</p>
                          <div className="mt-4 space-y-2">
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-slate-600">Overall Progress</span>
                              <span className="font-semibold text-slate-950">{computedProgress}%</span>
                            </div>
                            <AnimatedProgress value={computedProgress} gradient={goal.color} />
                            <p className="text-xs text-slate-500">Updated {goal.lastUpdated}</p>
                          </div>
                        </div>
                      </div>
                      <ArrowRight className="mt-1 h-5 w-5 flex-shrink-0 text-slate-400 transition-colors group-hover:translate-x-1 group-hover:text-blue-700" />
                    </div>
                  </Link>
                );
              })}
              </div>
              <Link
                to="/new-goal"
                className="group flex items-center justify-center gap-2 border-t border-slate-200/70 px-5 py-3.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-blue-700"
              >
                <Plus className="h-4 w-4 transition-colors group-hover:text-blue-700" />
                New Career Goal
              </Link>
            </div>
          )}
          {careerGoals.length > 0 && (
            <p className="px-1 text-xs text-slate-500">
              Tip: reorder or delete goals from the sidebar's Career Goals menu.
            </p>
          )}
        </section>

        <aside>
          <section className="overflow-hidden rounded-xl border border-slate-200/70 bg-white">
            <div className="border-b border-slate-100 p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 text-blue-600">
                    <User className="h-7 w-7" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold tracking-tight text-slate-950">
                      {userInfo.name}
                    </h2>
                    <p className="text-sm text-slate-600">
                      {[userInfo.degree, userInfo.major].filter(Boolean).join(" · ") || "Profile incomplete"}
                    </p>
                    {userInfo.school && (
                      <p className="text-sm text-slate-500">
                        {userInfo.school}
                        {userInfo.period ? ` · ${userInfo.period}` : ""}
                      </p>
                    )}
                  </div>
                </div>
                <Link
                  to="/profile"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50"
                  aria-label="Edit profile"
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Edit
                </Link>
              </div>
            </div>

            <div className="divide-y divide-slate-100">
              <div className="p-5">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
                  <Award className="h-4 w-4 text-blue-600" />
                  Skills
                </h3>
                {quickStats.skills.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {quickStats.skills.map((skill) => (
                      <span
                        key={skill}
                        className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">
                    No skills added yet.{" "}
                    <Link to="/profile" className="font-medium text-blue-700 hover:underline">
                      Add some
                    </Link>
                    .
                  </p>
                )}
              </div>

              <div className="p-5">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
                  <Code className="h-4 w-4 text-blue-600" />
                  Projects
                </h3>
                {quickStats.projects.length > 0 ? (
                  <div className="space-y-3">
                    {quickStats.projects.map((project, index) => (
                      <div key={index}>
                        <p className="text-sm font-semibold text-slate-950">{project.title}</p>
                        {formatPeriod(project.start, project.end) && (
                          <p className="text-xs text-slate-500">
                            {formatPeriod(project.start, project.end)}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No projects added yet.</p>
                )}
              </div>

              <div className="p-5">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
                  <GraduationCap className="h-4 w-4 text-blue-600" />
                  Coursework
                </h3>
                {quickStats.coursework.length > 0 ? (
                  <ul className="space-y-1.5">
                    {quickStats.coursework.map((course) => (
                      <li key={course} className="flex items-center gap-2 text-sm text-slate-700">
                        <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                        {course}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500">No coursework added yet.</p>
                )}
              </div>

              {quickStats.internships.length > 0 && (
                <div className="p-5">
                  <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
                    <BookOpen className="h-4 w-4 text-blue-600" />
                    Internships
                  </h3>
                  <div className="space-y-3">
                    {quickStats.internships.map((item, index) => (
                      <div key={index}>
                        <p className="text-sm font-semibold text-slate-950">{item.title}</p>
                        <p className="text-sm text-slate-600">{item.company}</p>
                        <p className="text-xs text-slate-500">
                          {formatPeriod(item.start, item.end) || item.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>
        </aside>
      </div>

      <section>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-blue-50">
              <Users className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-tight text-slate-950">
                Alumni network
              </h2>
              <p className="mt-0.5 text-sm text-slate-600">
                Chat with alumni who've landed roles you're targeting. Profiles are
                anonymized and your contact stays private.
              </p>
            </div>
          </div>
          <Link
            to="/alumni"
            className="inline-flex items-center justify-center gap-1.5 self-start rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          >
            Browse network
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
            <Shield className="h-3.5 w-3.5" />
            Privacy protected
          </span>
          {pendingMeetingCount > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 font-medium text-amber-800">
              <Clock className="h-3.5 w-3.5" />
              {pendingMeetingCount} pending request
              {pendingMeetingCount === 1 ? "" : "s"}
            </span>
          )}
          {completedMeetingCount > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-2.5 py-1 font-medium text-green-800">
              <CheckCircle2 className="h-3.5 w-3.5" />
              {completedMeetingCount} chat
              {completedMeetingCount === 1 ? "" : "s"} completed
            </span>
          )}
          {pendingMeetingCount === 0 && completedMeetingCount === 0 && (
            <span className="text-slate-500">
              No coffee chats yet — pick someone to start the conversation.
            </span>
          )}
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {recommendedAlumni.map(({ alumni, matched }) => (
            <Link
              key={alumni.id}
              to={`/alumni/${alumni.id}`}
              className="group flex h-full flex-col gap-3 rounded-xl border border-slate-200/70 bg-white p-4 transition-colors hover:border-slate-300 hover:bg-slate-50"
            >
              <div className="flex items-start gap-3">
                <div
                  className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${alumni.avatarGradient} text-base font-semibold text-white`}
                  aria-hidden="true"
                >
                  {alumni.firstName[0]}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <h3 className="text-sm font-semibold tracking-tight text-slate-950 transition-colors group-hover:text-blue-700">
                      {alumni.firstName} {alumni.lastInitial}
                    </h3>
                    {userGoalIds.length > 0 && matched && (
                      <span className="inline-flex items-center gap-0.5 rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-800">
                        <Sparkles className="h-2.5 w-2.5" />
                        Match
                      </span>
                    )}
                  </div>
                  <p className="truncate text-xs text-slate-600">
                    {alumni.role}
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    {alumni.company} · Class of {alumni.graduationYear}
                  </p>
                </div>
              </div>
              <div className="mt-auto flex items-center justify-between text-xs">
                <span className="truncate text-slate-500">
                  {alumni.topics[0]}
                </span>
                <span className="inline-flex items-center gap-0.5 font-medium text-blue-700 transition-transform group-hover:translate-x-0.5">
                  View
                  <ArrowRight className="h-3 w-3" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
