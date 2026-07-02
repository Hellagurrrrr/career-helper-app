import { useMutation, useQuery } from "@tanstack/react-query";
import { ApiError, apiRequest, errorMessage, getAccessToken, getRefreshToken } from "./api";
import { useAuth } from "./auth";
import { queryClient } from "./query-client";

export const profileKey = ["profile"] as const;

export type Education = {
  degree: string;
  school: string;
  major: string;
  grade: number | null;
  start: string;
  end: string | null;
};

export type Internship = {
  title: string;
  company: string;
  start: string;
  end: string | null;
  description: string;
};

export type Project = {
  title: string;
  start: string;
  end: string | null;
  description: string;
};

export type Profile = {
  name: string;
  education: Education[];
  internships: Internship[];
  projects: Project[];
  skills: string[];
  coursework: string[];
  updatedAt: number;
};

export const EMPTY_PROFILE: Profile = {
  name: "",
  education: [],
  internships: [],
  projects: [],
  skills: [],
  coursework: [],
  updatedAt: 0,
};

export const EMPTY_EDUCATION: Education = {
  degree: "",
  school: "",
  major: "",
  grade: null,
  start: "",
  end: null,
};

export const EMPTY_INTERNSHIP: Internship = {
  title: "",
  company: "",
  start: "",
  end: null,
  description: "",
};

export const EMPTY_PROJECT: Project = {
  title: "",
  start: "",
  end: null,
  description: "",
};

export function latestEducation(profile: Profile | null): Education | null {
  return profile?.education[0] ?? null;
}

export function formatPeriod(start: string, end: string | null): string {
  if (!start && !end) return "";
  const from = start || "?";
  const to = end ?? "present";
  return `${from} - ${to}`;
}

function normalizeProfile(profile: Profile): Profile {
  return {
    ...EMPTY_PROFILE,
    ...profile,
    education: (profile.education ?? []).map((e) => ({ ...EMPTY_EDUCATION, ...e })),
    internships: (profile.internships ?? []).map((e) => ({ ...EMPTY_INTERNSHIP, ...e })),
    projects: (profile.projects ?? []).map((e) => ({ ...EMPTY_PROJECT, ...e })),
    skills: profile.skills ?? [],
    coursework: profile.coursework ?? [],
  };
}

type UseProfile = {
  profile: Profile | null;
  loading: boolean;
  error: string | null;
  saveProfile: (profile: Profile) => Promise<void>;
  clearProfile: () => void;
  refreshProfile: () => Promise<Profile | null>;
};

// Fetch the profile. A 404 means "not created yet" -> null (not an error).
async function fetchProfile(): Promise<Profile | null> {
  try {
    return normalizeProfile(await apiRequest<Profile>("/profile"));
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export function useProfile(): UseProfile {
  const { currentUser } = useAuth();
  const enabled = Boolean(currentUser || getAccessToken() || getRefreshToken());

  const query = useQuery({
    queryKey: profileKey,
    queryFn: fetchProfile,
    enabled,
  });

  const save = useMutation({
    mutationFn: (next: Profile) => apiRequest<Profile>("/profile", { method: "PUT", body: next }),
    onSuccess: (saved) => queryClient.setQueryData(profileKey, normalizeProfile(saved)),
  });

  return {
    profile: query.data ?? null,
    loading: query.isLoading,
    error: query.error ? errorMessage(query.error, "Could not load profile.") : null,
    saveProfile: async (next) => {
      await save.mutateAsync(next);
    },
    clearProfile: () => queryClient.setQueryData(profileKey, null),
    refreshProfile: async () => (await query.refetch()).data ?? null,
  };
}

export function parseCommaList(input: string): string[] {
  return input
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);
}
