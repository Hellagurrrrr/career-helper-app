import React from "react";
import { getCatalogGoal, useGoals } from "../lib/goals";
import {
  computeGoalProgress,
  useTracking,
  WeekFocusKey,
} from "../lib/tracking";
import { useNotifications } from "../lib/notifications";

const MILESTONES = [25, 50, 75, 100];

function makeMilestoneKey(goalId: string, milestone: number) {
  return `milestone:${goalId}:${milestone}`;
}

function makeWeekKey(goalId: string, weekStartedAt: number) {
  return `week:${goalId}:${weekStartedAt}`;
}

function findCrossedMilestone(progress: number): number | null {
  let crossed: number | null = null;
  for (const m of MILESTONES) {
    if (progress >= m) crossed = m;
  }
  return crossed;
}

export function NotificationOrchestrator() {
  const { goals } = useGoals();
  const { state: trackingState } = useTracking();
  const { notify, hasDedupKey } = useNotifications();

  const lastWeekFocusRef = React.useRef<Record<string, WeekFocusKey[]>>({});
  const initializedRef = React.useRef(false);

  React.useEffect(() => {
    for (const goal of goals) {
      const catalog = getCatalogGoal(goal.catalogId);
      if (!catalog) continue;
      const tracked = trackingState[goal.id];
      const progress = computeGoalProgress(tracked, catalog);
      const milestone = findCrossedMilestone(progress);
      if (milestone === null) continue;
      const dedupKey = makeMilestoneKey(goal.id, milestone);
      if (hasDedupKey(dedupKey)) continue;
      notify({
        type: "milestone",
        severity: milestone === 100 ? "success" : "info",
        title:
          milestone === 100
            ? `🎉 ${goal.title}: 100% complete!`
            : `${milestone}% milestone reached`,
        body:
          milestone === 100
            ? `You've completed every action step in ${goal.title}. Consider re-rating your skills or adding a new goal.`
            : `You're ${milestone}% through ${goal.title}. Keep the streak going.`,
        link: `/career-goal/${goal.id}/plan-tracking`,
        dedupKey,
      });
    }
  }, [goals, trackingState, notify, hasDedupKey]);

  React.useEffect(() => {
    for (const goal of goals) {
      const tracked = trackingState[goal.id];
      if (!tracked || !tracked.weekStartedAt) continue;

      const prev = lastWeekFocusRef.current[goal.id];
      const current = tracked.weekFocus;
      lastWeekFocusRef.current[goal.id] = current;

      if (!initializedRef.current) continue;

      if (prev === undefined) continue;

      const changed =
        prev.length !== current.length ||
        prev.some((k, i) => k !== current[i]);
      if (!changed) continue;
      if (current.length === 0) continue;

      const dedupKey = makeWeekKey(goal.id, tracked.weekStartedAt);
      if (hasDedupKey(dedupKey)) continue;

      notify({
        type: "week",
        severity: "info",
        title: `Fresh weekly focus for ${goal.title}`,
        body: `${current.length} new actions picked from your weakest skills. Ready when you are.`,
        link: `/career-goal/${goal.id}/plan-tracking`,
        dedupKey,
      });
    }

    if (!initializedRef.current) {
      initializedRef.current = true;
    }
  }, [goals, trackingState, notify, hasDedupKey]);

  return null;
}
