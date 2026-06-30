import React from "react";
import { apiRequest } from "./api";
import { CatalogGoal, CoreSkill, getCatalogGoal, useGoals } from "./goals";
import { useAuth } from "./auth";

export type ModuleTracking = {
  completedSteps: number[];
  consumedResources: number[];
  stepsCompletedSinceRerate: number;
  rerateDismissed: boolean;
};

export type WeekFocusKey = `${string}:${number}`;

export type GoalTracking = {
  modules: Record<string, ModuleTracking>;
  weekStartedAt: number;
  weekFocus: WeekFocusKey[];
};

export type TrackingState = Record<string, GoalTracking>;

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

function emptyTracking(): GoalTracking {
  return { modules: {}, weekStartedAt: 0, weekFocus: [] };
}

type TrackingContextValue = {
  state: TrackingState;
  refreshTracking: (goalId: string) => Promise<GoalTracking | null>;
  toggleStep: (goalId: string, moduleId: string, stepIdx: number) => void;
  toggleResource: (goalId: string, moduleId: string, resourceIdx: number) => void;
  setWeekFocus: (goalId: string, keys: WeekFocusKey[]) => void;
  markRerateDismissed: (goalId: string, moduleId: string) => void;
  resetRerateCounter: (goalId: string, moduleId: string) => void;
  getGoalTracking: (goalId: string) => GoalTracking;
};

const TrackingContext = React.createContext<TrackingContextValue | null>(null);

