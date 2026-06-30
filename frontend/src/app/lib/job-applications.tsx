import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "./api";
import { useAuth } from "./auth";
import { queryClient } from "./query-client";
import { JOBS_BY_GOAL } from "./jobs";

export const applicationsKey = ["applications"] as const;

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

function setAppsCache(updater: (prev: JobApplication[]) => JobApplication[]): void {
  queryClient.setQueryData<JobApplication[]>(applicationsKey, (prev) => updater(prev ?? []));
}

function resolveJobId(goalId: string, jobIndexOrId: number | string): string | undefined {
  if (typeof jobIndexOrId === "string") return jobIndexOrId;
  return JOBS_BY_GOAL[goalId]?.jobs[jobIndexOrId]?.id;
}

export function useJobApplications() {
  const { currentUser } = useAuth();

  const query = useQuery({
    queryKey: applicationsKey,
    queryFn: async () => {
      const response = await apiRequest<ApplicationListResponse>("/applications");
      return response.items.map(withJobIndex);
    },
    enabled: Boolean(currentUser),
  });
  const applications = query.data ?? [];

  return {
    applications,
    loading: query.isLoading,
    refreshApplications: async () => {
      await query.refetch();
    },
    getApplicationsForGoal: (goalId: string) => applications.filter((a) => a.goalId === goalId),
    isJobApplied: (goalId: string, jobIndexOrId: number | string) => {
      const jobId = resolveJobId(goalId, jobIndexOrId);
      return applications.some((a) => a.goalId === goalId && a.jobId === jobId);
    },
    applyToJob: async (input: {
      goalId: string;
      jobIndex?: number;
      jobId?: string;
      title: string;
      company: string;
      isPartner: boolean;
      cvText?: string;
    }) => {
      const jobId =
        input.jobId ?? (input.jobIndex != null ? JOBS_BY_GOAL[input.goalId]?.jobs[input.jobIndex]?.id : undefined);
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
      setAppsCache((prev) => [...prev.filter((a) => a.id !== created.id), withJobIndex(created)]);
    },
    removeApplicationForJob: async (goalId: string, jobIndexOrId: number | string) => {
      const jobId = resolveJobId(goalId, jobIndexOrId);
      const existing = applications.find((a) => a.goalId === goalId && a.jobId === jobId);
      if (!existing) return;
      await apiRequest<void>(`/applications/${existing.id}`, { method: "DELETE" });
      setAppsCache((prev) => prev.filter((a) => a.id !== existing.id));
    },
    setManualStatus: async (applicationId: string, status: ManualApplicationStatus) => {
      const updated = await apiRequest<JobApplication>(`/applications/${applicationId}`, {
        method: "PATCH",
        body: { manualStatus: status },
      });
      setAppsCache((prev) => prev.map((a) => (a.id === applicationId ? withJobIndex(updated) : a)));
    },
  };
}
