import React from "react";
import { Outlet, NavLink, Link, useParams } from "react-router";
import { Target, Briefcase, ChevronRight, Plus } from "lucide-react";
import { useGoals } from "../lib/goals";

export function CareerGoalLayout() {
  const { goalId } = useParams();
  const { getGoal } = useGoals();
  const goal = goalId ? getGoal(goalId) : undefined;

  if (!goal) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
        <h2 className="text-lg font-semibold text-slate-950">Career goal not found</h2>
        <p className="mt-2 text-sm text-slate-600">
          You haven't added this goal yet. Pick one from the catalog and we'll
          build a learning plan for you.
        </p>
        <div className="mt-4 flex flex-col items-center justify-center gap-2 sm:flex-row">
          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          >
            Back to dashboard
          </Link>
          <Link
            to="/new-goal"
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Add a goal
          </Link>
        </div>
      </div>
    );
  }

  const currentSection = "Plan Tracking";

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200/70 bg-white p-4 sm:p-5">
        <nav aria-label="breadcrumb" className="mb-4">
          <ol className="flex flex-wrap items-center gap-1.5 text-sm text-slate-500">
            <li>
              <Link
                to="/"
                className="rounded-md px-1 transition-colors hover:bg-slate-100 hover:text-slate-900"
              >
                Dashboard
              </Link>
            </li>
            <li aria-hidden="true">
              <ChevronRight className="h-4 w-4 text-slate-400" />
            </li>
            <li className="font-medium text-slate-700">{goal.title}</li>
            <li aria-hidden="true">
              <ChevronRight className="h-4 w-4 text-slate-400" />
            </li>
            <li className="font-medium text-slate-950">{currentSection}</li>
          </ol>
        </nav>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${goal.color}`}
            >
              <Target className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-950">
                {goal.title}
              </h1>
              <p className="text-sm text-slate-600">
                Explore your path to becoming a {goal.title.toLowerCase()}
              </p>
            </div>
          </div>

          <div className="rounded-xl bg-blue-50 px-4 py-3 text-sm text-slate-700">
            <span className="font-semibold text-blue-800">{goal.progress}%</span> overall progress
          </div>
        </div>

        <div className="mt-5 flex gap-2 border-t border-slate-100 pt-4">
          <NavLink
            to={`/career-goal/${goalId}/plan-tracking`}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-blue-50 text-blue-800"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`
            }
          >
            <Target className="h-4 w-4" />
            Plan Tracking
          </NavLink>
          <Link
            to={`/jobs?goal=${goalId}`}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900"
          >
            <Briefcase className="h-4 w-4" />
            View jobs for this goal
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <Outlet />
    </div>
  );
}