export function TrackingProvider({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth();
  const { goals } = useGoals();
  const [state, setState] = React.useState<TrackingState>({});

  const refreshTracking = React.useCallback(async (goalId: string): Promise<GoalTracking | null> => {
    if (!currentUser) return null;
    try {
      const tracking = await apiRequest<GoalTracking>(`/goals/${goalId}/tracking`);
      setState((prev) => ({ ...prev, [goalId]: tracking }));
      return tracking;
    } catch {
      return null;
    }
  }, [currentUser]);

  React.useEffect(() => {
    if (!currentUser) {
      setState({});
      return;
    }
    for (const goal of goals) {
      if (!state[goal.id]) void refreshTracking(goal.id);
    }
  }, [currentUser, goals, refreshTracking, state]);

  const replaceGoal = React.useCallback((goalId: string, tracking: GoalTracking) => {
    setState((prev) => ({ ...prev, [goalId]: tracking }));
  }, []);

  const toggleStep = React.useCallback<TrackingContextValue["toggleStep"]>(
    (goalId, moduleId, stepIdx) => {
      const current = state[goalId] ?? emptyTracking();
      const has = current.modules[moduleId]?.completedSteps.includes(stepIdx) ?? false;
      void apiRequest<GoalTracking>(`/goals/${goalId}/tracking/modules/${moduleId}/steps/${stepIdx}`, {
        method: "PUT",
        body: { completed: !has },
      }).then((tracking) => replaceGoal(goalId, tracking));
    },
    [state, replaceGoal]
  );

  const toggleResource = React.useCallback<TrackingContextValue["toggleResource"]>(
    (goalId, moduleId, resourceIdx) => {
      const current = state[goalId] ?? emptyTracking();
      const has = current.modules[moduleId]?.consumedResources.includes(resourceIdx) ?? false;
      void apiRequest<GoalTracking>(`/goals/${goalId}/tracking/modules/${moduleId}/resources/${resourceIdx}`, {
        method: "PUT",
        body: { consumed: !has },
      }).then((tracking) => replaceGoal(goalId, tracking));
    },
    [state, replaceGoal]
  );

  const setWeekFocus = React.useCallback<TrackingContextValue["setWeekFocus"]>(
    (goalId, keys) => {
      void apiRequest<GoalTracking>(`/goals/${goalId}/tracking/week-focus`, {
        method: "PUT",
        body: { weekFocus: keys },
      }).then((tracking) => replaceGoal(goalId, tracking));
    },
    [replaceGoal]
  );

  const markRerateDismissed = React.useCallback<TrackingContextValue["markRerateDismissed"]>(
    (goalId, moduleId) => {
      void apiRequest<GoalTracking>(`/goals/${goalId}/tracking/modules/${moduleId}/rerate-dismiss`, {
        method: "POST",
      }).then((tracking) => replaceGoal(goalId, tracking));
    },
    [replaceGoal]
  );

  const resetRerateCounter = React.useCallback<TrackingContextValue["resetRerateCounter"]>(
    (goalId) => {
      void refreshTracking(goalId);
    },
    [refreshTracking]
  );

  const getGoalTracking = React.useCallback(
    (goalId: string) => state[goalId] ?? emptyTracking(),
    [state]
  );

  const value = React.useMemo(
    () => ({
      state,
      refreshTracking,
      toggleStep,
      toggleResource,
      setWeekFocus,
      markRerateDismissed,
      resetRerateCounter,
      getGoalTracking,
    }),
    [state, refreshTracking, toggleStep, toggleResource, setWeekFocus, markRerateDismissed, resetRerateCounter, getGoalTracking]
  );

  return <TrackingContext.Provider value={value}>{children}</TrackingContext.Provider>;
}

export function useTracking(): TrackingContextValue {
  const ctx = React.useContext(TrackingContext);
  if (!ctx) {
    throw new Error("useTracking must be used inside TrackingProvider");
  }
  return ctx;
}

export function getModuleProgress(tracking: GoalTracking | undefined, module: CoreSkill): number {
  if (!tracking) return 0;
  const mod = tracking.modules[module.id];
  if (!mod) return 0;
  const total = module.whatToDo.length;
  if (total === 0) return 0;
  return Math.round((mod.completedSteps.length / total) * 100);
}

export function computeGoalProgress(tracking: GoalTracking | undefined, catalogGoal: CatalogGoal | undefined): number {
  if (!tracking || !catalogGoal) return 0;
  const progresses = catalogGoal.coreSkills.map((m) => getModuleProgress(tracking, m));
  if (progresses.length === 0) return 0;
  const avg = progresses.reduce((a, b) => a + b, 0) / progresses.length;
  return Math.round(avg);
}

export function getModuleTracking(tracking: GoalTracking | undefined, moduleId: string): ModuleTracking | undefined {
  return tracking?.modules[moduleId];
}

export function parseWeekFocusKey(key: WeekFocusKey): { moduleId: string; stepIdx: number } {
  const [moduleId, idxStr] = key.split(":");
  return { moduleId, stepIdx: Number(idxStr) };
}

export function buildWeekFocusKey(moduleId: string, stepIdx: number): WeekFocusKey {
  return `${moduleId}:${stepIdx}` as WeekFocusKey;
}

export function isWeekStale(tracking: GoalTracking | undefined): boolean {
  if (!tracking || !tracking.weekStartedAt) return true;
  return Date.now() - tracking.weekStartedAt > WEEK_MS;
}

export function pickWeekFocus(
  catalogGoal: CatalogGoal,
  tracking: GoalTracking | undefined,
  confidence: Record<string, number>,
  exclude: WeekFocusKey[] = [],
  size = 3
): WeekFocusKey[] {
  const excludeSet = new Set(exclude);
  const candidates: { key: WeekFocusKey; confidence: number; priority: number }[] = [];
  const sortedModules = [...catalogGoal.coreSkills].sort((a, b) => (confidence[a.id] ?? 3) - (confidence[b.id] ?? 3));
  const priorityWeight = (p: CoreSkill["priority"]) => (p === "High" ? 3 : p === "Medium" ? 2 : 1);
  for (const module of sortedModules) {
    const completed = new Set(tracking?.modules[module.id]?.completedSteps ?? []);
    for (let i = 0; i < module.whatToDo.length; i++) {
      if (completed.has(i)) continue;
      const key = buildWeekFocusKey(module.id, i);
      if (excludeSet.has(key)) continue;
      candidates.push({ key, confidence: confidence[module.id] ?? 3, priority: priorityWeight(module.priority) });
    }
  }
  candidates.sort((a, b) => (a.confidence !== b.confidence ? a.confidence - b.confidence : b.priority - a.priority));
  return candidates.slice(0, size).map((c) => c.key);
}

export function computeOverallProgressForGoalId(state: TrackingState, goalId: string): number {
  const catalogGoal = getCatalogGoal(goalId);
  if (!catalogGoal) return 0;
  return computeGoalProgress(state[goalId], catalogGoal);
}
