import React from "react";
import { Link, useParams } from "react-router";
import {
  BookOpen,
  ExternalLink,
  Target,
  TrendingUp,
  Zap,
  CheckCircle2,
  Circle,
  Users,
  Briefcase,
  Sparkles,
  RefreshCw,
  ChevronRight,
  Star,
} from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "./ui/accordion";
import {
  confidenceLabel,
  confidenceTone,
  getCatalogGoal,
  useGoals,
  CoreSkill,
} from "../lib/goals";
import {
  useTracking,
  getModuleProgress,
  computeGoalProgress,
  isWeekStale,
  pickWeekFocus,
  parseWeekFocusKey,
  WeekFocusKey,
} from "../lib/tracking";
import { countJobsForSkillKeywords } from "../lib/jobs";
import { countAlumniForKeywords } from "../lib/alumni";

const RERATE_THRESHOLD = 2;

export function PlanTracking() {
  const { goalId } = useParams();
  const { getGoal, updateConfidence } = useGoals();
  const tracking = useTracking();

  const userGoal = goalId ? getGoal(goalId) : undefined;
  const trackingGoalId = userGoal?.id ?? goalId;
  const catalogGoal = userGoal ? getCatalogGoal(userGoal.catalogId) : undefined;
  const confidence = userGoal?.confidence ?? {};
  const goalTracking = trackingGoalId
    ? tracking.getGoalTracking(trackingGoalId)
    : undefined;

  React.useEffect(() => {
    if (!trackingGoalId || !catalogGoal) return;
    if (isWeekStale(goalTracking) || goalTracking?.weekFocus.length === 0) {
      const focus = pickWeekFocus(catalogGoal, goalTracking, confidence);
      if (focus.length > 0) {
        tracking.setWeekFocus(trackingGoalId, focus);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackingGoalId, catalogGoal]);

  if (!userGoal || !catalogGoal || !trackingGoalId) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
        <h2 className="text-lg font-semibold text-slate-950">
          No learning plan available
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          We couldn't find the catalog data for this goal.
        </p>
      </div>
    );
  }

  const sortedModules = React.useMemo(() => {
    return [...catalogGoal.coreSkills].sort((a, b) => {
      const ca = confidence[a.id] ?? 3;
      const cb = confidence[b.id] ?? 3;
      if (ca !== cb) return ca - cb;
      const pa = getModuleProgress(goalTracking, a);
      const pb = getModuleProgress(goalTracking, b);
      return pa - pb;
    });
  }, [catalogGoal.coreSkills, confidence, goalTracking]);

  const focusCount = catalogGoal.coreSkills.filter(
    (m) => (confidence[m.id] ?? 3) <= 2
  ).length;
  const strongCount = catalogGoal.coreSkills.filter(
    (m) => (confidence[m.id] ?? 3) >= 4
  ).length;
  const overallProgress = computeGoalProgress(goalTracking, catalogGoal);

  const defaultOpen = sortedModules[0]?.id;

  const handleReroll = () => {
    const focus = pickWeekFocus(
      catalogGoal,
      goalTracking,
      confidence,
      goalTracking?.weekFocus ?? []
    );
    tracking.setWeekFocus(trackingGoalId, focus);
  };

  return (
    <div className="space-y-6">
      <WeekFocusCard
        goalId={trackingGoalId}
        catalogGoal={catalogGoal}
        focusKeys={goalTracking?.weekFocus ?? []}
        goalTracking={goalTracking}
        onToggle={(moduleId, stepIdx) =>
          tracking.toggleStep(trackingGoalId, moduleId, stepIdx)
        }
        onReroll={handleReroll}
      />

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm font-medium text-slate-500">Overall progress</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
            {overallProgress}%
          </p>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${catalogGoal.color} transition-[width] duration-500`}
              style={{ width: `${overallProgress}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Averaged across {catalogGoal.coreSkills.length} skill modules.
          </p>
        </div>
        <div className="rounded-xl border border-red-100 bg-red-50 p-4">
          <div className="flex items-center gap-2.5">
            <div className="h-2.5 w-2.5 rounded-full bg-red-500" />
            <p className="text-sm font-medium text-red-800">Needs focus</p>
          </div>
          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
            {focusCount}
          </p>
          <p className="text-sm text-slate-600">Skills rated 1-2</p>
        </div>
        <div className="rounded-xl border border-green-100 bg-green-50 p-4 sm:col-span-2 lg:col-span-1">
          <div className="flex items-center gap-2.5">
            <div className="h-2.5 w-2.5 rounded-full bg-green-500" />
            <p className="text-sm font-medium text-green-800">Already strong</p>
          </div>
          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
            {strongCount}
          </p>
          <p className="text-sm text-slate-600">Skills rated 4-5</p>
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-center gap-2.5">
          <BookOpen className="h-5 w-5 text-blue-600" />
          <h2 className="text-lg font-semibold tracking-tight text-slate-950">
            Core Skill Modules
          </h2>
          <span className="ml-auto text-sm text-slate-500">
            {catalogGoal.coreSkills.length} modules · sorted by need
          </span>
        </div>

        <Accordion
          type="single"
          collapsible
          defaultValue={defaultOpen}
          className="space-y-3"
        >
          {sortedModules.map((module) => (
            <ModuleAccordionItem
              key={module.id}
              goalId={trackingGoalId}
              catalogGoalId={catalogGoal.id}
              module={module}
              confidenceValue={confidence[module.id]}
              goalTracking={goalTracking}
              onToggleStep={(stepIdx) =>
                tracking.toggleStep(trackingGoalId, module.id, stepIdx)
              }
              onToggleResource={(idx) =>
                tracking.toggleResource(trackingGoalId, module.id, idx)
              }
              onRerate={(value) => {
                updateConfidence(trackingGoalId, module.id, value);
                tracking.resetRerateCounter(trackingGoalId, module.id);
              }}
              onDismissRerate={() =>
                tracking.markRerateDismissed(trackingGoalId, module.id)
              }
            />
          ))}
        </Accordion>
      </section>
    </div>
  );
}

