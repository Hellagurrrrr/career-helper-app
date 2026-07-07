import React from "react";
import { useNavigate, Link } from "react-router";
import {
  ArrowLeft,
  ArrowRight,
  Sparkles,
  Target,
  CheckCircle2,
  TrendingUp,
} from "lucide-react";
import { Trans, useTranslation } from "react-i18next";
import { latestEducation, useProfile } from "../lib/profile";
import {
  CatalogGoal,
  UserGoal,
  useGoals,
  rankGoalsForProfile,
  confidenceLabel,
  confidenceTone,
} from "../lib/goals";
import { useNotifications } from "../lib/notifications";
import { countPartnerJobs, JOBS_BY_GOAL } from "../lib/jobs";
import { ALUMNI_CATALOG } from "../lib/alumni";

type Step = "select" | "quiz";

export function NewGoal() {
  const navigate = useNavigate();
  const { t } = useTranslation("newGoal");
  const { profile } = useProfile();
  const { goals, addGoal } = useGoals();
  const { notify } = useNotifications();

  const [step, setStep] = React.useState<Step>("select");
  const [selected, setSelected] = React.useState<CatalogGoal | null>(null);
  const [confidence, setConfidence] = React.useState<Record<string, number>>({});

  const ranked = React.useMemo(
    () =>
      rankGoalsForProfile(
        profile?.skills ?? [],
        latestEducation(profile)?.major
      ),
    [profile]
  );
  const ownedIds = React.useMemo(
    () => new Set(goals.map((g) => g.catalogId)),
    [goals]
  );

  const handleSelect = (g: CatalogGoal) => {
    const init: Record<string, number> = {};
    g.coreSkills.forEach((s) => {
      init[s.id] = 3;
    });
    setSelected(g);
    setConfidence(init);
    setStep("quiz");
  };

  const handleFinish = async () => {
    if (!selected) return;
    const lowCount = selected.coreSkills.filter(
      (s) => (confidence[s.id] ?? 3) <= 2
    ).length;
    const avg =
      selected.coreSkills.reduce(
        (sum, s) => sum + (confidence[s.id] ?? 3),
        0
      ) / Math.max(selected.coreSkills.length, 1);
    const initialProgress = Math.max(5, Math.round(((avg - 1) / 4) * 100 * 0.7));

    const newGoal: UserGoal = {
      id: selected.id,
      catalogId: selected.id,
      title: selected.title,
      description: selected.description,
      color: selected.color,
      status: selected.defaultStatus,
      progress: initialProgress,
      lastUpdated: "just now",
      createdAt: Date.now(),
      confidence: { ...confidence },
    };
    const createdGoal = await addGoal(newGoal);
    const savedGoal = createdGoal ?? newGoal;
    void lowCount;

    const jobCount = JOBS_BY_GOAL[savedGoal.catalogId]?.jobs.length ?? 0;
    const partnerCount = countPartnerJobs(savedGoal.catalogId);
    if (jobCount > 0) {
      notify({
        type: "job",
        severity: "info",
        title: t("notify.jobsMatchTitle", { count: jobCount, goal: savedGoal.title }),
        body:
          partnerCount > 0
            ? t("notify.jobsMatchBodyPartner", {
                count: partnerCount,
                openCount: jobCount - partnerCount,
              })
            : t("notify.jobsMatchBodyPlain", { count: jobCount }),
        link: `/jobs?goal=${savedGoal.id}`,
        dedupKey: `jobs:${savedGoal.id}`,
      });
    }
    if (partnerCount > 0) {
      notify({
        type: "job",
        severity: "success",
        title: t("notify.referralTitle", { count: partnerCount }),
        body: t("notify.referralBody", { count: partnerCount, goal: savedGoal.title }),
        link: `/jobs?goal=${savedGoal.id}`,
        dedupKey: `partner-jobs:${savedGoal.id}`,
      });
    }
    const alumniCount = ALUMNI_CATALOG.filter((a) =>
      a.goalAlignment.includes(savedGoal.catalogId)
    ).length;
    if (alumniCount > 0) {
      notify({
        type: "alumni",
        severity: "info",
        title: t("notify.alumniTitle", { count: alumniCount, goal: savedGoal.title }),
        body: t("notify.alumniBody"),
        link: `/alumni?expertise=${encodeURIComponent(savedGoal.title)}`,
        dedupKey: `alumni:${savedGoal.id}`,
      });
    }

    navigate(`/career-goal/${savedGoal.id}/plan-tracking`, { replace: true });
  };

  return (
    <div className="space-y-6">
      {step === "select" && (
        <SelectStep
          ranked={ranked}
          ownedIds={ownedIds}
          hasProfileSkills={(profile?.skills?.length ?? 0) > 0}
          onCancel={() => navigate("/")}
          onSelect={handleSelect}
        />
      )}
      {step === "quiz" && selected && (
        <QuizStep
          goal={selected}
          confidence={confidence}
          onChange={setConfidence}
          onBack={() => setStep("select")}
          onFinish={handleFinish}
        />
      )}
    </div>
  );
}

