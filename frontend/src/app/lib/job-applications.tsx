import React from "react";
import { apiRequest } from "./api";
import { useAuth } from "./auth";
import { JOBS_BY_GOAL } from "./jobs";

export type ManualApplicationStatus =
  | "applied"
  | "screening"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";

export const MANUAL_STATUS_LABELS: Record<ManualApplicationStatus, string> = {
  applied: "Applied",
  screening: "Screening / review",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export type PartnerPipelineCode =
  | "referral_sent"
  | "under_review"
  | "interview"
  | "final_round"
  | "offer_extended";

export const PARTNER_STATUS_LABELS: Record<PartnerPipelineCode, string> = {
  referral_sent: "Referral sent",
  under_review: "Under review",
  interview: "Interview",
  final_round: "Final round",
  offer_extended: "Offer extended",
};

export type JobApplication = {
  id: string;
  kind: "partner" | "standard";
  goalId: string;
  jobId: string;
  jobIndex?: number;
  title: string;
  company: string;
  submittedAt: number;
  partnerStatus?: PartnerPipelineCode | null;
  manualStatus?: ManualApplicationStatus | null;
  reviewCount?: number;
  mockCount?: number;
};

type ApplicationListResponse = {
  items: JobApplication[];
  summary: {
    total: number;
    partner: number;
    selfTracked: number;
    inProgress: number;
    offers: number;
  };
};

function withJobIndex(app: JobApplication): JobApplication {
  const jobs = JOBS_BY_GOAL[app.goalId]?.jobs ?? [];
  const jobIndex = jobs.findIndex((job) => job.id === app.jobId);
  return { ...app, jobIndex: jobIndex >= 0 ? jobIndex : app.jobIndex };
}

export function getPartnerPipelineStage(submittedAt: number): PartnerPipelineCode {
  void submittedAt;
  return "referral_sent";
}

export function isTerminalManualStatus(s: ManualApplicationStatus): boolean {
  return s === "rejected" || s === "withdrawn";
}

type JobApplicationsContextValue = {
  applications: JobApplication[];
  loading: boolean;
  refreshApplications: () => Promise<void>;
  getApplicationsForGoal: (goalId: string) => JobApplication[];
  isJobApplied: (goalId: string, jobIndexOrId: number | string) => boolean;
  applyToJob: (input: {
    goalId: string;
    jobIndex?: number;
    jobId?: string;
    title: string;
    company: string;
    isPartner: boolean;
    cvText?: string;
  }) => Promise<void>;
  removeApplicationForJob: (goalId: string, jobIndexOrId: number | string) => Promise<void>;
  setManualStatus: (applicationId: string, status: ManualApplicationStatus) => Promise<void>;
};

const JobApplicationsContext = React.createContext<JobApplicationsContextValue | null>(null);

export function JobApplicationsProvider({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth();
  const [applications, setApplications] = React.useState<JobApplication[]>([]);
  const [loading, setLoading] = React.useState(false);

  const refreshApplications = React.useCallback(async () => {
    if (!currentUser) {
      setApplications([]);
      return;
    }
    setLoading(true);
    try {
      const response = await apiRequest<ApplicationListResponse>("/applications");
      setApplications(response.items.map(withJobIndex));
    } finally {
      setLoading(false);
    }
  }, [currentUser]);

  React.useEffect(() => {
    void refreshApplications();
  }, [refreshApplications]);

  const getApplicationsForGoal = React.useCallback(
    (goalId: string) => applications.filter((a) => a.goalId === goalId),
    [applications]
  );

  const resolveJobId = React.useCallback((goalId: string, jobIndexOrId: number | string) => {
    if (typeof jobIndexOrId === "string") return jobIndexOrId;
    return JOBS_BY_GOAL[goalId]?.jobs[jobIndexOrId]?.id;
  }, []);

  const isJobApplied = React.useCallback(
    (goalId: string, jobIndexOrId: number | string) => {
      const jobId = resolveJobId(goalId, jobIndexOrId);
      return applications.some((a) => a.goalId === goalId && a.jobId === jobId);
    },
    [applications, resolveJobId]
  );

  const applyToJob = React.useCallback<JobApplicationsContextValue["applyToJob"]>(
    async (input) => {
      const jobId = input.jobId ?? (input.jobIndex != null ? JOBS_BY_GOAL[input.goalId]?.jobs[input.jobIndex]?.id : undefined);
      if (!jobId) return;
      const created = await apiRequest<JobApplication>("/applications", {
        method: "POST",
        body: {
          kind: input.isPartner ? "partner" : "standard",
          goalId: input.goalId,
          jobId,
          cvText: input.cvText,
        },
      });
      setApplications((prev) => [...prev.filter((a) => a.id !== created.id), withJobIndex(created)]);
    },
    []
  );

  const removeApplicationForJob = React.useCallback<JobApplicationsContextValue["removeApplicationForJob"]>(
    async (goalId, jobIndexOrId) => {
      const jobId = resolveJobId(goalId, jobIndexOrId);
      const existing = applications.find((a) => a.goalId === goalId && a.jobId === jobId);
      if (!existing) return;
      await apiRequest<void>(`/applications/${existing.id}`, { method: "DELETE" });
      setApplications((prev) => prev.filter((a) => a.id !== existing.id));
    },
    [applications, resolveJobId]
  );

  const setManualStatus = React.useCallback(async (applicationId: string, status: ManualApplicationStatus) => {
    const updated = await apiRequest<JobApplication>(`/applications/${applicationId}`, {
      method: "PATCH",
      body: { manualStatus: status },
    });
    setApplications((prev) => prev.map((a) => (a.id === applicationId ? withJobIndex(updated) : a)));
  }, []);

  const value = React.useMemo(
    () => ({
      applications,
      loading,
      refreshApplications,
      getApplicationsForGoal,
      isJobApplied,
      applyToJob,
      removeApplicationForJob,
      setManualStatus,
    }),
    [applications, loading, refreshApplications, getApplicationsForGoal, isJobApplied, applyToJob, removeApplicationForJob, setManualStatus]
  );

  return <JobApplicationsContext.Provider value={value}>{children}</JobApplicationsContext.Provider>;
}

export function useJobApplications() {
  const ctx = React.useContext(JobApplicationsContext);
  if (!ctx) {
    throw new Error("useJobApplications must be used within JobApplicationsProvider");
  }
  return ctx;
}
