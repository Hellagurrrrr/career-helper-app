import React from "react";
import { apiRequest } from "./api";
import { useAuth } from "./auth";

export type AlumniProfile = {
  id: string;
  firstName: string;
  lastInitial: string;
  role: string;
  company: string;
  industry: string;
  graduationYear: number;
  major: string;
  university: string;
  yearsExperience: number;
  bio: string;
  expertise: string[];
  topics: string[];
  responseTime: string;
  availability: string;
  goalAlignment: string[];
  avatarGradient: string;
  linkedinUrl: string;
};

export const ALUMNI_CATALOG: AlumniProfile[] = [];

function setAlumniCache(items: AlumniProfile[]) {
  ALUMNI_CATALOG.splice(0, ALUMNI_CATALOG.length, ...items);
}

export async function loadAlumniCatalog(goalId?: string, q?: string): Promise<AlumniProfile[]> {
  const params = new URLSearchParams();
  if (goalId) params.set("goalId", goalId);
  if (q) params.set("q", q);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const items = await apiRequest<AlumniProfile[]>(`/alumni${suffix}`);
  setAlumniCache(items);
  return items;
}

export function getAlumni(id: string): AlumniProfile | undefined {
  return ALUMNI_CATALOG.find((a) => a.id === id);
}

export function countAlumniForKeywords(keywords: string[]): number {
  if (keywords.length === 0) return 0;
  const lows = keywords.map((k) => k.toLowerCase());
  return ALUMNI_CATALOG.filter((a) => {
    const haystack = [...a.expertise, ...a.topics, a.role, a.industry].join(" ").toLowerCase();
    return lows.some((k) => haystack.includes(k));
  }).length;
}

export function rankAlumniForUser(
  goalIds: string[],
  query?: string
): { alumni: AlumniProfile; score: number; matched: boolean }[] {
  const q = (query ?? "").trim().toLowerCase();
  return ALUMNI_CATALOG.map((alumni) => {
    let score = 0;
    let matched = false;
    for (const gid of goalIds) {
      if (alumni.goalAlignment.includes(gid)) {
        score += 5;
        matched = true;
      }
    }
    score += Math.min(alumni.yearsExperience, 10) * 0.2;
    if (q) {
      const haystack = [
        alumni.firstName,
        alumni.role,
        alumni.company,
        alumni.industry,
        alumni.major,
        ...alumni.expertise,
        ...alumni.topics,
      ].join(" ").toLowerCase();
      if (!haystack.includes(q)) score = -1;
    }
    return { alumni, score, matched };
  })
    .filter((x) => x.score >= 0)
    .sort((a, b) => b.score - a.score);
}

export type MeetingStatus = "pending" | "completed" | "withdrawn";

export type MeetingRequest = {
  id: string;
  alumniId: string;
  topic: string;
  message: string;
  preferredTimes: string[];
  submittedAt: number;
  status: MeetingStatus;
  completedAt?: number;
};

type MeetingsContextValue = {
  meetings: MeetingRequest[];
  alumni: AlumniProfile[];
  refreshMeetings: () => Promise<void>;
  refreshAlumni: () => Promise<void>;
  requestChat: (input: Omit<MeetingRequest, "id" | "submittedAt" | "status">) => MeetingRequest;
  withdrawRequest: (id: string) => void;
  completeRequest: (id: string) => void;
  getRequestForAlumni: (alumniId: string) => MeetingRequest | undefined;
};

const MeetingsContext = React.createContext<MeetingsContextValue | null>(null);

export function MeetingsProvider({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth();
  const [meetings, setMeetings] = React.useState<MeetingRequest[]>([]);
  const [alumni, setAlumni] = React.useState<AlumniProfile[]>([]);

  const refreshAlumni = React.useCallback(async () => {
    if (!currentUser) {
      setAlumni([]);
      setAlumniCache([]);
      return;
    }
    const items = await loadAlumniCatalog();
    setAlumni(items);
  }, [currentUser]);

  const refreshMeetings = React.useCallback(async () => {
    if (!currentUser) {
      setMeetings([]);
      return;
    }
    const items = await apiRequest<MeetingRequest[]>("/meetings");
    setMeetings(items);
  }, [currentUser]);

  React.useEffect(() => {
    void refreshAlumni();
    void refreshMeetings();
  }, [refreshAlumni, refreshMeetings]);

  const requestChat = React.useCallback<MeetingsContextValue["requestChat"]>(
    (input) => {
      const optimistic: MeetingRequest = {
        ...input,
        id: `pending_${Date.now().toString(36)}`,
        submittedAt: Date.now(),
        status: "pending",
      };
      setMeetings((prev) => {
        const existing = prev.find((m) => m.alumniId === input.alumniId && m.status === "pending");
        return existing ? prev : [optimistic, ...prev];
      });
      void apiRequest<MeetingRequest>("/meetings", {
        method: "POST",
        body: input,
      })
        .then((saved) =>
          setMeetings((prev) => [saved, ...prev.filter((m) => m.id !== optimistic.id)])
        )
        .catch(() => void refreshMeetings());
      return optimistic;
    },
    [refreshMeetings]
  );

  const withdrawRequest = React.useCallback((id: string) => {
    setMeetings((prev) => prev.filter((m) => m.id !== id));
    if (!id.startsWith("pending_")) {
      void apiRequest<MeetingRequest>(`/meetings/${id}`, {
        method: "PATCH",
        body: { status: "withdrawn" },
      }).then(() => refreshMeetings());
    }
  }, [refreshMeetings]);

  const completeRequest = React.useCallback((id: string) => {
    setMeetings((prev) =>
      prev.map((m) => (m.id === id ? { ...m, status: "completed", completedAt: Date.now() } : m))
    );
    if (!id.startsWith("pending_")) {
      void apiRequest<MeetingRequest>(`/meetings/${id}`, {
        method: "PATCH",
        body: { status: "completed" },
      }).then(() => refreshMeetings());
    }
  }, [refreshMeetings]);

  const getRequestForAlumni = React.useCallback(
    (alumniId: string) => meetings.find((m) => m.alumniId === alumniId && m.status === "pending"),
    [meetings]
  );

  const value = React.useMemo(
    () => ({
      meetings,
      alumni,
      refreshMeetings,
      refreshAlumni,
      requestChat,
      withdrawRequest,
      completeRequest,
      getRequestForAlumni,
    }),
    [meetings, alumni, refreshMeetings, refreshAlumni, requestChat, withdrawRequest, completeRequest, getRequestForAlumni]
  );

  return <MeetingsContext.Provider value={value}>{children}</MeetingsContext.Provider>;
}

export function useMeetings(): MeetingsContextValue {
  const ctx = React.useContext(MeetingsContext);
  if (!ctx) throw new Error("useMeetings must be used inside MeetingsProvider");
  return ctx;
}

export function formatRelativeDate(ts: number): string {
  const diff = Date.now() - ts;
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} min ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} hour${hr === 1 ? "" : "s"} ago`;
  const days = Math.floor(hr / 24);
  if (days < 30) return `${days} day${days === 1 ? "" : "s"} ago`;
  const months = Math.floor(days / 30);
  return `${months} month${months === 1 ? "" : "s"} ago`;
}