function SelectStep({
  ranked,
  ownedIds,
  hasProfileSkills,
  onCancel,
  onSelect,
}: {
  ranked: { goal: CatalogGoal; score: number }[];
  ownedIds: Set<string>;
  hasProfileSkills: boolean;
  onCancel: () => void;
  onSelect: (g: CatalogGoal) => void;
}) {
  const { t } = useTranslation("newGoal");
  const topScore = ranked[0]?.score ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-blue-700">
            {t("select.step")}
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
            {t("select.title")}
          </h1>
          <p className="mt-1 text-slate-600">
            {hasProfileSkills ? t("select.subtitleRanked") : t("select.subtitleNoSkills")}
          </p>
        </div>
        <Link
          to="/"
          onClick={(e) => {
            e.preventDefault();
            onCancel();
          }}
          className="inline-flex items-center gap-2 self-start rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("select.cancel")}
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {ranked.map(({ goal, score }, idx) => {
          const owned = ownedIds.has(goal.id);
          const isRecommended =
            hasProfileSkills && idx === 0 && topScore > 0;
          return (
            <article
              key={goal.id}
              className={`flex h-full flex-col gap-4 rounded-xl border bg-white p-5 transition-colors ${
                owned
                  ? "border-slate-200 opacity-70"
                  : "border-slate-200 hover:border-blue-300"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div
                  className={`flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${goal.color}`}
                >
                  <Target className="h-6 w-6 text-white" />
                </div>
                {isRecommended && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-800">
                    <Sparkles className="h-3.5 w-3.5" />
                    {t("select.recommended")}
                  </span>
                )}
                {owned && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2.5 py-1 text-xs font-medium text-green-800">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {t("select.added")}
                  </span>
                )}
              </div>

              <div className="flex-1 space-y-3">
                <div>
                  <h3 className="text-lg font-semibold tracking-tight text-slate-950">
                    {goal.title}
                  </h3>
                  <p className="mt-1 text-sm text-slate-600">{goal.description}</p>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t("select.coreSkills", { count: goal.coreSkills.length })}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {goal.coreSkills.slice(0, 4).map((s) => (
                      <span
                        key={s.id}
                        className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700"
                      >
                        {s.name}
                      </span>
                    ))}
                    {goal.coreSkills.length > 4 && (
                      <span className="rounded-md bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-500">
                        +{goal.coreSkills.length - 4}
                      </span>
                    )}
                  </div>
                </div>

                {hasProfileSkills && score > 0 && (
                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <TrendingUp className="h-3.5 w-3.5 text-blue-700" />
                    {t("select.matches", {
                      count: Math.min(Math.ceil(score / 2), goal.matchSignals.length),
                    })}
                  </div>
                )}
              </div>

              <button
                onClick={() => onSelect(goal)}
                disabled={owned}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
              >
                {owned ? t("select.alreadyAdded") : t("select.startQuiz")}
                {!owned && <ArrowRight className="h-4 w-4" />}
              </button>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function QuizStep({
  goal,
  confidence,
  onChange,
  onBack,
  onFinish,
}: {
  goal: CatalogGoal;
  confidence: Record<string, number>;
  onChange: (next: Record<string, number>) => void;
  onBack: () => void;
  onFinish: () => void;
}) {
  const { t } = useTranslation("newGoal");
  const answered = goal.coreSkills.filter((s) => confidence[s.id] !== undefined)
    .length;
  const total = goal.coreSkills.length;
  const allAnswered = answered === total;

  const setValue = (skillId: string, value: number) => {
    onChange({ ...confidence, [skillId]: value });
  };

  const lowCount = goal.coreSkills.filter(
    (s) => (confidence[s.id] ?? 0) > 0 && confidence[s.id] <= 2
  ).length;
  const strongCount = goal.coreSkills.filter(
    (s) => (confidence[s.id] ?? 0) >= 4
  ).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-blue-700">
            {t("quiz.step")}
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
            {t("quiz.title")}
          </h1>
          <p className="mt-1 text-slate-600">
            <Trans
              i18nKey="newGoal:quiz.subtitle"
              values={{ title: goal.title }}
              components={{ goal: <span className="font-semibold text-slate-900" /> }}
            />
          </p>
        </div>
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 self-start rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("quiz.changeGoal")}
        </button>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${goal.color}`}
            >
              <Target className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-tight text-slate-950">{goal.title}</h2>
              <p className="text-sm text-slate-600">
                {t("quiz.answered", { answered, total })}
              </p>
            </div>
          </div>
          <div className="flex gap-2 text-xs">
            <span className="rounded-full bg-red-50 px-2.5 py-1 font-medium text-red-800">
              {t("quiz.needFocus", { count: lowCount })}
            </span>
            <span className="rounded-full bg-green-50 px-2.5 py-1 font-medium text-green-800">
              {t("quiz.alreadyStrong", { count: strongCount })}
            </span>
          </div>
        </div>

        <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-blue-600 transition-[width] duration-500 ease-out"
            style={{ width: `${(answered / total) * 100}%` }}
          />
        </div>
      </section>

      <ul className="space-y-3">
        {goal.coreSkills.map((skill) => {
          const value = confidence[skill.id];
          return (
            <li
              key={skill.id}
              className="rounded-xl border border-slate-200 bg-white p-5"
            >
              <div className="flex flex-col gap-3">
                <div>
                  <h3 className="text-base font-semibold tracking-tight text-slate-950">
                    {skill.name}
                  </h3>
                  <p className="text-sm text-slate-600">{skill.description}</p>
                </div>
                <ConfidencePicker
                  value={value}
                  onChange={(v) => setValue(skill.id, v)}
                />
              </div>
            </li>
          );
        })}
      </ul>

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <button
          onClick={onBack}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("quiz.back")}
        </button>
        <button
          onClick={onFinish}
          disabled={!allAnswered}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
        >
          <CheckCircle2 className="h-4 w-4" />
          {t("quiz.buildPlan")}
        </button>
      </div>
    </div>
  );
}

function ConfidencePicker({
  value,
  onChange,
}: {
  value: number | undefined;
  onChange: (v: number) => void;
}) {
  const { t } = useTranslation(["tracking", "newGoal"]);
  const options = [1, 2, 3, 4, 5];
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {options.map((v) => {
          const active = value === v;
          return (
            <button
              key={v}
              type="button"
              onClick={() => onChange(v)}
              className={`min-w-[70px] flex-1 rounded-xl border px-3 py-2 text-sm font-medium transition-colors sm:flex-none ${
                active
                  ? `${confidenceTone(v)}`
                  : "border-slate-200 bg-white text-slate-700 hover:border-blue-200 hover:bg-blue-50/50"
              }`}
              aria-pressed={active}
            >
              <div className="text-base font-bold">{v}</div>
              <div className="text-[11px] font-medium opacity-80">
                {confidenceLabel(v, t)}
              </div>
            </button>
          );
        })}
      </div>
      {value === undefined && (
        <p className="text-xs text-slate-500">{t("newGoal:quiz.pickRating")}</p>
      )}
    </div>
  );
}
