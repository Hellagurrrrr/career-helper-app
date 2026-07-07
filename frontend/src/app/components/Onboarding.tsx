import React from "react";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useAuth } from "../lib/auth";
import {
  Target,
  Upload,
  MessagesSquare,
  ArrowLeft,
  ArrowRight,
  FileText,
  Sparkles,
  Send,
  CheckCircle2,
  X,
} from "lucide-react";
import {
  EMPTY_EDUCATION,
  EMPTY_INTERNSHIP,
  EMPTY_PROFILE,
  EMPTY_PROJECT,
  Education,
  Profile,
  parseCommaList,
  useProfile,
} from "../lib/profile";
import { useNotifications } from "../lib/notifications";

type Step = "welcome" | "upload" | "extracting" | "chat" | "review";

type ChatMessage = {
  from: "bot" | "user";
  text: string;
};

// Prompt/placeholder text lives in the `onboarding` namespace (chat.questions.*),
// keyed by `id`; only the field-mapping stays in code.
type ChatQuestion = {
  id: string;
  apply: (draft: Profile, raw: string) => Profile;
};

function withEducation(draft: Profile, patch: Partial<Education>): Profile {
  const current = draft.education[0] ?? EMPTY_EDUCATION;
  return {
    ...draft,
    education: [{ ...current, ...patch }, ...draft.education.slice(1)],
  };
}

const CHAT_QUESTIONS: ChatQuestion[] = [
  { id: "name", apply: (draft, raw) => ({ ...draft, name: raw }) },
  { id: "school", apply: (draft, raw) => withEducation(draft, { school: raw }) },
  { id: "major", apply: (draft, raw) => withEducation(draft, { major: raw }) },
  { id: "degree", apply: (draft, raw) => withEducation(draft, { degree: raw }) },
  { id: "skills", apply: (draft, raw) => ({ ...draft, skills: parseCommaList(raw) }) },
  { id: "coursework", apply: (draft, raw) => ({ ...draft, coursework: parseCommaList(raw) }) },
];

function ProgressDots({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-1.5">
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={`h-1.5 rounded-full transition-all ${
            i < current
              ? "w-6 bg-blue-600"
              : i === current
              ? "w-6 bg-blue-400"
              : "w-3 bg-slate-200"
          }`}
        />
      ))}
    </div>
  );
}

export function Onboarding() {
  const navigate = useNavigate();
  const { t } = useTranslation(["onboarding", "common"]);
  const { saveProfile } = useProfile();
  const { notify } = useNotifications();
  const { currentUser } = useAuth();

  React.useEffect(() => {
    if (!currentUser) {
      navigate("/login", { replace: true });
    }
  }, [currentUser, navigate]);

  const [step, setStep] = React.useState<Step>("welcome");
  const [draft, setDraft] = React.useState<Profile>(EMPTY_PROFILE);
  const [fileName, setFileName] = React.useState<string | null>(null);

  const emitWelcome = (name: string) => {
    notify({
      type: "system",
      severity: "info",
      title: t("notify.welcomeTitle", { name }),
      body: t("notify.welcomeBody"),
      link: "/new-goal",
      dedupKey: "onboarding-welcome",
    });
  };

  const handleSkip = async () => {
    await saveProfile({ ...EMPTY_PROFILE, name: t("friend") });
    emitWelcome(t("friend"));
    navigate("/", { replace: true });
  };

  const finish = async (profile: Profile) => {
    await saveProfile(profile);
    emitWelcome(profile.name?.trim() || t("friend"));
    navigate("/", { replace: true });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-slate-50">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-4 pb-2 pt-6 sm:px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600">
            <Target className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-semibold tracking-tight text-slate-950">
            {t("common:appName")}
          </span>
        </div>
        {step !== "welcome" && (
          <button
            onClick={handleSkip}
            className="text-sm font-medium text-slate-500 transition-colors hover:text-slate-700"
          >
            {t("skipForNow")}
          </button>
        )}
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-12 pt-6 sm:px-6 lg:pt-10">
        {step === "welcome" && (
          <WelcomeStep
            onChooseUpload={() => setStep("upload")}
            onChooseChat={() => {
              setDraft(EMPTY_PROFILE);
              setStep("chat");
            }}
            onSkip={handleSkip}
          />
        )}

        {step === "upload" && (
          <UploadStep
            fileName={fileName}
            onBack={() => {
              setFileName(null);
              setStep("welcome");
            }}
            onSelectFile={(name) => setFileName(name)}
            onClearFile={() => setFileName(null)}
            onExtract={() => setStep("extracting")}
          />
        )}

        {step === "extracting" && (
          <ExtractingStep
            fileName={fileName ?? t("extracting.yourResume")}
            onDone={() => {
              setDraft({
                ...EMPTY_PROFILE,
                projects: [
                  {
                    ...EMPTY_PROJECT,
                    title: t("extracting.projectTitle"),
                    description: t("extracting.projectDesc"),
                  },
                ],
              });
              setStep("review");
            }}
          />
        )}

        {step === "chat" && (
          <ChatStep
            onBack={() => setStep("welcome")}
            onComplete={(collected) => {
              setDraft(collected);
              setStep("review");
            }}
          />
        )}

        {step === "review" && (
          <ReviewStep
            draft={draft}
            onChange={setDraft}
            onBack={() =>
              setStep(fileName ? "upload" : "chat")
            }
            onSave={finish}
          />
        )}
      </main>
    </div>
  );
}

