import React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest, errorMessage } from "./api";
import { useAuth } from "./auth";
import { queryClient } from "./query-client";

export const goalCatalogKey = ["goal-catalog"] as const;
export const goalsKey = ["goals"] as const;

export type SkillResource = {
  title: string;
  type: string;
  url: string;
};

export type CoreSkill = {
  id: string;
  name: string;
  description: string;
  priority: "High" | "Medium" | "Low";
  defaultStatus: string;
  whatToDo: string[];
  resources: SkillResource[];
  jobSkillKeywords: string[];
};

export type CatalogGoal = {
  id: string;
  title: string;
  description: string;
  color: string;
  matchSignals: string[];
  defaultStatus: "active" | "exploring";
  coreSkills: CoreSkill[];
};

export type UserGoal = {
  id: string;
  catalogId: string;
  title: string;
  description: string;
  color: string;
  status: "active" | "exploring";
  progress: number;
  lastUpdated: string;
  createdAt: number;
  confidence: Record<string, number>;
  sortOrder?: number;
};

function normalizeCatalog(goal: CatalogGoal): CatalogGoal {
  return {
    ...goal,
    coreSkills: (goal.coreSkills ?? []).map((skill) => ({
      priority: "Medium",
      ...skill,
      whatToDo: skill.whatToDo ?? [],
      resources: skill.resources ?? [],
      jobSkillKeywords: skill.jobSkillKeywords ?? [],
    })),
  };
}

// Single source of truth: the (already normalized) catalog held by React Query.
// Lets the module-level readers below work outside of a component/hook.
function cachedCatalog(): CatalogGoal[] {
  return queryClient.getQueryData<CatalogGoal[]>(goalCatalogKey) ?? [];
}

function setGoalsCache(updater: (prev: UserGoal[]) => UserGoal[]): void {
  queryClient.setQueryData<UserGoal[]>(goalsKey, (prev) => updater(prev ?? []));
}

export function useGoals() {
  const { currentUser } = useAuth();
  const enabled = Boolean(currentUser);
  // Surfaced only for addGoal (the one mutation that reports errors inline).
  const [mutationError, setMutationError] = React.useState<string | null>(null);

  const catalogQuery = useQuery({
    queryKey: goalCatalogKey,
    queryFn: async () => (await apiRequest<CatalogGoal[]>("/goal-catalog")).map(normalizeCatalog),
    enabled,
  });

  const goalsQuery = useQuery({
    queryKey: goalsKey,
    queryFn: () => apiRequest<UserGoal[]>("/goals"),
    enabled,
  });

  const goals = goalsQuery.data ?? [];
  const catalog = catalogQuery.data ?? [];
  const queryError = catalogQuery.error ?? goalsQuery.error;

  return {
    goals,
    catalog,
    loading: catalogQuery.isLoading || goalsQuery.isLoading,
    error: queryError ? errorMessage(queryError, "Could not load goals.") : mutationError,
    refreshGoals: async () => {
      await Promise.all([catalogQuery.refetch(), goalsQuery.refetch()]);
    },
    addGoal: async (
      goal: UserGoal | { catalogId: string; confidence?: Record<string, number> }
    ): Promise<UserGoal | null> => {
      const catalogId = "catalogId" in goal ? goal.catalogId : goal.id;
      try {
        let created = await apiRequest<UserGoal>("/goals", { method: "POST", body: { catalogId } });
        const confidence = "confidence" in goal ? goal.confidence : undefined;
        if (confidence && Object.keys(confidence).length > 0) {
          created = await apiRequest<UserGoal>(`/goals/${created.id}`, {
            method: "PATCH",
            body: { confidence },
          });
        }
        setGoalsCache((prev) => [...prev.filter((g) => g.id !== created.id), created]);
        setMutationError(null);
        return created;
      } catch (err) {
        setMutationError(errorMessage(err, "Could not add goal."));
        return null;
      }
    },
    removeGoal: async (id: string) => {
      await apiRequest<void>(`/goals/${id}`, { method: "DELETE" });
      setGoalsCache((prev) => prev.filter((g) => g.id !== id));
    },
    reorderGoals: async (fromIndex: number, toIndex: number) => {
      if (
        fromIndex < 0 ||
        fromIndex >= goals.length ||
        toIndex < 0 ||
        toIndex >= goals.length ||
        fromIndex === toIndex
      ) {
        return;
      }
      const next = [...goals];
      const [moved] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, moved);
      setGoalsCache(() => next);
      const saved = await apiRequest<UserGoal[]>("/goals/order", {
        method: "PUT",
        body: { goalIds: next.map((g) => g.id) },
      });
      setGoalsCache(() => saved);
    },
    updateConfidence: async (id: string, skillId: string, value: number) => {
      const current = goals.find((g) => g.id === id);
      if (!current) return;
      const confidence = { ...current.confidence, [skillId]: value };
      const updated = await apiRequest<UserGoal>(`/goals/${id}`, {
        method: "PATCH",
        body: { confidence },
      });
      setGoalsCache((prev) => prev.map((g) => (g.id === id ? updated : g)));
    },
    getGoal: (id: string) => goals.find((g) => g.id === id || g.catalogId === id),
  };
}

export function getCatalogGoal(id: string): CatalogGoal | undefined {
  return cachedCatalog().find((g) => g.id === id);
}

export function getCatalogSkill(goalId: string, skillId: string): CoreSkill | undefined {
  return getCatalogGoal(goalId)?.coreSkills.find((s) => s.id === skillId);
}

export function rankGoalsForProfile(
  profileSkills: string[],
  major?: string
): { goal: CatalogGoal; score: number }[] {
  const lowercaseSkills = profileSkills.map((x) => x.toLowerCase());
  const lowMajor = (major ?? "").toLowerCase();

  const scoreOf = (goal: CatalogGoal): number => {
    let score = 0;
    for (const sig of goal.matchSignals) {
      const low = sig.toLowerCase();
      if (lowercaseSkills.some((sk) => sk === low || sk.includes(low) || low.includes(sk))) {
        score += 2;
      }
    }
    if (lowMajor && goal.matchSignals.some((s) => lowMajor.includes(s.toLowerCase()))) score += 1;
    return score;
  };

  return cachedCatalog()
    .map((goal) => ({ goal, score: scoreOf(goal) }))
    .sort((a, b) => b.score - a.score);
}

// Accepts the `tracking`-namespace translator so confidence labels localize.
type ConfidenceTranslate = (key: string) => string;

export function confidenceLabel(value: number, t: ConfidenceTranslate): string {
  if (value >= 1 && value <= 5) return t(`confidence.${value}`);
  return t("confidence.unknown");
}

export function confidenceTone(value: number): string {
  if (value <= 2) return "bg-red-50 text-red-800 border-red-200";
  if (value === 3) return "bg-amber-50 text-amber-800 border-amber-200";
  return "bg-green-50 text-green-800 border-green-200";
}
