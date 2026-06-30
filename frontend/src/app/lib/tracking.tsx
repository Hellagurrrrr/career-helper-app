import React from "react";
import { useQueries } from "@tanstack/react-query";
import { apiRequest } from "./api";
import { CatalogGoal, CoreSkill, getCatalogGoal, useGoals } from "./goals";
import { useAuth } from "./auth";
import { queryClient } from "./query-client";

export const trackingKey = (goalId: string) => ["tracking", goalId] as const;

function fetchTracking(goalId: string): Promise<GoalTracking> {
  return apiRequest<GoalTracking>(`/goals/${goalId}/tracking`);
}

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

export function useTracking() {
  const { currentUser } = useAuth();
  const { goals } = useGoals();
  const enabled = Boolean(currentUser);

  // One query per goal (the API is per-goal). useQueries handles the dynamic list.
  const results = useQueries({
    queries: goals.map((g) => ({
      queryKey: trackingKey(g.id),
      queryFn: () => fetchTracking(g.id),
      enabled,
    })),
  });

  // Aggregate into the { goalId: tracking } map the consumers expect. Memoized
  // on a (goalId, dataUpdatedAt) signature so `state` stays referentially stable
  // unless a goal's tracking actually changes -- consumer effects depend on it.
  const signature = goals.map((g, i) => `${g.id}:${results[i]?.dataUpdatedAt ?? 0}`).join("|");
  const state = React.useMemo<TrackingState>(() => {
    const next: TrackingState = {};
    goals.forEach((g, i) => {
      const data = results[i]?.data;
      if (data) next[g.id] = data;
    });
    return next;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature]);

  const refreshTracking = React.useCallback(
    async (goalId: string): Promise<GoalTracking | null> => {
      if (!currentUser) return null;
      try {
        return await queryClient.fetchQuery({
          queryKey: trackingKey(goalId),
          queryFn: () => fetchTracking(goalId),
        });
      } catch {
        return null;
      }
    },
    [currentUser]
  );

  const toggleStep = React.useCallback(
    (goalId: string, moduleId: string, stepIdx: number) => {
      const has = state[goalId]?.modules[moduleId]?.completedSteps.includes(stepIdx) ?? false;
      void apiRequest<GoalTracking>(`/goals/${goalId}/tracking/modules/${moduleId}/steps/${stepIdx}`, {
        method: "PUT",
        body: { completed: !has },
      }).then((tracking) => queryClient.setQueryData(trackingKey(goalId), tracking));
    },
    [state]
  );

  const toggleResource = React.useCallback(
    (goalId: string, moduleId: string, resourceIdx: number) => {
      const has = state[goalId]?.modules[moduleId]?.consumedResources.includes(resourceIdx) ?? false;
      void apiRequest<GoalTracking>(`/goals/${goalId}/tracking/modules/${moduleId}/resources/${resourceIdx}`, {
        method: "PUT",
        body: { consumed: !has },
      }).then((tracking) => queryClient.setQueryData(trackingKey(goalId), tracking));
    },
    [state]
  );

  const setWeekFocus = React.useCallback((goalId: string, keys: WeekFocusKey[]) => {
    void apiRequest<GoalTracking>(`/goals/${goalId}/tracking/week-focus`, {
      method: "PUT",
      body: { weekFocus: keys },
    }).then((tracking) => queryClient.setQueryData(trackingKey(goalId), tracking));
  }, []);

  const markRerateDismissed = React.useCallback((goalId: string, moduleId: string) => {
    void apiRequest<GoalTracking>(`/goals/${goalId}/tracking/modules/${moduleId}/rerate-dismiss`, {
      method: "POST",
    }).then((tracking) => queryClient.setQueryData(trackingKey(goalId), tracking));
  }, []);

  const resetRerateCounter = React.useCallback(
    (goalId: string) => {
      void refreshTracking(goalId);
    },
    [refreshTracking]
  );

  const getGoalTracking = React.useCallback(
    (goalId: string) => state[goalId] ?? emptyTracking(),
    [state]
  );

  return {
    state,
    refreshTracking,
    toggleStep,
    toggleResource,
    setWeekFocus,
    markRerateDismissed,
    resetRerateCounter,
    getGoalTracking,
  };
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
