import React from "react";
import { apiRequest } from "./api";
import { useAuth } from "./auth";

const MAX_FILE_BYTES = 25 * 1024 * 1024;

export type InterviewAnalysisStep =
  | "transcribing"
  | "summarizing"
  | "scoring"
  | "recommendations"
  | "complete";

export type InterviewDimensionScore = {
  id: string;
  label: string;
  score: number;
  narrative: string;
};

export type InterviewReview = {
  id: string;
  applicationId: string;
  fileName: string;
  uploadedAt: number;
  durationSec: number | null;
  transcript: string;
  overallSummary: string;
  dimensions: InterviewDimensionScore[];
  improvementAdvice: string;
};

export type InterviewReviewContext = {
  applicationId: string;
  jobTitle: string;
  company: string;
  goalTitle?: string;
  skills: string[];
};

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function getAudioDurationSec(file: File): Promise<number | null> {
  if (typeof window === "undefined") return null;
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    audio.preload = "metadata";
    audio.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(Number.isFinite(audio.duration) ? audio.duration : null);
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(null);
    };
    audio.src = url;
  });
}

export type AudioValidationError = "not-audio" | "too-large";

export function validateInterviewAudioFile(file: File): AudioValidationError | null {
  const type = file.type.toLowerCase();
  const name = file.name.toLowerCase();
  const audioLike =
    type.startsWith("audio/") ||
    name.endsWith(".mp3") ||
    name.endsWith(".wav") ||
    name.endsWith(".m4a") ||
    name.endsWith(".webm");
  if (!audioLike) return "not-audio";
  if (file.size > MAX_FILE_BYTES) return "too-large";
  return null;
}

export async function runInterviewAnalysisDemo(
  file: File,
  ctx: InterviewReviewContext,
  onStep: (step: InterviewAnalysisStep) => void
): Promise<InterviewReview> {
  onStep("transcribing");
  const form = new FormData();
  form.append("file", file);
  const created = await apiRequest<{ id: string; applicationId: string; status: InterviewAnalysisStep }>(
    `/applications/${ctx.applicationId}/interview-reviews`,
    { method: "POST", body: form }
  );

  for (let i = 0; i < 24; i++) {
    await delay(700);
    const status = await apiRequest<{
      id: string;
      applicationId: string;
      status: InterviewAnalysisStep;
      review?: InterviewReview;
    }>(`/applications/${ctx.applicationId}/interview-reviews/${created.id}`);
    onStep(status.status);
    if (status.status === "complete" && status.review) return status.review;
  }
  throw new Error("Analysis timed out.");
}

type InterviewReviewsContextValue = {
  reviews: InterviewReview[];
  getReviewsForApplication: (applicationId: string) => InterviewReview[];
  getReviewById: (id: string) => InterviewReview | undefined;
  saveReview: (review: InterviewReview) => void;
  deleteReview: (id: string) => void;
};

const InterviewReviewsContext = React.createContext<InterviewReviewsContextValue | null>(null);

export function InterviewReviewsProvider({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth();
  const [reviews, setReviews] = React.useState<InterviewReview[]>([]);

  React.useEffect(() => {
    if (!currentUser) setReviews([]);
  }, [currentUser]);

  const getReviewsForApplication = React.useCallback(
    (applicationId: string) =>
      reviews.filter((r) => r.applicationId === applicationId).sort((a, b) => b.uploadedAt - a.uploadedAt),
    [reviews]
  );

  const getReviewById = React.useCallback((id: string) => reviews.find((r) => r.id === id), [reviews]);

  const saveReview = React.useCallback((review: InterviewReview) => {
    setReviews((prev) => {
      const idx = prev.findIndex((r) => r.id === review.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = review;
        return next;
      }
      return [review, ...prev];
    });
  }, []);

  const deleteReview = React.useCallback(
    (id: string) => {
      const review = reviews.find((r) => r.id === id);
      setReviews((prev) => prev.filter((r) => r.id !== id));
      if (review) {
        void apiRequest<void>(`/applications/${review.applicationId}/interview-reviews/${review.id}`, {
          method: "DELETE",
        });
      }
    },
    [reviews]
  );

  const value = React.useMemo(
    () => ({ reviews, getReviewsForApplication, getReviewById, saveReview, deleteReview }),
    [reviews, getReviewsForApplication, getReviewById, saveReview, deleteReview]
  );

  return <InterviewReviewsContext.Provider value={value}>{children}</InterviewReviewsContext.Provider>;
}

export function useInterviewReviews() {
  const ctx = React.useContext(InterviewReviewsContext);
  if (!ctx) {
    throw new Error("useInterviewReviews must be used within InterviewReviewsProvider");
  }
  return ctx;
}

export const ANALYSIS_STEP_LABELS: Record<InterviewAnalysisStep, string> = {
  transcribing: "Transcribing your recording...",
  summarizing: "Summarizing the conversation...",
  scoring: "Scoring interview dimensions...",
  recommendations: "Drafting improvement advice...",
  complete: "Analysis complete",
};
