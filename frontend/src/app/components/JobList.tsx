import React from "react";
import {
  Briefcase,
  MapPin,
  DollarSign,
  TrendingUp,
  CheckCircle2,
  Bookmark,
  BookmarkCheck,
  Sparkles,
  ShieldCheck,
  Handshake,
  Lock,
  ArrowRight,
  Clock,
} from "lucide-react";
import { Trans, useTranslation } from "react-i18next";
import { getJobDetailDescription, JobListing, listJobsForGoal } from "../lib/jobs";
import { apiRequest } from "../lib/api";
import { useGoals } from "../lib/goals";
import { useJobApplications } from "../lib/job-applications";
import { JobApplyCvDialog } from "./JobApplyCvDialog";
import { JobRoadmap } from "./JobRoadmap";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";

export function JobList({ goalId }: { goalId: string }) {
  const { t } = useTranslation("jobs");
  const effectiveGoalId = goalId;
  const { getGoal } = useGoals();
  const selectedGoal = getGoal(effectiveGoalId);
  const catalogGoalId = selectedGoal?.catalogId ?? effectiveGoalId;
  const [data, setData] = React.useState<{ title: string; jobs: JobListing[] }>({
    title: selectedGoal?.title ?? "Jobs",
    jobs: [],
  });
  const [savedJobIds, setSavedJobIds] = React.useState<Set<string>>(new Set());

  React.useEffect(() => {
    let cancelled = false;
    void listJobsForGoal(catalogGoalId, selectedGoal?.title).then((jobs) => {
      if (!cancelled) setData({ title: selectedGoal?.title ?? "Jobs", jobs });
    });
    void apiRequest<JobListing[]>(`/saved-jobs?goalId=${encodeURIComponent(effectiveGoalId)}`)
      .then((jobs) => {
        if (!cancelled) setSavedJobIds(new Set(jobs.map((job) => job.id)));
      })
      .catch(() => {
        if (!cancelled) setSavedJobIds(new Set());
      });
    return () => {
      cancelled = true;
    };
  }, [effectiveGoalId, catalogGoalId, selectedGoal?.title]);

  const savedJobEntries = React.useMemo(
    () =>
      data.jobs
        .map((job, index) => ({ index, job }))
        .filter(({ job }) => savedJobIds.has(job.id)),
    [savedJobIds, data.jobs]
  );

  const scrollToJobCard = React.useCallback(
    (index: number) => {
      document
        .getElementById(`job-card-${effectiveGoalId}-${index}`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    },
    [effectiveGoalId]
  );

  const { isJobApplied, applyToJob, removeApplicationForJob, getApplicationsForGoal } =
    useJobApplications();
  const applicationsForGoal = React.useMemo(
    () => getApplicationsForGoal(effectiveGoalId),
    [getApplicationsForGoal, effectiveGoalId]
  );
  const appliedCount = applicationsForGoal.length;

  const [applyCvIndex, setApplyCvIndex] = React.useState<number | null>(null);
  const [detailJobIndex, setDetailJobIndex] = React.useState<number | null>(null);

  const openApplyCvFlow = (index: number) => {
    const job = data.jobs[index];
    if (!job) return;
    if (isJobApplied(effectiveGoalId, job.id)) {
      void removeApplicationForJob(effectiveGoalId, job.id);
      return;
    }
    setApplyCvIndex(index);
  };

  const completeApplicationFromDialog = () => {
    if (applyCvIndex === null) return;
    const job = data.jobs[applyCvIndex];
    if (!job) return;
    applyToJob({
      goalId: effectiveGoalId,
      jobIndex: applyCvIndex,
      jobId: job.id,
      title: job.title,
      company: job.company,
      isPartner: Boolean(job.partner),
    });
    setApplyCvIndex(null);
  };

  React.useEffect(() => {
    setApplyCvIndex(null);
    setDetailJobIndex(null);
  }, [effectiveGoalId]);

  const toggleSaved = (index: number) => {
    const job = data.jobs[index];
    if (!job) return;
    const isSaved = savedJobIds.has(job.id);
    setSavedJobIds((prev) => {
      const next = new Set(prev);
      if (isSaved) next.delete(job.id);
      else next.add(job.id);
      return next;
    });
    if (isSaved) {
      void apiRequest<void>(`/saved-jobs/${job.id}?goalId=${encodeURIComponent(effectiveGoalId)}`, {
        method: "DELETE",
      });
    } else {
      void apiRequest<JobListing[]>(`/saved-jobs/${job.id}`, {
        method: "PUT",
        body: { goalId: effectiveGoalId },
      });
    }
  };

  const recommendedJobs = data.jobs;
  const indexedJobs = recommendedJobs.map((job, index) => ({ job, index }));
  const partnerJobs = indexedJobs.filter(({ job }) => job.partner);
  const regularJobs = indexedJobs.filter(({ job }) => !job.partner);
  const applyDraft = applyCvIndex !== null ? data.jobs[applyCvIndex] ?? null : null;
  const detailJob = detailJobIndex !== null ? data.jobs[detailJobIndex] ?? null : null;

  return (
    <div className="space-y-6">
      <section>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-200/70 bg-white px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{t("stats.saved")}</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-slate-950">{savedJobIds.size}</p>
          </div>
          <div className="rounded-xl border border-slate-200/70 bg-white px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{t("stats.applied")}</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-slate-950">{appliedCount}</p>
          </div>
          <div className="rounded-xl border border-slate-200/70 bg-white px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{t("stats.openRoles")}</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-slate-950">{recommendedJobs.length}</p>
          </div>
          <div className="rounded-xl border border-slate-200/70 bg-white px-4 py-3">
            <p className="flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-blue-600">
              <Sparkles className="h-3 w-3" />
              {t("stats.referral")}
            </p>
            <p className="mt-1 text-xl font-bold tracking-tight text-slate-950">{partnerJobs.length}</p>
          </div>
        </div>
      </section>

      <JobRoadmap />

      <section
        id="saved-jobs"
        className="rounded-xl border border-slate-200/70 bg-white p-5"
        aria-labelledby="saved-jobs-heading"
      >
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <BookmarkCheck className="h-5 w-5 shrink-0 text-blue-600" aria-hidden />
            <h2 id="saved-jobs-heading" className="text-lg font-semibold tracking-tight text-slate-950">
              {t("saved.title")}
            </h2>
            {savedJobEntries.length > 0 && (
              <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-800">
                {t("saved.forThisGoal", { count: savedJobEntries.length })}
              </span>
            )}
          </div>
        </div>
        {savedJobEntries.length === 0 ? (
          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            <Trans
              i18nKey="jobs:saved.emptyHint"
              components={{ strong: <span className="font-medium text-slate-800" /> }}
            />
          </p>
        ) : (
          <ul className="mt-4 space-y-2">
            {savedJobEntries.map(({ job, index }) => (
              <li
                key={`${effectiveGoalId}-${index}`}
                className="flex flex-col gap-3 rounded-xl border border-slate-200/70 bg-slate-50/60 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-slate-950">{job.title}</p>
                  <p className="text-sm text-slate-600">{job.company}</p>
                  {job.partner && (
                    <p className="mt-1 text-xs font-medium text-blue-700">{t("saved.partnerTrack")}</p>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                  <span className="text-sm font-semibold tabular-nums text-blue-700">
                    {t("matchPercent", { value: job.match ?? job.matchScore ?? "--" })}
                  </span>
                  <button
                    type="button"
                    onClick={() => scrollToJobCard(index)}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50"
                  >
                    {t("saved.showInList")}
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleSaved(index)}
                    className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-800 transition-colors hover:bg-blue-100"
                  >
                    {t("actions.unsave")}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {partnerJobs.length > 0 && (
        <section aria-labelledby="partner-roles-heading">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 via-indigo-500 to-blue-600 text-white">
              <Sparkles className="h-4 w-4" />
            </span>
            <h2 id="partner-roles-heading" className="text-lg font-semibold tracking-tight text-slate-950">
              {t("partner.title")}
            </h2>
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-800">
              <Handshake className="h-3 w-3" />
              {t("partner.referralTrack")}
            </span>
            <span className="ml-auto text-sm text-slate-500">
              {t("rolesCount", { count: partnerJobs.length })}
            </span>
          </div>

          <div className="mb-4 rounded-xl border border-slate-200/70 bg-slate-50 p-4">
            <div className="flex gap-3">
              <div className="hidden h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-white text-blue-600 ring-1 ring-slate-200 sm:flex">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div className="flex-1 space-y-1.5 text-sm text-slate-700">
                <p className="font-semibold text-slate-900">{t("partner.infoTitle")}</p>
                <p>
                  <Trans
                    i18nKey="jobs:partner.infoBody"
                    components={{ strong: <span className="font-medium text-blue-800" /> }}
                  />
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {partnerJobs.map(({ job, index }) => {
              const isSaved = savedJobIds.has(job.id);
              const isApplied = isJobApplied(effectiveGoalId, job.id);
              const companyInitial = job.company.charAt(0).toUpperCase();
              return (
                <div
                  key={index}
                  id={`job-card-${effectiveGoalId}-${index}`}
                  className="group relative overflow-hidden rounded-xl bg-gradient-to-br from-blue-500 via-indigo-500 to-blue-600 p-[1.5px] shadow-sm transition-shadow hover:shadow-md"
                >
                  <div className="absolute -right-12 -top-12 h-32 w-32 rounded-full bg-white/10 blur-2xl" aria-hidden="true" />
                  <div className="relative rounded-[14px] bg-white">
                    <div
                      role="button"
                      tabIndex={0}
                      aria-label={t("viewJobAria", { title: job.title, company: job.company })}
                      className="flex cursor-pointer flex-wrap items-center justify-between gap-2 rounded-t-[14px] bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-700 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white outline-none ring-white/30 transition-colors hover:brightness-110 focus-visible:ring-2"
                      onClick={() => setDetailJobIndex(index)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setDetailJobIndex(index);
                        }
                      }}
                    >
                      <span className="inline-flex items-center gap-1.5">
                        <Sparkles className="h-3.5 w-3.5" />
                        {t("partner.badge")}
                        <span className="opacity-60">·</span>
                        {t("partner.referralTrack")}
                      </span>
                      <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2 py-0.5 text-[10px] backdrop-blur">
                        <Lock className="h-3 w-3" />
                        {t("partner.exclusive")}
                      </span>
                    </div>

                    <div className="p-5">
                      <div
                        role="button"
                        tabIndex={0}
                        aria-label={t("viewJobAria", { title: job.title, company: job.company })}
                        className="-m-1 cursor-pointer rounded-xl p-1 text-left outline-none ring-blue-300/50 transition-colors hover:bg-slate-50/90 focus-visible:ring-2"
                        onClick={() => setDetailJobIndex(index)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            setDetailJobIndex(index);
                          }
                        }}
                      >
                        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                        <div className="flex min-w-0 flex-1 gap-3">
                          <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 text-lg font-bold text-white shadow-sm">
                            {companyInitial}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="text-lg font-semibold tracking-tight text-slate-950">
                                {job.title}
                              </h3>
                              {isApplied && (
                                <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-800">
                                  <CheckCircle2 className="h-3 w-3" />
                                  {t("actions.applied")}
                                </span>
                              )}
                            </div>
                            <div className="mt-0.5 flex flex-wrap items-center gap-2 text-sm">
                              <span className="font-medium text-slate-800">{job.company}</span>
                              <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-800 ring-1 ring-blue-200">
                                <ShieldCheck className="h-3 w-3" />
                                {t("partner.verified")}
                              </span>
                            </div>
                            {job.companyTagline && (
                              <p className="mt-1 text-sm italic text-slate-600">
                                "{job.companyTagline}"
                              </p>
                            )}

                            <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-600">
                              <span className="flex items-center gap-1">
                                <MapPin className="h-4 w-4" />
                                {job.location}
                              </span>
                              <span className="flex items-center gap-1">
                                <Briefcase className="h-4 w-4" />
                                {job.type}
                              </span>
                              <span className="flex items-center gap-1">
                                <DollarSign className="h-4 w-4" />
                                {job.salary}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-col gap-3 md:items-end">
                          <div className="flex items-baseline gap-2">
                            <span className="bg-gradient-to-r from-blue-700 to-indigo-700 bg-clip-text text-2xl font-bold tracking-tight text-transparent">
                              {job.match ?? job.matchScore ?? "--"}%
                            </span>
                            <span className="text-xs text-slate-500">{t("match")}</span>
                          </div>
                          <span className="text-xs text-slate-500">{job.posted}</span>
                        </div>
                      </div>
                      </div>

                      <div
                        className="mt-4 flex w-full flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-x-4 sm:gap-y-3"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="flex min-w-0 flex-1 flex-wrap gap-2">
                          {job.skills.map((skill) => (
                            <span
                              key={skill}
                              className="rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-800 ring-1 ring-blue-100"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                        <div className="flex w-full shrink-0 flex-row flex-wrap items-center justify-end gap-2 self-end sm:w-auto sm:self-auto">
                          <button
                            onClick={() => toggleSaved(index)}
                            className={`inline-flex items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition-colors ${
                              isSaved
                                ? "border-blue-200 bg-blue-50 text-blue-800 hover:bg-blue-100"
                                : "border-slate-200 text-slate-700 hover:bg-slate-50"
                            }`}
                            aria-pressed={isSaved}
                          >
                            {isSaved ? (
                              <>
                                <BookmarkCheck className="h-4 w-4" />
                                {t("actions.saved")}
                              </>
                            ) : (
                              <>
                                <Bookmark className="h-4 w-4" />
                                {t("actions.save")}
                              </>
                            )}
                          </button>
                          <button
                            onClick={() => openApplyCvFlow(index)}
                            className={`group/cta inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold shadow-sm transition-all ${
                              isApplied
                                ? "bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:brightness-110"
                                : "bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-700 text-white hover:brightness-110 hover:shadow-md"
                            }`}
                            aria-pressed={isApplied}
                          >
                            {isApplied ? (
                              <>
                                <CheckCircle2 className="h-4 w-4" />
                                {t("partner.referralSubmitted")}
                              </>
                            ) : (
                              <>
                                <Sparkles className="h-4 w-4" />
                                {t("partner.applyWithReferral")}
                                <ArrowRight className="h-4 w-4 transition-transform group-hover/cta:translate-x-0.5" />
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <div className="mb-4 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-blue-600" />
          <h2 className="text-lg font-semibold tracking-tight text-slate-950">
            {partnerJobs.length > 0 ? t("other.titleWithPartner") : t("other.titleDefault")}
          </h2>
          <span className="ml-auto text-sm text-slate-500">
            {t("rolesCount", { count: regularJobs.length })}
          </span>
        </div>
        <div className="space-y-3">
          {regularJobs.map(({ job, index }) => {
            const isSaved = savedJobIds.has(job.id);
            const isApplied = isJobApplied(effectiveGoalId, job.id);

            return (
              <div
                key={index}
                id={`job-card-${effectiveGoalId}-${index}`}
                className="rounded-xl border border-slate-200/70 bg-white p-5 transition-colors hover:border-slate-300 hover:bg-slate-50"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div
                    role="button"
                    tabIndex={0}
                    aria-label={t("viewJobAria", { title: job.title, company: job.company })}
                    className="min-w-0 flex-1 cursor-pointer rounded-xl p-1 text-left outline-none ring-blue-300/50 transition-colors hover:bg-slate-50 focus-visible:ring-2"
                    onClick={() => setDetailJobIndex(index)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setDetailJobIndex(index);
                      }
                    }}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold tracking-tight text-slate-950">
                        {job.title}
                      </h3>
                      {isApplied && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-800">
                          <CheckCircle2 className="h-3 w-3" />
                          {t("actions.applied")}
                        </span>
                      )}
                    </div>
                    <p className="mb-3 mt-1 text-slate-700">{job.company}</p>
                    <div className="mb-3 flex flex-wrap gap-3 text-sm text-slate-600">
                      <span className="flex items-center gap-1">
                        <MapPin className="h-4 w-4" />
                        {job.location}
                      </span>
                      <span className="flex items-center gap-1">
                        <Briefcase className="h-4 w-4" />
                        {job.type}
                      </span>
                      <span className="flex items-center gap-1">
                        <DollarSign className="h-4 w-4" />
                        {job.salary}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {job.skills.map((skill) => (
                        <span
                          key={skill}
                          className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div
                    className="flex flex-col gap-3 md:items-end"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-bold tracking-tight text-blue-700">
                        {job.match ?? job.matchScore ?? "--"}%
                      </span>
                      <span className="text-xs text-slate-500">{t("match")}</span>
                    </div>
                    <span className="text-xs text-slate-500">{job.posted}</span>
                    <div className="flex w-full flex-col gap-2 sm:flex-row md:w-auto">
                      <button
                        onClick={() => toggleSaved(index)}
                        className={`inline-flex w-full items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition-colors md:w-auto ${
                          isSaved
                            ? "border-blue-200 bg-blue-50 text-blue-800 hover:bg-blue-100"
                            : "border-slate-200 text-slate-700 hover:bg-slate-50"
                        }`}
                        aria-pressed={isSaved}
                      >
                        {isSaved ? (
                          <>
                            <BookmarkCheck className="h-4 w-4" />
                            {t("actions.saved")}
                          </>
                        ) : (
                          <>
                            <Bookmark className="h-4 w-4" />
                            {t("actions.save")}
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => openApplyCvFlow(index)}
                        className={`inline-flex w-full items-center justify-center rounded-xl px-4 py-2 text-sm font-medium transition-colors md:w-auto ${
                          isApplied
                            ? "bg-green-600 text-white hover:bg-green-700"
                            : "bg-blue-600 text-white hover:bg-blue-700"
                        }`}
                        aria-pressed={isApplied}
                      >
                        {isApplied ? t("actions.applied") : t("actions.applyNow")}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <JobApplyCvDialog
        open={applyDraft !== null}
        onOpenChange={(o) => {
          if (!o) setApplyCvIndex(null);
        }}
        goalTitle={data.title}
        job={applyDraft}
        isPartner={Boolean(applyDraft?.partner)}
        onSubmitApplication={completeApplicationFromDialog}
      />

      <Dialog
        open={detailJob !== null}
        onOpenChange={(open) => {
          if (!open) setDetailJobIndex(null);
        }}
      >
        <DialogContent className="max-h-[85vh] gap-0 overflow-y-auto p-0 sm:max-w-2xl">
          {detailJob && (
            <>
              <DialogHeader className="space-y-3 border-b border-slate-100 p-6 pb-4 text-left">
                <div className="flex flex-wrap items-center gap-2 pr-8">
                  <DialogTitle className="text-xl font-semibold tracking-tight text-slate-950">
                    {detailJob.title}
                  </DialogTitle>
                  {detailJob.partner && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-800 ring-1 ring-blue-200">
                      <Sparkles className="h-3 w-3" />
                      {t("partner.badge")}
                    </span>
                  )}
                </div>
                <DialogDescription asChild>
                  <div className="space-y-2 text-left text-slate-600">
                    <p className="text-base font-medium text-slate-800">{detailJob.company}</p>
                    {detailJob.companyTagline && (
                      <p className="text-sm italic text-slate-600">"{detailJob.companyTagline}"</p>
                    )}
                    <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
                      <span className="inline-flex items-center gap-1.5">
                        <MapPin className="h-4 w-4 shrink-0 text-slate-500" />
                        {detailJob.location}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <Briefcase className="h-4 w-4 shrink-0 text-slate-500" />
                        {detailJob.type}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <DollarSign className="h-4 w-4 shrink-0 text-slate-500" />
                        {detailJob.salary}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <TrendingUp className="h-4 w-4 shrink-0 text-slate-500" />
                        {t("matchPercent", { value: detailJob.match ?? detailJob.matchScore ?? "--" })}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <Clock className="h-4 w-4 shrink-0 text-slate-500" />
                        {detailJob.posted}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {detailJob.skills.map((skill) => (
                        <span
                          key={skill}
                          className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                </DialogDescription>
              </DialogHeader>
              <div className="p-6 pt-4">
                <p className="mb-2 text-sm font-semibold text-slate-900">{t("detail.description")}</p>
                <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                  {getJobDetailDescription(detailJob)}
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