function WelcomeStep({
  onChooseUpload,
  onChooseChat,
  onSkip,
}: {
  onChooseUpload: () => void;
  onChooseChat: () => void;
  onSkip: () => void;
}) {
  const { t } = useTranslation("onboarding");
  return (
    <div className="space-y-8">
      <div className="text-center">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium uppercase tracking-wide text-blue-700">
          <Sparkles className="h-3.5 w-3.5" />
          {t("welcome.eyebrow")}
        </span>
        <h1 className="mx-auto mt-4 max-w-2xl text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
          {t("welcome.title")}
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-slate-600">{t("welcome.subtitle")}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <button
          onClick={onChooseUpload}
          className="group flex h-full flex-col items-start gap-4 rounded-xl border border-slate-200 bg-white p-6 text-left transition-colors hover:border-blue-300 hover:bg-blue-50/30"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-700 transition-colors group-hover:bg-blue-100">
            <Upload className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold tracking-tight text-slate-950">
              {t("welcome.uploadTitle")}
            </h2>
            <p className="mt-1 text-sm text-slate-600">{t("welcome.uploadBody")}</p>
          </div>
          <span className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700">
            {t("welcome.uploadCta")}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </span>
        </button>

        <button
          onClick={onChooseChat}
          className="group flex h-full flex-col items-start gap-4 rounded-xl border border-slate-200 bg-white p-6 text-left transition-colors hover:border-blue-300 hover:bg-blue-50/30"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-700 transition-colors group-hover:bg-blue-100">
            <MessagesSquare className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold tracking-tight text-slate-950">
              {t("welcome.chatTitle")}
            </h2>
            <p className="mt-1 text-sm text-slate-600">{t("welcome.chatBody")}</p>
          </div>
          <span className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700">
            {t("welcome.chatCta")}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </span>
        </button>
      </div>

      <div className="text-center">
        <button
          onClick={onSkip}
          className="text-sm font-medium text-slate-500 transition-colors hover:text-slate-700"
        >
          {t("welcome.skipExplore")}
        </button>
      </div>
    </div>
  );
}

