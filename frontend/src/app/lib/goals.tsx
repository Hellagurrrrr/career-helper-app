import React from "react";
import { apiRequest, errorMessage } from "./api";
import { useAuth } from "./auth";

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

export const GOAL_CATALOG: CatalogGoal[] = [];

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

function setCatalogCache(goals: CatalogGoal[]) {
  GOAL_CATALOG.splice(0, GOAL_CATALOG.length, ...goals.map(normalizeCatalog));
}

type GoalsContextValue = {
  goals: UserGoal[];
  catalog: CatalogGoal[];
  loading: boolean;
  error: string | null;
  refreshGoals: () => Promise<void>;
  addGoal: (goal: UserGoal | { catalogId: string; confidence?: Record<string, number> }) => Promise<UserGoal | null>;
  removeGoal: (id: string) => Promise<void>;
  reorderGoals: (fromIndex: number, toIndex: number) => Promise<void>;
  updateConfidence: (id: string, skillId: string, value: number) => Promise<void>;
  getGoal: (id: string) => UserGoal | undefined;
};

const GoalsContext = React.createContext<GoalsContextValue | null>(null);

export function GoalsProvider({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth();
  const [goals, setGoals] = React.useState<UserGoal[]>([]);
  const [catalog, setCatalog] = React.useState<CatalogGoal[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refreshGoals = React.useCallback(async () => {
    if (!currentUser) {
      setGoals([]);
      setCatalog([]);
      setCatalogCache([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [catalogResponse, goalsResponse] = await Promise.all([
        apiRequest<CatalogGoal[]>("/goal-catalog"),
        apiRequest<UserGoal[]>("/goals"),
      ]);
      const normalized = catalogResponse.map(normalizeCatalog);
      setCatalog(normalized);
      setCatalogCache(normalized);
      setGoals(goalsResponse);
    } catch (err) {
      setError(errorMessage(err, "Could not load goals."));
    } finally {
      setLoading(false);
    }
  }, [currentUser]);

  React.useEffect(() => {
    void refreshGoals();
  }, [refreshGoals]);

  const addGoal = React.useCallback<GoalsContextValue["addGoal"]>(async (goal) => {
    const catalogId = "catalogId" in goal ? goal.catalogId : goal.id;
    try {
      let created = await apiRequest<UserGoal>("/goals", {
        method: "POST",
        body: { catalogId },
      });
      const confidence = "confidence" in goal ? goal.confidence : undefined;
      if (confidence && Object.keys(confidence).length > 0) {
        created = await apiRequest<UserGoal>(`/goals/${created.id}`, {
          method: "PATCH",
          body: { confidence },
        });
      }
      setGoals((prev) => [...prev.filter((g) => g.id !== created.id), created]);
      return created;
    } catch (err) {
      setError(errorMessage(err, "Could not add goal."));
      return null;
    }
  }, []);

  const removeGoal = React.useCallback(async (id: string) => {
    await apiRequest<void>(`/goals/${id}`, { method: "DELETE" });
    setGoals((prev) => prev.filter((g) => g.id !== id));
  }, []);

  const reorderGoals = React.useCallback(
    async (fromIndex: number, toIndex: number) => {
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
      setGoals(next);
      const saved = await apiRequest<UserGoal[]>("/goals/order", {
        method: "PUT",
        body: { goalIds: next.map((g) => g.id) },
      });
      setGoals(saved);
    },
    [goals]
  );

  const updateConfidence = React.useCallback(async (id: string, skillId: string, value: number) => {
    const current = goals.find((g) => g.id === id);
    if (!current) return;
    const confidence = { ...current.confidence, [skillId]: value };
    const updated = await apiRequest<UserGoal>(`/goals/${id}`, {
      method: "PATCH",
      body: { confidence },
    });
    setGoals((prev) => prev.map((g) => (g.id === id ? updated : g)));
  }, [goals]);

  const getGoal = React.useCallback(
    (id: string) => goals.find((g) => g.id === id || g.catalogId === id),
    [goals]
  );

  const value = React.useMemo(
    () => ({
      goals,
      catalog,
      loading,
      error,
      refreshGoals,
      addGoal,
      removeGoal,
      reorderGoals,
      updateConfidence,
      getGoal,
    }),
    [goals, catalog, loading, error, refreshGoals, addGoal, removeGoal, reorderGoals, updateConfidence, getGoal]
  );

  return <GoalsContext.Provider value={value}>{children}</GoalsContext.Provider>;
}

export function useGoals(): GoalsContextValue {
  const ctx = React.useContext(GoalsContext);
  if (!ctx) throw new Error("useGoals must be used inside a GoalsProvider");
  return ctx;
}

export function getCatalogGoal(id: string): CatalogGoal | undefined {
  return GOAL_CATALOG.find((g) => g.id === id);
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

  return GOAL_CATALOG.map((goal) => ({ goal, score: scoreOf(goal) })).sort((a, b) => b.score - a.score);
}

export function confidenceLabel(value: number): string {
  switch (value) {
    case 1:
      return "Just starting";
    case 2:
      return "Some exposure";
    case 3:
      return "Comfortable";
    case 4:
      return "Confident";
    case 5:
      return "Expert";
    default:
      return "Unknown";
  }
}

export function confidenceTone(value: number): string {
  if (value <= 2) return "bg-red-50 text-red-800 border-red-200";
  if (value === 3) return "bg-amber-50 text-amber-800 border-amber-200";
  return "bg-green-50 text-green-800 border-green-200";
}
