import React from "react";
import { Sparkles, ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { InterviewDimensionScore } from "../lib/interview-reviews";

function scoreTone(score: number): string {
  if (score >= 8) return "text-green-700 ring-green-200 bg-green-50";
  if (score >= 7) return "text-blue-800 ring-blue-200 bg-blue-50";
  if (score >= 6) return "text-amber-800 ring-amber-200 bg-amber-50";
  return "text-slate-700 ring-slate-200 bg-slate-50";
}

function ScoreCard({
  label,
  score,
  narrative,
}: {
  label: string;
  score: number;
  narrative: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-slate-900">{label}</h4>
        <span
          className={`inline-flex h-10 min-w-[3rem] items-center justify-center rounded-lg px-2 text-lg font-bold tabular-nums ring-1 ${scoreTone(score)}`}
        >
          {score.toFixed(1)}
        </span>
      </div>
      <p className="text-sm leading-relaxed text-slate-600">{narrative}</p>
    </div>
  );
}

export function CoachingFeedbackResults({
  title,
  subtitle,
  overallSummary,
  dimensions,
  improvementAdvice,
  transcript,
  onDelete,
  deleteLabel,
}: {
  title?: string;
  subtitle?: string;
  overallSummary: string;
  dimensions: InterviewDimensionScore[];
  improvementAdvice: string;
  transcript: string;
  onDelete?: () => void;
  deleteLabel?: string;
}) {
  const { t } = useTranslation("coaching");
  const [showTranscript, setShowTranscript] = React.useState(false);
  const avg =
    dimensions.length > 0
      ? Math.round(
          (dimensions.reduce((s, d) => s + d.score, 0) / dimensions.length) * 10
        ) / 10
      : 0;

  return (
    <div className="space-y-4">
      {(title || subtitle || onDelete) && (
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            {title && (
              <p className="text-sm font-semibold text-slate-900">{title}</p>
            )}
            {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
          </div>
          {onDelete && (
            <button
              type="button"
              onClick={onDelete}
              className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-slate-500 transition-colors hover:bg-red-50 hover:text-red-700"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {deleteLabel ?? t("results.delete")}
            </button>
          )}
        </div>
      )}

      <div className="rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50 to-indigo-50/50 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-800">
          {t("results.overallScore")}
        </p>
        <p className="mt-1 text-3xl font-bold tracking-tight text-slate-950">{avg}</p>
        <p className="text-xs text-slate-500">
          {t("results.average", { count: dimensions.length })}
        </p>
      </div>

      <div>
        <h4 className="mb-2 text-sm font-semibold text-slate-900">{t("results.sessionSummary")}</h4>
        <p className="text-sm leading-relaxed text-slate-700">{overallSummary}</p>
      </div>

      <div>
        <h4 className="mb-3 text-sm font-semibold text-slate-900">{t("results.dimensionScores")}</h4>
        <div className="grid gap-3 sm:grid-cols-2">
          {dimensions.map((d) => (
            <ScoreCard key={d.id} label={d.label} score={d.score} narrative={d.narrative} />
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4">
        <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-900">
          <Sparkles className="h-4 w-4 text-indigo-600" />
          {t("results.improvementAdvice")}
        </h4>
        <p className="text-sm leading-relaxed text-slate-700">{improvementAdvice}</p>
      </div>

      {transcript && (
        <div>
          <button
            type="button"
            onClick={() => setShowTranscript((v) => !v)}
            className="inline-flex items-center gap-1 text-sm font-medium text-blue-700 hover:underline"
          >
            {showTranscript ? (
              <>
                <ChevronUp className="h-4 w-4" />
                {t("results.hideTranscript")}
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4" />
                {t("results.viewTranscript")}
              </>
            )}
          </button>
          {showTranscript && (
            <pre className="mt-2 max-h-48 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed whitespace-pre-wrap text-slate-700">
              {transcript}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
