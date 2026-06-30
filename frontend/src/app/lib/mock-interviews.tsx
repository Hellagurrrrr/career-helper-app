import React from "react";
import type { InterviewDimensionScore } from "./interview-reviews";
import { apiRequest } from "./api";
import { useAuth } from "./auth";

const STORAGE_KEY = "aichh:mock-interviews-v1";

export type MockInterviewTurn = {
  id: string;
  role: "coach" | "user";
  text: string;
  timestamp: number;
};

export type MockInterviewSession = {
  id: string;
  applicationId: string;
  jobTitle: string;
  company: string;
  goalTitle?: string;
  skills: string[];
  startedAt: number;
  completedAt: number;
  turns: MockInterviewTurn[];
  transcript: string;
  overallSummary: string;
  dimensions: InterviewDimensionScore[];
  improvementAdvice: string;
  durationSec: number;
};

export type MockInterviewContext = {
  applicationId: string;
  jobTitle: string;
  company: string;
  goalTitle?: string;
  skills: string[];
};

const DEMO_QUESTIONS = [
  (ctx: MockInterviewContext) =>
    `Hi! I'm your AI interview coach. Let's practice for the ${ctx.jobTitle} role at ${ctx.company}. First — in about 90 seconds, tell me why you're interested in this position.`,
  (ctx: MockInterviewContext) =>
    `Thanks. Now walk me through a recent project where you used skills relevant to ${ctx.skills.slice(0, 2).join(" and ") || "this role"}. What was your specific contribution?`,
  (ctx: MockInterviewContext) =>
    `Good context. Here's a scenario: a critical feature is behind schedule two weeks before launch at ${ctx.company}. How would you diagnose the problem and communicate with stakeholders?`,
  (ctx: MockInterviewContext) =>
    `Last question — what would you want to learn in your first 90 days as a ${ctx.jobTitle}, and what questions would you ask the hiring manager?`,
];

export type MockStartResponse = {
  sessionId: string;
  status: "in_progress";
  question: string;
  questionIndex: number;
  totalQuestions: number;
};

export type MockTurnResponse = {
  status: "in_progress" | "complete" | "scoring";
  question?: string | null;
  questionIndex?: number | null;
  totalQuestions?: number | null;
  session?: MockInterviewSession | null;
};

export async function startServerMockInterview(applicationId: string): Promise<MockStartResponse> {
  return apiRequest<MockStartResponse>(`/applications/${applicationId}/mock-interviews`, {
    method: "POST",
  });
}

export async function submitServerMockTurn(
  applicationId: string,
  sessionId: string,
  text: string,
  end = false
): Promise<MockTurnResponse> {
  return apiRequest<MockTurnResponse>(`/applications/${applicationId}/mock-interviews/${sessionId}/turns`, {
    method: "POST",
    body: { text, end },
  });
}

function loadAll(): MockInterviewSession[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isValidSession);
  } catch {
    return [];
  }
}

function isValidSession(x: unknown): x is MockInterviewSession {
  if (!x || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.applicationId === "string" &&
    typeof o.jobTitle === "string" &&
    typeof o.company === "string" &&
    typeof o.startedAt === "number" &&
    typeof o.completedAt === "number" &&
    Array.isArray(o.turns) &&
    typeof o.transcript === "string" &&
    typeof o.overallSummary === "string" &&
    typeof o.improvementAdvice === "string" &&
    Array.isArray(o.dimensions)
  );
}

