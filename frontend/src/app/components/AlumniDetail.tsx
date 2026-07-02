import React from "react";
import { Link, useNavigate, useParams } from "react-router";
import {
  ArrowLeft,
  Building2,
  GraduationCap,
  ChevronRight,
  Briefcase,
  Clock,
  Shield,
  Send,
  Plus,
  X,
  CheckCircle2,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import {
  AlumniProfile,
  formatRelativeDate,
  getAlumni,
  useMeetings,
} from "../lib/alumni";
import { useNotifications } from "../lib/notifications";

export function AlumniDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const alumni = id ? getAlumni(id) : undefined;
  const { getRequestForAlumni, withdrawRequest } = useMeetings();

  if (!alumni) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
        <h2 className="text-lg font-semibold text-slate-950">Profile not found</h2>
        <p className="mt-2 text-sm text-slate-600">
          This alumnus may have paused chat requests. Browse the directory for
          others.
        </p>
        <Link
          to="/alumni"
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          Back to network
        </Link>
      </div>
    );
  }

  const existing = getRequestForAlumni(alumni.id);

  return (
    <div className="space-y-6">
      <nav aria-label="breadcrumb">
        <ol className="flex flex-wrap items-center gap-1.5 text-sm text-slate-500">
          <li>
            <Link
              to="/"
              className="rounded-md px-1 transition-colors hover:bg-slate-100 hover:text-slate-900"
            >
              Dashboard
            </Link>
          </li>
          <li aria-hidden="true">
            <ChevronRight className="h-4 w-4 text-slate-400" />
          </li>
          <li>
            <Link
              to="/alumni"
              className="rounded-md px-1 transition-colors hover:bg-slate-100 hover:text-slate-900"
            >
              Alumni network
            </Link>
          </li>
          <li aria-hidden="true">
            <ChevronRight className="h-4 w-4 text-slate-400" />
          </li>
          <li className="font-medium text-slate-950">
            {alumni.firstName} {alumni.lastInitial}
          </li>
        </ol>
      </nav>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div
          className={`h-24 bg-gradient-to-br ${alumni.avatarGradient}`}
          aria-hidden="true"
        />
        <div className="px-6 pb-6">
          <div className="-mt-10 flex flex-wrap items-end gap-4">
            <div
              className={`flex h-20 w-20 flex-shrink-0 items-center justify-center rounded-xl border-4 border-white bg-gradient-to-br ${alumni.avatarGradient} text-2xl font-bold text-white shadow-sm`}
              aria-hidden="true"
            >
              {alumni.firstName[0]}
            </div>
            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-slate-950">
                  {alumni.firstName} {alumni.lastInitial}
                </h1>
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                  <Shield className="h-3 w-3" />
                  Privacy protected
                </span>
                <a
                  href={alumni.linkedinUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-[#0A66C2]/35 bg-sky-50 px-3 py-1.5 text-xs font-semibold text-[#0A66C2] shadow-sm transition-colors hover:bg-sky-100"
                  aria-label={`View ${alumni.firstName}'s LinkedIn profile (opens in a new tab)`}
                >
                  <ExternalLink className="h-4 w-4 shrink-0" aria-hidden />
                  LinkedIn
                </a>
              </div>
              <p className="mt-1 text-base font-medium text-slate-700">
                {alumni.role} · {alumni.company}
              </p>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
                <span className="inline-flex items-center gap-1.5">
                  <Building2 className="h-4 w-4" />
                  {alumni.industry}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <GraduationCap className="h-4 w-4" />
                  {alumni.major}, Class of {alumni.graduationYear}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Briefcase className="h-4 w-4" />
                  {alumni.yearsExperience} yrs experience
                </span>
              </div>
            </div>
          </div>

          <p className="mt-5 text-sm leading-relaxed text-slate-700">
            {alumni.bio}
          </p>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="flex items-center gap-2 text-base font-semibold tracking-tight text-slate-950">
              <Sparkles className="h-4 w-4 text-blue-700" />
              Open to chat about
            </h2>
            <ul className="mt-3 space-y-2">
              {alumni.topics.map((topic) => (
                <li
                  key={topic}
                  className="flex items-start gap-2.5 rounded-xl bg-blue-50/50 px-3 py-2.5 text-sm text-slate-800"
                >
                  <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-700" />
                  {topic}
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold tracking-tight text-slate-950">
              Expertise
            </h2>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {alumni.expertise.map((tag) => (
                <span
                  key={tag}
                  className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
                >
                  {tag}
                </span>
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-4">
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Availability
            </h3>
            <p className="mt-2 flex items-center gap-2 text-sm text-slate-800">
              <Clock className="h-4 w-4 text-slate-500" />
              {alumni.responseTime}
            </p>
            <p className="mt-1 text-sm text-slate-600">{alumni.availability}</p>
          </section>

          {existing ? (
            <RequestSentCard
              alumni={alumni}
              onWithdraw={() => withdrawRequest(existing.id)}
              submittedAt={existing.submittedAt}
              topic={existing.topic}
            />
          ) : (
            <RequestChatForm
              alumni={alumni}
              onSubmitted={() => navigate("/alumni?tab=requests")}
            />
          )}

          <section className="rounded-xl border border-blue-100 bg-blue-50/60 p-4 text-sm text-blue-900">
            <p className="flex items-center gap-1.5 font-semibold">
              <Shield className="h-4 w-4" />
              How introductions work
            </p>
            <p className="mt-1 text-blue-800">
              When {alumni.firstName} accepts, we share contact details with
              both of you privately. Your email stays hidden until then.
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
}

function RequestSentCard({
  alumni,
  onWithdraw,
  submittedAt,
  topic,
}: {
  alumni: AlumniProfile;
  onWithdraw: () => void;
  submittedAt: number;
  topic: string;
}) {
  return (
    <section className="rounded-xl border border-amber-200 bg-amber-50/70 p-5">
      <div className="flex items-center gap-2 text-sm font-semibold text-amber-900">
        <Clock className="h-4 w-4" />
        Request sent
      </div>
      <p className="mt-2 text-sm text-amber-900">
        We're waiting for {alumni.firstName}'s response. {alumni.responseTime}.
      </p>
      <dl className="mt-3 space-y-1 text-xs text-amber-900">
        <div>
          <dt className="inline font-semibold">Topic: </dt>
          <dd className="inline">{topic}</dd>
        </div>
        <div>
          <dt className="inline font-semibold">Sent: </dt>
          <dd className="inline">{formatRelativeDate(submittedAt)}</dd>
        </div>
      </dl>
      <button
        onClick={onWithdraw}
        className="mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-xl border border-amber-300 bg-white px-3 py-2 text-sm font-medium text-amber-900 transition-colors hover:bg-amber-50"
      >
        <X className="h-4 w-4" />
        Withdraw request
      </button>
    </section>
  );
}

function RequestChatForm({
  alumni,
  onSubmitted,
}: {
  alumni: AlumniProfile;
  onSubmitted: () => void;
}) {
  const { requestChat } = useMeetings();
  const { notify } = useNotifications();

  const [topic, setTopic] = React.useState<string>(alumni.topics[0] ?? "");
  const [message, setMessage] = React.useState<string>("");
  const [timeDraft, setTimeDraft] = React.useState<string>("");
  const [times, setTimes] = React.useState<string[]>([]);

  const canSubmit = topic.trim().length > 0 && message.trim().length >= 20;

  const addTime = () => {
    const v = timeDraft.trim();
    if (!v) return;
    setTimes((prev) => Array.from(new Set([...prev, v])));
    setTimeDraft("");
  };

  const removeTime = (v: string) => {
    setTimes((prev) => prev.filter((t) => t !== v));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    const created = requestChat({
      alumniId: alumni.id,
      topic: topic.trim(),
      message: message.trim(),
      preferredTimes: times,
    });
    notify({
      type: "meeting",
      severity: "info",
      title: `Request sent to ${alumni.firstName} ${alumni.lastInitial}`,
      body: `${alumni.responseTime}. We'll alert you when there's an update.`,
      link: "/alumni?tab=requests",
      dedupKey: `meeting-sent:${created.id}`,
    });
    onSubmitted();
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-xl border border-slate-200 bg-white p-5"
    >
      <div>
        <h3 className="text-base font-semibold tracking-tight text-slate-950">
          Request a coffee chat
        </h3>
        <p className="mt-0.5 text-xs text-slate-500">
          Keep it short. {alumni.firstName} responds best to specific questions.
        </p>
      </div>

      <div>
        <label
          htmlFor="topic"
          className="text-xs font-semibold uppercase tracking-wide text-slate-600"
        >
          Topic
        </label>
        <select
          id="topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-100"
        >
          {alumni.topics.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label
          htmlFor="message"
          className="text-xs font-semibold uppercase tracking-wide text-slate-600"
        >
          Your message
        </label>
        <textarea
          id="message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={4}
          placeholder={`Hi ${alumni.firstName}, I'm a senior studying CS and would love to learn about your path into...`}
          className="mt-1.5 w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-100"
        />
        <p className="mt-1 text-xs text-slate-500">
          {message.trim().length < 20
            ? `${20 - message.trim().length} more character${
                20 - message.trim().length === 1 ? "" : "s"
              } recommended`
            : "Looks good."}
        </p>
      </div>

      <div>
        <label
          htmlFor="time"
          className="text-xs font-semibold uppercase tracking-wide text-slate-600"
        >
          Preferred times (optional)
        </label>
        <div className="mt-1.5 flex gap-2">
          <input
            id="time"
            value={timeDraft}
            onChange={(e) => setTimeDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addTime();
              }
            }}
            placeholder="Tue afternoon, weekend evenings..."
            className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
          <button
            type="button"
            onClick={addTime}
            className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          >
            <Plus className="h-4 w-4" />
            Add
          </button>
        </div>
        {times.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {times.map((t) => (
              <span
                key={t}
                className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-800"
              >
                {t}
                <button
                  type="button"
                  onClick={() => removeTime(t)}
                  className="rounded-full p-0.5 transition-colors hover:bg-blue-100"
                  aria-label={`Remove ${t}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
        <Link
          to="/alumni"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 transition-colors hover:text-slate-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to list
        </Link>
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
        >
          <Send className="h-4 w-4" />
          Send request
        </button>
      </div>
    </form>
  );
}
