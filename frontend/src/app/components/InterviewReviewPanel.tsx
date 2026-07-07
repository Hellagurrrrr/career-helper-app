import React from "react";
import { Upload, Sparkles, Loader2, FileAudio } from "lucide-react";
import { Trans, useTranslation } from "react-i18next";
import { CoachingFeedbackResults } from "./CoachingFeedbackResults";
import {
  InterviewAnalysisStep,
  InterviewReview,
  InterviewReviewContext,
  runInterviewAnalysisDemo,
  useInterviewReviews,
  validateInterviewAudioFile,
} from "../lib/interview-reviews";

export function InterviewReviewPanel({
  context,
  showArchive = true,
}: {
  context: InterviewReviewContext;
  showArchive?: boolean;
}) {
  const { t } = useTranslation("coaching");
  const { getReviewsForApplication, saveReview, deleteReview } = useInterviewReviews();
  const archived = getReviewsForApplication(context.applicationId);

  const inputRef = React.useRef<HTMLInputElement>(null);
  const [step, setStep] = React.useState<InterviewAnalysisStep | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [activeReview, setActiveReview] = React.useState<InterviewReview | null>(null);

  const busy = step !== null && step !== "complete";

  const handleFile = async (file: File) => {
    const validationError = validateInterviewAudioFile(file);
    if (validationError) {
      setError(validationError === "not-audio" ? t("validate.notAudio") : t("validate.tooLarge"));
      return;
    }
    setError(null);
    setActiveReview(null);
    setStep("transcribing");

    try {
      const result = await runInterviewAnalysisDemo(file, context, setStep);
      saveReview(result);
      setActiveReview(result);
      setStep("complete");
      window.setTimeout(() => setStep(null), 400);
    } catch {
      setError(t("review.analysisFailed"));
      setStep(null);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-xs leading-relaxed text-slate-500">
        <Trans
          i18nKey="coaching:review.intro"
          values={{ jobTitle: context.jobTitle }}
          components={{ role: <span className="font-medium text-slate-700" /> }}
        />
      </p>

      <input
        ref={inputRef}
        type="file"
        accept="audio/mpeg,audio/mp3,audio/wav,audio/webm,audio/*,.mp3,.wav,.m4a"
        className="sr-only"
        disabled={busy}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
          e.target.value = "";
        }}
      />

      <button
        type="button"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-indigo-200 bg-indigo-50/50 px-3 py-2.5 text-sm font-medium text-indigo-900 transition-colors hover:border-indigo-300 hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
      >
        {busy ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            {step ? t(`steps.${step}`) : t("review.processing")}
          </>
        ) : (
          <>
            <Upload className="h-4 w-4" />
            {t("review.upload")}
          </>
        )}
      </button>

      {error && (
        <p className="text-xs font-medium text-red-700" role="alert">
          {error}
        </p>
      )}

      {activeReview && (
        <div className="rounded-xl border border-indigo-100 bg-white p-4">
          <div className="mb-3 flex items-center gap-2 text-sm text-slate-600">
            <Sparkles className="h-4 w-4 text-indigo-600" />
            <span className="font-medium text-slate-800">{t("review.latestAnalysis")}</span>
          </div>
          <CoachingFeedbackResults
            title={activeReview.fileName}
            subtitle={
              activeReview.durationSec != null
                ? t("results.durationSubtitle", {
                    minutes: Math.round(activeReview.durationSec / 60),
                    date: new Date(activeReview.uploadedAt).toLocaleString(),
                  })
                : new Date(activeReview.uploadedAt).toLocaleString()
            }
            overallSummary={activeReview.overallSummary}
            dimensions={activeReview.dimensions}
            improvementAdvice={activeReview.improvementAdvice}
            transcript={activeReview.transcript}
          />
        </div>
      )}

      {showArchive && archived.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t("review.archived", { count: archived.length })}
          </h4>
          {archived.map((review) => (
            <details
              key={review.id}
              className="group rounded-xl border border-slate-200 bg-slate-50/50 p-3"
              open={activeReview?.id === review.id}
            >
              <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-medium text-slate-800">
                <FileAudio className="h-4 w-4 shrink-0 text-blue-600" />
                <span className="min-w-0 flex-1 truncate">{review.fileName}</span>
                <span className="shrink-0 text-xs text-slate-500">
                  {new Date(review.uploadedAt).toLocaleDateString()}
                </span>
              </summary>
              <div className="mt-3 border-t border-slate-200 pt-3">
                <CoachingFeedbackResults
                  overallSummary={review.overallSummary}
                  dimensions={review.dimensions}
                  improvementAdvice={review.improvementAdvice}
                  transcript={review.transcript}
                  onDelete={() => {
                    deleteReview(review.id);
                    if (activeReview?.id === review.id) setActiveReview(null);
                  }}
                />
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