function WeekFocusCard({
  goalId,
  catalogGoal,
  focusKeys,
  goalTracking,
  onToggle,
  onReroll,
}: {
  goalId: string;
  catalogGoal: ReturnType<typeof getCatalogGoal>;
  focusKeys: WeekFocusKey[];
  goalTracking: ReturnType<typeof useTracking>["state"][string] | undefined;
  onToggle: (moduleId: string, stepIdx: number) => void;
  onReroll: () => void;
}) {
  void goalId;
  if (!catalogGoal || focusKeys.length === 0) {
    return (
      <section className="rounded-xl border border-blue-100 bg-blue-50/60 p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-blue-700 shadow-sm">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold tracking-tight text-slate-950">
              All caught up!
            </h2>
            <p className="text-sm text-slate-600">
              No outstanding actions this week. Mark some steps incomplete or
              add a new goal to keep moving.
            </p>
          </div>
        </div>
      </section>
    );
  }

  const items = focusKeys
    .map((key) => {
      const { moduleId, stepIdx } = parseWeekFocusKey(key);
      const module = catalogGoal.coreSkills.find((m) => m.id === moduleId);
      if (!module) return null;
      const step = module.whatToDo[stepIdx];
      if (!step) return null;
      const isDone =
        goalTracking?.modules[moduleId]?.completedSteps.includes(stepIdx) ??
        false;
      return { moduleId, stepIdx, module, step, isDone };
    })
    .filter((x): x is NonNullable<typeof x> => x !== null);

  const doneCount = items.filter((i) => i.isDone).length;
  const allDone = doneCount === items.length;

  return (
    <section className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50 via-white to-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
              This week's focus
            </p>
            <h2 className="text-lg font-semibold tracking-tight text-slate-950">
              {allDone
                ? "Great week — ready for the next batch?"
                : `Pick off ${items.length - doneCount} more this week`}
            </h2>
            <p className="mt-0.5 text-sm text-slate-600">
              Drawn from your weakest-confidence modules. Resets every 7 days.
            </p>
          </div>
        </div>
        <button
          onClick={onReroll}
          className="inline-flex items-center gap-1.5 rounded-xl border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-800 transition-colors hover:bg-blue-50"
        >
          <RefreshCw className="h-4 w-4" />
          Pick different focus
        </button>
      </div>

      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-blue-100">
        <div
          className="h-full rounded-full bg-blue-600 transition-[width] duration-500"
          style={{ width: `${(doneCount / items.length) * 100}%` }}
        />
      </div>

      <ul className="mt-4 space-y-2">
        {items.map((item) => (
          <li key={`${item.moduleId}:${item.stepIdx}`}>
            <button
              type="button"
              onClick={() => onToggle(item.moduleId, item.stepIdx)}
              className={`group flex w-full items-start gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors ${
                item.isDone
                  ? "border-green-200 bg-green-50/70"
                  : "border-slate-200 bg-white hover:border-blue-200 hover:bg-blue-50/40"
              }`}
            >
              {item.isDone ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-600" />
              ) : (
                <Circle className="mt-0.5 h-5 w-5 flex-shrink-0 text-slate-300 group-hover:text-blue-500" />
              )}
              <div className="min-w-0 flex-1">
                <p
                  className={`text-sm font-medium ${
                    item.isDone
                      ? "text-slate-500 line-through"
                      : "text-slate-900"
                  }`}
                >
                  {item.step}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {item.module.name}
                </p>
              </div>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ModuleAccordionItem({
  goalId,
  catalogGoalId,
  module,
  confidenceValue,
  goalTracking,
  onToggleStep,
  onToggleResource,
  onRerate,
  onDismissRerate,
}: {
  goalId: string;
  catalogGoalId: string;
  module: CoreSkill;
  confidenceValue: number | undefined;
  goalTracking: ReturnType<typeof useTracking>["state"][string] | undefined;
  onToggleStep: (stepIdx: number) => void;
  onToggleResource: (resourceIdx: number) => void;
  onRerate: (value: number) => void;
  onDismissRerate: () => void;
}) {
  void goalId;
  const stepCount = module.whatToDo.length;
  const resourceCount = module.resources.length;
  const progress = getModuleProgress(goalTracking, module);
  const moduleTracking = goalTracking?.modules[module.id];
  const completedSteps = new Set(moduleTracking?.completedSteps ?? []);
  const consumedResources = new Set(moduleTracking?.consumedResources ?? []);

  const alumniCount = countAlumniForKeywords([
    module.name,
    ...module.jobSkillKeywords,
  ]);
  const jobCount = countJobsForSkillKeywords(catalogGoalId, module.jobSkillKeywords);

  const shouldShowRerate =
    confidenceValue !== undefined &&
    !moduleTracking?.rerateDismissed &&
    (moduleTracking?.stepsCompletedSinceRerate ?? 0) >= RERATE_THRESHOLD;

  return (
    <AccordionItem
      value={module.id}
      className="overflow-hidden rounded-xl border border-slate-200 bg-white transition-colors hover:border-blue-200"
    >
      <AccordionTrigger className="group px-5 py-4 transition-colors hover:bg-slate-50 hover:no-underline data-[state=open]:bg-slate-50">
        <div className="flex w-full flex-col gap-3 pr-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-blue-50 transition-colors group-hover:bg-blue-100">
                <BookOpen className="h-5 w-5 text-blue-700" />
              </div>
              <div className="text-left">
                <div className="mb-0.5 text-base font-semibold tracking-tight text-slate-950">
                  {module.name}
                </div>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
                  <span>
                    {completedSteps.size}/{stepCount} steps done
                  </span>
                  <span aria-hidden="true">·</span>
                  <span>{resourceCount} resources</span>
                  {alumniCount > 0 && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span className="inline-flex items-center gap-0.5">
                        <Users className="h-3 w-3" />
                        {alumniCount} alumni
                      </span>
                    </>
                  )}
                  {jobCount > 0 && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span className="inline-flex items-center gap-0.5">
                        <Briefcase className="h-3 w-3" />
                        {jobCount} open jobs
                      </span>
                    </>
                  )}
                </div>
              </div>
            </div>
            <div className="flex flex-shrink-0 flex-col items-end gap-1.5">
              {confidenceValue !== undefined && (
                <span
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${confidenceTone(
                    confidenceValue
                  )}`}
                >
                  {confidenceLabel(confidenceValue)}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-blue-600 transition-[width] duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="w-9 text-right text-xs font-semibold tracking-tight text-slate-700">
              {progress}%
            </span>
          </div>
        </div>
      </AccordionTrigger>

      <AccordionContent className="bg-slate-50/60 px-5 pb-5 pt-2">
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4 lg:col-span-3">
            <div className="mb-2 flex items-center gap-2.5">
              <div className="rounded-md bg-blue-50 p-1.5">
                <TrendingUp className="h-4 w-4 text-blue-700" />
              </div>
              <h4 className="text-sm font-semibold text-slate-950">
                Where you are
              </h4>
            </div>
            <p className="text-sm leading-relaxed text-slate-700">
              {module.defaultStatus}
            </p>
            {(alumniCount > 0 || jobCount > 0) && (
              <div className="mt-3 flex flex-wrap gap-2">
                {alumniCount > 0 && (
                  <Link
                    to={`/alumni?expertise=${encodeURIComponent(module.name)}`}
                    className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-800 transition-colors hover:bg-blue-100"
                  >
                    <Users className="h-3.5 w-3.5" />
                    Find {alumniCount} alumni who can help
                    <ChevronRight className="h-3 w-3" />
                  </Link>
                )}
                {jobCount > 0 && (
                  <Link
                    to={`/jobs?goal=${goalId}`}
                    className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-800 transition-colors hover:bg-blue-100"
                  >
                    <Briefcase className="h-3.5 w-3.5" />
                    {jobCount} open jobs need this
                    <ChevronRight className="h-3 w-3" />
                  </Link>
                )}
              </div>
            )}
          </div>

          {shouldShowRerate && (
            <RerateCard
              currentValue={confidenceValue!}
              onRerate={onRerate}
              onDismiss={onDismissRerate}
              moduleName={module.name}
            />
          )}

          <div
            className={`rounded-xl border border-amber-100 bg-amber-50/70 p-4 ${
              shouldShowRerate ? "lg:col-span-2" : "lg:col-span-3"
            }`}
          >
            <div className="mb-3 flex items-center justify-between gap-2.5">
              <div className="flex items-center gap-2.5">
                <div className="rounded-md bg-amber-100 p-1.5">
                  <Zap className="h-4 w-4 text-amber-700" />
                </div>
                <h4 className="text-sm font-semibold text-slate-950">
                  Action Steps
                </h4>
              </div>
              <span className="text-xs font-medium text-amber-900">
                {completedSteps.size}/{stepCount} complete
              </span>
            </div>
            <ul className="space-y-2">
              {module.whatToDo.map((action, idx) => {
                const done = completedSteps.has(idx);
                return (
                  <li key={idx}>
                    <button
                      type="button"
                      onClick={() => onToggleStep(idx)}
                      className={`group/step flex w-full items-start gap-3 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                        done
                          ? "border-green-200 bg-green-50/70"
                          : "border-amber-200/60 bg-white hover:border-amber-300 hover:bg-amber-50"
                      }`}
                    >
                      {done ? (
                        <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-600" />
                      ) : (
                        <Circle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-400 group-hover/step:text-amber-600" />
                      )}
                      <span
                        className={`flex-1 leading-relaxed ${
                          done ? "text-slate-500 line-through" : "text-slate-800"
                        }`}
                      >
                        {action}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 lg:col-span-3">
            <div className="mb-3 flex items-center justify-between gap-2.5">
              <div className="flex items-center gap-2.5">
                <div className="rounded-md bg-blue-50 p-1.5">
                  <BookOpen className="h-4 w-4 text-blue-700" />
                </div>
                <h4 className="text-sm font-semibold text-slate-950">
                  Recommended Resources
                </h4>
              </div>
              <span className="text-xs font-medium text-slate-500">
                {consumedResources.size}/{resourceCount} done
              </span>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {module.resources.map((resource, idx) => {
                const consumed = consumedResources.has(idx);
                return (
                  <div
                    key={idx}
                    className={`group/res flex items-center gap-3 rounded-xl border px-3 py-3 transition-colors ${
                      consumed
                        ? "border-green-200 bg-green-50/60"
                        : "border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50/30"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => onToggleResource(idx)}
                      className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-400 transition-colors hover:bg-slate-50 hover:text-slate-700"
                      aria-label={
                        consumed ? "Mark unread" : "Mark resource as consumed"
                      }
                      title={
                        consumed ? "Mark unread" : "Mark resource as consumed"
                      }
                    >
                      {consumed ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                      ) : (
                        <Circle className="h-4 w-4" />
                      )}
                    </button>
                    <a
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex flex-1 items-center justify-between gap-2 text-left"
                    >
                      <div className="min-w-0">
                        <div
                          className={`truncate text-sm font-medium ${
                            consumed
                              ? "text-slate-500 line-through"
                              : "text-slate-950"
                          }`}
                        >
                          {resource.title}
                        </div>
                        <div className="mt-0.5 text-xs text-slate-500">
                          {resource.type}
                        </div>
                      </div>
                      <ExternalLink className="h-4 w-4 flex-shrink-0 text-slate-400 transition-colors group-hover/res:text-blue-700" />
                    </a>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </AccordionContent>
    </AccordionItem>
  );
}

function RerateCard({
  currentValue,
  onRerate,
  onDismiss,
  moduleName,
}: {
  currentValue: number;
  onRerate: (value: number) => void;
  onDismiss: () => void;
  moduleName: string;
}) {
  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-4">
      <div className="flex items-start gap-2.5">
        <div className="rounded-md bg-white p-1.5 text-blue-700 shadow-sm">
          <Star className="h-4 w-4" />
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-slate-950">
            Re-rate your confidence
          </h4>
          <p className="mt-0.5 text-xs text-slate-600">
            You've made progress in {moduleName}. Current: {confidenceLabel(currentValue)} ({currentValue}/5).
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {[1, 2, 3, 4, 5].map((v) => {
              const active = v === currentValue;
              return (
                <button
                  key={v}
                  type="button"
                  onClick={() => onRerate(v)}
                  className={`h-8 w-8 rounded-lg border text-sm font-semibold transition-colors ${
                    active
                      ? confidenceTone(v)
                      : "border-slate-200 bg-white text-slate-700 hover:border-blue-200 hover:bg-blue-50"
                  }`}
                  aria-pressed={active}
                  title={confidenceLabel(v)}
                >
                  {v}
                </button>
              );
            })}
          </div>
          <button
            onClick={onDismiss}
            className="mt-3 text-xs font-medium text-slate-500 hover:text-slate-800"
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}
