import { apiRequest } from "./api";

export type JobListing = {
  id: string;
  catalogGoalId: string;
  title: string;
  company: string;
  location: string;
  type: string;
  salary: string;
  match?: number;
  matchScore?: number;
  posted: string;
  skills: string[];
  partner?: boolean;
  exclusive?: boolean;
  companyTagline?: string | null;
  applicationUrl?: string | null;
  description?: string | null;
};

export type GoalJobBundle = {
  title: string;
  jobs: JobListing[];
};

export const JOBS_BY_GOAL: Record<string, GoalJobBundle> = {};

type JobListPage = {
  items: JobListing[];
  nextCursor: string | null;
  total: number;
};

function cacheJobs(goalId: string, jobs: JobListing[], title?: string) {
  JOBS_BY_GOAL[goalId] = { title: title ?? JOBS_BY_GOAL[goalId]?.title ?? "Jobs", jobs };
}

export async function listJobsForGoal(goalId: string, title?: string): Promise<JobListing[]> {
  const page = await apiRequest<JobListPage>(`/jobs?catalogGoalId=${encodeURIComponent(goalId)}&limit=100`);
  cacheJobs(goalId, page.items, title);
  return page.items;
}

export async function getJobDetail(jobId: string): Promise<JobListing> {
  const detail = await apiRequest<JobListing>(`/jobs/${jobId}`);
  const bundle = JOBS_BY_GOAL[detail.catalogGoalId];
  if (bundle) {
    const jobs = bundle.jobs.map((job) => (job.id === detail.id ? { ...job, ...detail, match: detail.matchScore } : job));
    cacheJobs(detail.catalogGoalId, jobs, bundle.title);
  }
  return { ...detail, match: detail.matchScore };
}

export function getJobApplicationUrl(job: JobListing): string {
  if (job.applicationUrl?.trim()) return job.applicationUrl.trim();
  const slug = job.company
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const roleSlug = job.title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `https://careers.${slug || "company"}.example/apply/${roleSlug || "role"}`;
}

export function getJobDetailDescription(job: JobListing): string {
  if (job.description?.trim()) return job.description.trim();
  const skillBlock = job.skills
    .map((s) => `- ${s}: show practical project, internship, or coursework evidence.`)
    .join("\n");
  const partnerNote = job.partner
    ? "This partner role can be submitted through AI Career Helper with a referral packet."
    : `Apply on the company careers site (${getJobApplicationUrl(job)}) after tailoring your CV.`;
  return [
    "About this role",
    "",
    `${job.company} is hiring for ${job.title} (${job.type}, ${job.location}). The highlighted compensation band is ${job.salary}.`,
    "",
    "Skills & experience",
    skillBlock,
    "",
    "Applying through this app",
    partnerNote,
  ].join("\n");
}

export function getJobsForGoal(goalId: string): GoalJobBundle | undefined {
  return JOBS_BY_GOAL[goalId];
}

export function countJobsForSkillKeywords(goalId: string, keywords: string[]): number {
  const bundle = JOBS_BY_GOAL[goalId];
  if (!bundle) return 0;
  const lowKeywords = keywords.map((k) => k.toLowerCase());
  return bundle.jobs.filter((job) =>
    job.skills.some((s) => {
      const low = s.toLowerCase();
      return lowKeywords.some((k) => low.includes(k) || k.includes(low));
    })
  ).length;
}

export function countPartnerJobs(goalId: string): number {
  return JOBS_BY_GOAL[goalId]?.jobs.filter((j) => j.partner).length ?? 0;
}
