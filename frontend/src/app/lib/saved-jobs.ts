/** Per career goal: indices into `JOBS_BY_GOAL[goalId].jobs` (stable for this mock catalog). */
export type SavedJobsByGoal = Record<string, number[]>;

const STORAGE_KEY = "aichh:saved-jobs-by-goal";

export function loadSavedJobsByGoal(): SavedJobsByGoal {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const out: SavedJobsByGoal = {};
    for (const [goalId, val] of Object.entries(parsed)) {
      if (Array.isArray(val) && val.every((x) => typeof x === "number" && Number.isInteger(x))) {
        out[goalId] = [...new Set(val as number[])].sort((a, b) => a - b);
      }
    }
    return out;
  } catch {
    return {};
  }
}

export function persistSavedJobsByGoal(state: SavedJobsByGoal) {
  if (typeof window === "undefined") return;
  const cleaned: SavedJobsByGoal = {};
  for (const [gid, arr] of Object.entries(state)) {
    if (arr.length > 0) cleaned[gid] = [...new Set(arr)].sort((a, b) => a - b);
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cleaned));
}

export function indicesToSet(goalId: string, state: SavedJobsByGoal): Set<number> {
  return new Set(state[goalId] ?? []);
}

export function toggleSavedIndex(
  goalId: string,
  state: SavedJobsByGoal,
  index: number
): SavedJobsByGoal {
  const set = new Set(state[goalId] ?? []);
  if (set.has(index)) set.delete(index);
  else set.add(index);
  const next = { ...state, [goalId]: [...set].sort((a, b) => a - b) };
  if (next[goalId].length === 0) {
    const { [goalId]: _, ...rest } = next;
    return rest;
  }
  return next;
}