function persist(sessions: MockInterviewSession[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

function hashSeed(input: string): number {
  let h = 0;
  for (let i = 0; i < input.length; i++) h = (h * 31 + input.charCodeAt(i)) | 0;
  return Math.abs(h);
}

function scoreFromSeed(seed: number, offset: number): number {
  const raw = ((seed + offset * 97) % 1000) / 1000;
  return Math.round((6.0 + raw * 2.8) * 10) / 10;
}

function newId(prefix: string): string {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${prefix}-${Date.now()}`;
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function getCoachOpening(ctx: MockInterviewContext): string {
  return DEMO_QUESTIONS[0](ctx);
}

export function getNextCoachQuestion(
  ctx: MockInterviewContext,
  questionIndex: number
): string | null {
  if (questionIndex >= DEMO_QUESTIONS.length) return null;
  return DEMO_QUESTIONS[questionIndex](ctx);
}

export const MOCK_QUESTION_COUNT = DEMO_QUESTIONS.length;

/** Demo: speak coach line via browser TTS (no server). */
export function speakCoachLine(
  text: string,
  onEnd?: () => void
): SpeechSynthesisUtterance | null {
  if (typeof window === "undefined" || !window.speechSynthesis) {
    onEnd?.();
    return null;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.95;
  utterance.pitch = 1;
  const voices = window.speechSynthesis.getVoices();
  const preferred =
    voices.find((v) => v.lang.startsWith("en") && v.name.includes("Google")) ??
    voices.find((v) => v.lang.startsWith("en")) ??
    voices[0];
  if (preferred) utterance.voice = preferred;
  if (onEnd) utterance.onend = onEnd;
  window.speechSynthesis.speak(utterance);
  return utterance;
}

export function stopCoachSpeech() {
  if (typeof window !== "undefined" && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

export type SpeechRecognitionCtor = new () => SpeechRecognition;

export function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as Window & {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export async function runMockInterviewEvaluation(
  ctx: MockInterviewContext,
  turns: MockInterviewTurn[],
  durationSec: number
): Promise<Pick<
  MockInterviewSession,
  "transcript" | "overallSummary" | "dimensions" | "improvementAdvice"
>> {
  await delay(1200);
  const seed = hashSeed(
    `${ctx.applicationId}:${turns.map((t) => t.text).join("|")}:${durationSec}`
  );
  const skillFocus = ctx.skills.slice(0, 3).join(", ") || "core role competencies";
  const roleLabel = ctx.goalTitle
    ? `${ctx.jobTitle} (${ctx.goalTitle} track)`
    : ctx.jobTitle;

  const transcript = turns
    .map((t) => {
      const label = t.role === "coach" ? "Coach" : "You";
      const time = new Date(t.timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
      return `[${time}] ${label}: ${t.text}`;
    })
    .join("\n");

  const userTurns = turns.filter((t) => t.role === "user");
  const avgWords =
    userTurns.length > 0
      ? userTurns.reduce((s, t) => s + t.text.split(/\s+/).length, 0) /
        userTurns.length
      : 0;

  const dimensions: InterviewDimensionScore[] = [
    {
      id: "role_fit",
      label: "Role alignment",
      score: scoreFromSeed(seed, 1),
      narrative: `Your answers connected to ${roleLabel} at ${ctx.company}. Mentioning ${skillFocus} more explicitly in each response would strengthen fit signals for hiring managers.`,
    },
    {
      id: "depth",
      label: "Technical / competency depth",
      score: scoreFromSeed(seed, 2),
      narrative: `You showed workable depth in the mock. For ${ctx.jobTitle}, add one layer of detail — metrics, trade-offs, or failure modes — to each technical story.`,
    },
    {
      id: "communication",
      label: "Communication & structure",
      score: scoreFromSeed(seed, 3),
      narrative:
        avgWords > 80
          ? "Responses were thorough but occasionally long. Practice tighter STAR structure: Situation → Action → Result in under 2 minutes per answer."
          : "Responses were concise. Ensure each answer ends with a clear outcome or learning to leave a memorable impression.",
    },
    {
      id: "problem_solving",
      label: "Problem-solving & examples",
      score: scoreFromSeed(seed, 4),
      narrative: `Scenario answers showed reasonable judgment. Quantify impact (time saved, users affected, error rate) to differentiate from other ${ctx.jobTitle} candidates.`,
    },
    {
      id: "presence",
      label: "Professional presence",
      score: scoreFromSeed(seed, 5),
      narrative: `Voice delivery in this demo session came across as ${avgWords > 40 ? "engaged and thoughtful" : "brief — expand with one concrete example per question"}. A confident 90-second opener would sharpen your first impression.`,
    },
  ];

  const avg =
    Math.round(
      (dimensions.reduce((s, d) => s + d.score, 0) / dimensions.length) * 10
    ) / 10;

  const overallSummary = `This ${Math.max(1, Math.round(durationSec / 60))}-minute mock interview for ${ctx.jobTitle} at ${ctx.company} scored ${avg}/10 overall — a ${avg >= 7.5 ? "strong" : avg >= 6.5 ? "solid" : "developing"} practice session. You answered ${userTurns.length} coach prompts with role-relevant examples. The session is archived so you can compare scores over time.`;

  const improvementAdvice = `For your next mock on this role: (1) Open with a crisp "why ${ctx.company} / why ${ctx.jobTitle}" narrative. (2) Prepare two STAR stories naming ${skillFocus} with measurable outcomes. (3) For scenario questions, state assumptions, options, and your recommendation before diving into details. Run another mock here and watch dimension scores improve.`;

  return { transcript, overallSummary, dimensions, improvementAdvice };
}

export function buildMockSession(
  ctx: MockInterviewContext,
  turns: MockInterviewTurn[],
  startedAt: number,
  evaluation: Pick<
    MockInterviewSession,
    "transcript" | "overallSummary" | "dimensions" | "improvementAdvice"
  >
): MockInterviewSession {
  const completedAt = Date.now();
  return {
    id: newId("mi"),
    applicationId: ctx.applicationId,
    jobTitle: ctx.jobTitle,
    company: ctx.company,
    goalTitle: ctx.goalTitle,
    skills: ctx.skills,
    startedAt,
    completedAt,
    turns,
    durationSec: Math.round((completedAt - startedAt) / 1000),
    ...evaluation,
  };
}

type MockInterviewsContextValue = {
  sessions: MockInterviewSession[];
  getSessionsForApplication: (applicationId: string) => MockInterviewSession[];
  getSessionById: (id: string) => MockInterviewSession | undefined;
  saveSession: (session: MockInterviewSession) => void;
  deleteSession: (id: string) => void;
};

const MockInterviewsContext =
  React.createContext<MockInterviewsContextValue | null>(null);

export function MockInterviewsProvider({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth();
  const [sessions, setSessions] = React.useState<MockInterviewSession[]>([]);

  React.useEffect(() => {
    if (!currentUser) setSessions([]);
  }, [currentUser]);

  const getSessionsForApplication = React.useCallback(
    (applicationId: string) =>
      sessions
        .filter((s) => s.applicationId === applicationId)
        .sort((a, b) => b.completedAt - a.completedAt),
    [sessions]
  );

  const getSessionById = React.useCallback(
    (id: string) => sessions.find((s) => s.id === id),
    [sessions]
  );

  const saveSession = React.useCallback((session: MockInterviewSession) => {
    setSessions((prev) => {
      const idx = prev.findIndex((s) => s.id === session.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = session;
        return next;
      }
      return [...prev, session];
    });
  }, []);

  const deleteSession = React.useCallback((id: string) => {
    const session = sessions.find((s) => s.id === id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (session) {
      void apiRequest<void>(`/applications/${session.applicationId}/mock-interviews/${session.id}`, {
        method: "DELETE",
      });
    }
  }, [sessions]);

  const value = React.useMemo(
    () => ({
      sessions,
      getSessionsForApplication,
      getSessionById,
      saveSession,
      deleteSession,
    }),
    [sessions, getSessionsForApplication, getSessionById, saveSession, deleteSession]
  );

  return (
    <MockInterviewsContext.Provider value={value}>
      {children}
    </MockInterviewsContext.Provider>
  );
}

export function useMockInterviews() {
  const ctx = React.useContext(MockInterviewsContext);
  if (!ctx) {
    throw new Error("useMockInterviews must be used within MockInterviewsProvider");
  }
  return ctx;
}
