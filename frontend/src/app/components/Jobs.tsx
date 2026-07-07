import React from "react";
import { Link, useSearchParams } from "react-router";
import { Briefcase, Plus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useGoals } from "../lib/goals";
import { JobList } from "./JobList";

export function Jobs() {
  const { t } = useTranslation(["jobs", "nav"]);
  const { goals } = useGoals();
  const [searchParams, setSearchParams] = useSearchParams();

  const goalParam = searchParams.get("goal");
  const validParam = goalParam && goals.some((g) => g.id === goalParam) ? goalParam : null;
  const selectedGoalId = validParam ?? goals[0]?.id ?? null;

  const handleSelect = (id: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("goal", id);
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="space-y-8">
      <div>
        <p className="mb-2 text-sm font-medium text-blue-700">{t("eyebrow")}</p>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          {t("title")}
        </h1>
        <p className="mt-2 text-slate-600">{t("subtitle")}</p>
      </div>

      {goals.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50">
            <Briefcase className="h-6 w-6 text-blue-600" />
          </div>
          <h3 className="text-base font-semibold text-slate-950">{t("emptyTitle")}</h3>
          <p className="max-w-sm text-sm text-slate-600">{t("emptyBody")}</p>
          <Link
            to="/new-goal"
            className="mt-1 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            {t("nav:addFirstGoal")}
          </Link>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <label
              htmlFor="jobs-goal-filter"
              className="text-sm font-medium text-slate-700"
            >
              {t("showingFor")}
            </label>
            <select
              id="jobs-goal-filter"
              value={selectedGoalId ?? ""}
              onChange={(e) => handleSelect(e.target.value)}
              className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-900 outline-none transition-colors focus:border-blue-400 focus:ring-2 focus:ring-blue-100 sm:min-w-[16rem]"
            >
              {goals.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.title}
                </option>
              ))}
            </select>
          </div>

          {selectedGoalId && <JobList key={selectedGoalId} goalId={selectedGoalId} />}
        </>
      )}
    </div>
  );
}
