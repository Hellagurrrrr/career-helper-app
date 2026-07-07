import React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { useProfile } from "../lib/profile";
import { getJobApplicationUrl, type JobListing } from "../lib/jobs";
import {
  buildTailoredCvText,
  downloadCvAsPng,
  downloadCvAsWord,
  openCvPrintPreview,
} from "../lib/tailored-cv";
import { ExternalLink, FileImage, FileText, Printer, Sparkles } from "lucide-react";
import { Trans, useTranslation } from "react-i18next";

type JobApplyCvDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  goalTitle: string;
  job: JobListing | null;
  isPartner: boolean;
  onSubmitApplication: () => void;
};

export function JobApplyCvDialog({
  open,
  onOpenChange,
  goalTitle,
  job,
  isPartner,
  onSubmitApplication,
}: JobApplyCvDialogProps) {
  const { t } = useTranslation("jobs");
  const { profile } = useProfile();
  const [cvText, setCvText] = React.useState("");
  const [reviewed, setReviewed] = React.useState(false);

  const active = open && job !== null;

  React.useEffect(() => {
    if (active && job) {
      setCvText(buildTailoredCvText(profile, job, goalTitle));
      setReviewed(false);
    }
  }, [active, job, profile, goalTitle]);

  React.useEffect(() => {
    if (!open) setReviewed(false);
  }, [open]);

  const fileBase = job ? `${job.company}-${job.title}` : "";
  const applicationUrl = job && !isPartner ? getJobApplicationUrl(job) : null;

  const handlePartnerSubmit = () => {
    if (!reviewed || !job) return;
    onSubmitApplication();
    onOpenChange(false);
  };

  return (
    <Dialog open={active} onOpenChange={onOpenChange}>
      {job ? (
        <DialogContent className="flex max-h-[92vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
        <div className="min-h-0 flex-1 overflow-y-auto p-6">
          <DialogHeader>
            <DialogTitle className="pr-8 text-left text-slate-950">
              {isPartner ? t("apply.titlePartner") : t("apply.titleStandard")}
            </DialogTitle>
            <DialogDescription className="text-left text-slate-600">
              <Trans
                i18nKey={isPartner ? "jobs:apply.descPartner" : "jobs:apply.descStandard"}
                values={{ title: job.title, company: job.company }}
                components={{ b: <span className="font-medium text-slate-800" /> }}
              />
            </DialogDescription>
          </DialogHeader>

          {applicationUrl && (
            <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                {t("apply.companyApplication")}
              </p>
              <p className="mt-1 text-sm leading-relaxed text-slate-700">
                <Trans
                  i18nKey="jobs:apply.companyApplicationBody"
                  values={{ company: job.company }}
                  components={{ b: <span className="font-medium text-slate-900" /> }}
                />
              </p>
              <a
                href={applicationUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-emerald-900 shadow-sm ring-1 ring-emerald-200 transition-colors hover:bg-emerald-50"
              >
                <ExternalLink className="h-4 w-4 shrink-0" />
                {t("apply.openApplicationPage")}
              </a>
              <p className="mt-2 break-all text-xs text-slate-500">{applicationUrl}</p>
            </div>
          )}

          <label htmlFor="tailored-cv-editor" className="mt-4 block text-sm font-medium text-slate-700">
            {t("apply.cvContent")}
          </label>
          <textarea
            id="tailored-cv-editor"
            value={cvText}
            onChange={(e) => setCvText(e.target.value)}
            spellCheck
            className="mt-2 min-h-72 max-h-[45vh] w-full resize-y rounded-xl border border-slate-200 bg-slate-50/80 p-3 font-mono text-sm leading-relaxed text-slate-900 shadow-inner focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            aria-describedby="cv-editor-hint"
          />
          <p id="cv-editor-hint" className="mt-2 text-xs text-slate-500">
            {t("apply.tip")}
          </p>

          {!isPartner && (
            <div className="mt-4 border-t border-slate-200 pt-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t("apply.exportTitle")}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    openCvPrintPreview(
                      t("apply.printTitle", { title: job.title, company: job.company }),
                      cvText,
                    )
                  }
                >
                  <Printer className="h-4 w-4" />
                  {t("apply.pdfPrint")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => downloadCvAsWord(cvText, fileBase)}
                >
                  <FileText className="h-4 w-4" />
                  {t("apply.word")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => downloadCvAsPng(cvText, fileBase)}
                >
                  <FileImage className="h-4 w-4" />
                  {t("apply.png")}
                </Button>
              </div>
            </div>
          )}

          {isPartner && (
            <label className="mt-4 flex cursor-pointer items-start gap-3 rounded-xl border border-blue-100 bg-blue-50/60 px-3 py-3 text-sm text-slate-800">
              <input
                type="checkbox"
                checked={reviewed}
                onChange={(e) => setReviewed(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span>{t("apply.reviewConfirm")}</span>
            </label>
          )}
        </div>

        <DialogFooter className="shrink-0 gap-3 border-t border-slate-100 bg-slate-50/90 p-4 sm:flex-row sm:items-center sm:justify-between sm:[&>div]:flex-nowrap">
          {isPartner ? (
            <>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {t("apply.cancel")}
              </Button>
              <Button
                type="button"
                disabled={!reviewed}
                className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:brightness-110"
                onClick={handlePartnerSubmit}
              >
                <Sparkles className="h-4 w-4" />
                {t("apply.submitReferral")}
              </Button>
            </>
          ) : (
            <>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {t("apply.cancel")}
              </Button>
              <Button
                type="button"
                onClick={() => {
                  onSubmitApplication();
                  onOpenChange(false);
                }}
              >
                {t("apply.saveToTracker")}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
      ) : null}
    </Dialog>
  );
}