function UploadStep({
  fileName,
  onBack,
  onSelectFile,
  onClearFile,
  onExtract,
}: {
  fileName: string | null;
  onBack: () => void;
  onSelectFile: (name: string) => void;
  onClearFile: () => void;
  onExtract: () => void;
}) {
  const { t } = useTranslation("onboarding");
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = React.useState(false);

  const acceptFile = (file: File | null | undefined) => {
    if (!file) return;
    onSelectFile(file.name);
  };

  return (
    <div className="space-y-6">
      <StepHeader
        eyebrow={t("upload.eyebrow")}
        title={t("upload.title")}
        description={t("upload.description")}
        onBack={onBack}
      />

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          acceptFile(e.dataTransfer.files?.[0]);
        }}
        className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
          dragOver
            ? "border-blue-400 bg-blue-50"
            : "border-slate-300 bg-white"
        }`}
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
          <Upload className="h-7 w-7" />
        </div>
        <p className="text-base font-semibold text-slate-950">{t("upload.dropHere")}</p>
        <p className="max-w-sm text-sm text-slate-600">{t("upload.supports")}</p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-1 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          {t("upload.chooseFile")}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.doc,.docx,.txt"
          className="hidden"
          onChange={(e) => acceptFile(e.target.files?.[0])}
        />
      </div>

      {fileName && (
        <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-950">{fileName}</p>
              <p className="text-xs text-slate-500">{t("upload.readyToAnalyze")}</p>
            </div>
          </div>
          <button
            onClick={onClearFile}
            className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100"
            aria-label={t("upload.removeFile")}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={onExtract}
          disabled={!fileName}
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
        >
          {t("upload.extractInfo")}
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function ExtractingStep({
  fileName,
  onDone,
}: {
  fileName: string;
  onDone: () => void;
}) {
  const { t } = useTranslation("onboarding");
  const [stage, setStage] = React.useState(0);
  const stages = [
    t("extracting.stage1"),
    t("extracting.stage2"),
    t("extracting.stage3"),
  ];

  React.useEffect(() => {
    if (stage < stages.length - 1) {
      const t = window.setTimeout(() => setStage((s) => s + 1), 800);
      return () => window.clearTimeout(t);
    }
    const done = window.setTimeout(onDone, 900);
    return () => window.clearTimeout(done);
  }, [stage, onDone, stages.length]);

  return (
    <div className="flex flex-col items-center justify-center gap-6 rounded-xl border border-slate-200 bg-white p-12 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
        <Sparkles className="h-7 w-7 animate-pulse" />
      </div>
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-slate-950">
          {t("extracting.analyzing", { fileName })}
        </h2>
        <p className="mt-2 text-sm text-slate-600">{stages[stage]}</p>
      </div>
      <div className="h-1.5 w-64 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-blue-600 transition-[width] duration-700 ease-out"
          style={{ width: `${((stage + 1) / stages.length) * 100}%` }}
        />
      </div>
    </div>
  );
}

function ChatStep({
  onBack,
  onComplete,
}: {
  onBack: () => void;
  onComplete: (profile: Profile) => void;
}) {
  const { t } = useTranslation("onboarding");
  const questionText = (id: string) => t(`chat.questions.${id}.prompt`);
  const [messages, setMessages] = React.useState<ChatMessage[]>([
    { from: "bot", text: questionText(CHAT_QUESTIONS[0].id) },
  ]);
  const [draft, setDraft] = React.useState<Profile>(EMPTY_PROFILE);
  const [index, setIndex] = React.useState(0);
  const [input, setInput] = React.useState("");
  const scrollerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (scrollerRef.current) {
      scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    const question = CHAT_QUESTIONS[index];
    const updatedDraft = question.apply(draft, trimmed);

    const next: ChatMessage[] = [
      ...messages,
      { from: "user", text: trimmed },
    ];

    const nextIndex = index + 1;
    if (nextIndex < CHAT_QUESTIONS.length) {
      next.push({ from: "bot", text: questionText(CHAT_QUESTIONS[nextIndex].id) });
      setMessages(next);
      setDraft(updatedDraft);
      setIndex(nextIndex);
      setInput("");
    } else {
      next.push({
        from: "bot",
        text: t("chat.done"),
      });
      setMessages(next);
      setDraft(updatedDraft);
      setInput("");
      window.setTimeout(() => onComplete(updatedDraft), 600);
    }
  };

  return (
    <div className="space-y-5">
      <StepHeader
        eyebrow={t("chat.questionOf", {
          current: Math.min(index + 1, CHAT_QUESTIONS.length),
          total: CHAT_QUESTIONS.length,
        })}
        title={t("chat.title")}
        description={t("chat.description")}
        onBack={onBack}
      />

      <div className="rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-5 py-3">
          <ProgressDots current={index} total={CHAT_QUESTIONS.length} />
        </div>

        <div
          ref={scrollerRef}
          className="flex max-h-[420px] min-h-[280px] flex-col gap-3 overflow-y-auto p-5"
        >
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${
                m.from === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                  m.from === "user"
                    ? "rounded-br-md bg-blue-600 text-white"
                    : "rounded-bl-md bg-slate-100 text-slate-800"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-2 border-t border-slate-100 p-3"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              index < CHAT_QUESTIONS.length
                ? t(`chat.questions.${CHAT_QUESTIONS[index].id}.placeholder`)
                : t("chat.sending")
            }
            disabled={index >= CHAT_QUESTIONS.length}
            className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:bg-slate-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || index >= CHAT_QUESTIONS.length}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            aria-label={t("chat.send")}
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}

function ReviewStep({
  draft,
  onChange,
  onBack,
  onSave,
}: {
  draft: Profile;
  onChange: (next: Profile) => void;
  onBack: () => void;
  onSave: (profile: Profile) => void;
}) {
  const { t } = useTranslation(["onboarding", "profile"]);
  const [skillsText, setSkillsText] = React.useState(draft.skills.join(", "));
  const [courseworkText, setCourseworkText] = React.useState(
    draft.coursework.join(", ")
  );
  const edu = draft.education[0] ?? EMPTY_EDUCATION;
  const [gradeText, setGradeText] = React.useState(
    edu.grade != null ? String(edu.grade) : ""
  );
  const [internship, setInternship] = React.useState({
    ...EMPTY_INTERNSHIP,
    ...(draft.internships[0] ?? {}),
    end: draft.internships[0]?.end ?? "",
  });

  const canSave = draft.name.trim().length > 0;

  const setEdu = (patch: Partial<Education>) =>
    onChange(withEducation(draft, patch));

  const handleSave = () => {
    const grade = Number.parseFloat(gradeText);
    const education = [
      {
        ...edu,
        grade: Number.isFinite(grade) ? grade : null,
        end: edu.end?.trim() || null,
      },
      ...draft.education.slice(1),
    ].filter((e) => e.degree.trim() || e.school.trim() || e.major.trim());

    const hasInternship =
      internship.title.trim() ||
      internship.company.trim() ||
      internship.description.trim();

    const finalProfile: Profile = {
      ...draft,
      education,
      skills: parseCommaList(skillsText),
      coursework: parseCommaList(courseworkText),
      internships: hasInternship
        ? [{ ...internship, end: internship.end?.trim() || null }]
        : [],
    };
    onChange(finalProfile);
    onSave(finalProfile);
  };

  return (
    <div className="space-y-5">
      <StepHeader
        eyebrow={t("review.eyebrow")}
        title={t("review.title")}
        description={t("review.description")}
        onBack={onBack}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Field
          label={t("profile:fields.name")}
          value={draft.name}
          onChange={(v) => onChange({ ...draft, name: v })}
          placeholder={t("profile:placeholders.name")}
          required
          full
        />

        <div className="rounded-xl border border-slate-200 bg-white p-5 lg:col-span-2">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            {t("profile:sections.education")}
          </h3>
          <div className="grid gap-3 sm:grid-cols-4">
            <Field
              label={t("profile:fields.degree")}
              value={edu.degree}
              onChange={(v) => setEdu({ degree: v })}
              placeholder="BSc"
              inline
            />
            <Field
              label={t("profile:fields.school")}
              value={edu.school}
              onChange={(v) => setEdu({ school: v })}
              placeholder={t("profile:placeholders.school")}
              inline
            />
            <Field
              label={t("profile:fields.major")}
              value={edu.major}
              onChange={(v) => setEdu({ major: v })}
              placeholder={t("profile:placeholders.major")}
              inline
            />
            <Field
              label={t("profile:fields.gpa")}
              value={gradeText}
              onChange={setGradeText}
              placeholder="3.7"
              inline
            />
            <Field
              label={t("profile:fields.start")}
              value={edu.start}
              onChange={(v) => setEdu({ start: v })}
              placeholder="2022-09"
              inline
            />
            <Field
              label={t("profile:fields.end")}
              value={edu.end ?? ""}
              onChange={(v) => setEdu({ end: v })}
              placeholder="2026-06"
              inline
            />
          </div>
        </div>

        <Field
          label={t("profile:fields.skills")}
          value={skillsText}
          onChange={setSkillsText}
          placeholder={t("profile:placeholders.skills")}
          full
        />
        <Field
          label={t("profile:fields.coursework")}
          value={courseworkText}
          onChange={setCourseworkText}
          placeholder={t("profile:placeholders.coursework")}
          full
        />

        <div className="rounded-xl border border-slate-200 bg-white p-5 lg:col-span-2">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            {t("review.internshipTitle")}
          </h3>
          <div className="grid gap-3 sm:grid-cols-4">
            <Field
              label={t("profile:fields.role")}
              value={internship.title}
              onChange={(v) => setInternship({ ...internship, title: v })}
              placeholder={t("profile:placeholders.role")}
              inline
            />
            <Field
              label={t("profile:fields.company")}
              value={internship.company}
              onChange={(v) => setInternship({ ...internship, company: v })}
              placeholder={t("profile:placeholders.company")}
              inline
            />
            <Field
              label={t("profile:fields.start")}
              value={internship.start}
              onChange={(v) => setInternship({ ...internship, start: v })}
              placeholder="2025-06"
              inline
            />
            <Field
              label={t("profile:fields.end")}
              value={internship.end ?? ""}
              onChange={(v) => setInternship({ ...internship, end: v })}
              placeholder="2025-09"
              inline
            />
          </div>
          <div className="mt-3">
            <Field
              label={t("profile:fields.description")}
              value={internship.description}
              onChange={(v) =>
                setInternship({ ...internship, description: v })
              }
              placeholder={t("profile:placeholders.internDesc")}
              inline
            />
          </div>
        </div>
      </div>

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <button
          onClick={onBack}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("back")}
        </button>
        <button
          onClick={handleSave}
          disabled={!canSave}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
        >
          <CheckCircle2 className="h-4 w-4" />
          {t("review.continue")}
        </button>
      </div>
    </div>
  );
}

function StepHeader({
  eyebrow,
  title,
  description,
  onBack,
}: {
  eyebrow: string;
  title: string;
  description: string;
  onBack: () => void;
}) {
  const { t } = useTranslation("onboarding");
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-blue-700">
          {eyebrow}
        </p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
          {title}
        </h1>
        <p className="mt-1 text-slate-600">{description}</p>
      </div>
      <button
        onClick={onBack}
        className="inline-flex items-center gap-2 self-start rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("back")}
      </button>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  required,
  full,
  inline,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  full?: boolean;
  inline?: boolean;
}) {
  return (
    <label
      className={`block ${
        inline
          ? ""
          : `rounded-xl border border-slate-200 bg-white p-4 ${
              full ? "lg:col-span-2" : ""
            }`
      }`}
    >
      <span className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
        {required && <span className="ml-1 text-red-600">*</span>}
      </span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
      />
    </label>
  );
}
