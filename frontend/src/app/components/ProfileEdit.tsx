import React from "react";
import { Link } from "react-router";
import { ChevronRight, Plus, Trash2, Check } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  EMPTY_EDUCATION,
  EMPTY_INTERNSHIP,
  EMPTY_PROFILE,
  EMPTY_PROJECT,
  Education,
  Internship,
  Project,
  parseCommaList,
  useProfile,
} from "../lib/profile";

function FieldRow({
  id,
  label,
  type = "text",
  value,
  onChange,
  placeholder,
}: {
  id: string;
  label: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
      />
    </div>
  );
}

function SectionHeader({
  title,
  onAdd,
}: {
  title: string;
  onAdd: () => void;
}) {
  const { t } = useTranslation("profile");
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        {title}
      </h2>
      <button
        type="button"
        onClick={onAdd}
        className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-50"
      >
        <Plus className="h-4 w-4" />
        {t("add")}
      </button>
    </div>
  );
}

function RemoveButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-red-50 hover:text-red-700"
      aria-label={label}
    >
      <Trash2 className="h-4 w-4" />
    </button>
  );
}

/** Education rows keep grade as editable text; converted to number on save. */
type EducationDraft = Omit<Education, "grade"> & { gradeText: string };

export function ProfileEdit() {
  const { t } = useTranslation(["profile", "nav"]);
  const { profile, saveProfile } = useProfile();

  const [name, setName] = React.useState(profile?.name ?? "");
  const [skillsText, setSkillsText] = React.useState(
    (profile?.skills ?? []).join(", ")
  );
  const [courseworkText, setCourseworkText] = React.useState(
    (profile?.coursework ?? []).join(", ")
  );
  const [education, setEducation] = React.useState<EducationDraft[]>(
    (profile?.education ?? []).map((e) => ({
      ...e,
      gradeText: e.grade != null ? String(e.grade) : "",
    }))
  );
  const [internships, setInternships] = React.useState<Internship[]>(
    profile?.internships ?? []
  );
  const [projects, setProjects] = React.useState<Project[]>(
    profile?.projects ?? []
  );
  const [saved, setSaved] = React.useState(false);

  const updateAt = <T,>(
    setter: React.Dispatch<React.SetStateAction<T[]>>,
    idx: number,
    patch: Partial<T>
  ) => {
    setter((prev) => prev.map((e, i) => (i === idx ? { ...e, ...patch } : e)));
  };

  const removeAt = <T,>(
    setter: React.Dispatch<React.SetStateAction<T[]>>,
    idx: number
  ) => {
    setter((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    saveProfile({
      ...EMPTY_PROFILE,
      ...profile,
      name: name.trim() || "Friend",
      skills: parseCommaList(skillsText),
      coursework: parseCommaList(courseworkText),
      education: education
        .filter((x) => x.degree.trim() || x.school.trim() || x.major.trim())
        .map(({ gradeText, ...rest }) => {
          const grade = Number.parseFloat(gradeText);
          return {
            ...rest,
            grade: Number.isFinite(grade) ? grade : null,
            end: rest.end?.trim() || null,
          };
        }),
      internships: internships
        .filter((x) => x.title.trim() || x.company.trim() || x.description.trim())
        .map((x) => ({ ...x, end: x.end?.trim() || null })),
      projects: projects
        .filter((x) => x.title.trim() || x.description.trim())
        .map((x) => ({ ...x, end: x.end?.trim() || null })),
    });
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <nav aria-label="breadcrumb">
        <ol className="flex flex-wrap items-center gap-1.5 text-sm text-slate-500">
          <li>
            <Link
              to="/"
              className="rounded-md px-1 transition-colors hover:bg-slate-100 hover:text-slate-900"
            >
              {t("nav:dashboard")}
            </Link>
          </li>
          <li aria-hidden="true">
            <ChevronRight className="h-4 w-4 text-slate-400" />
          </li>
          <li className="font-medium text-slate-900">{t("breadcrumb")}</li>
        </ol>
      </nav>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          {t("title")}
        </h1>
        <p className="mt-1 text-sm text-slate-500">{t("subtitle")}</p>
      </div>

      <form onSubmit={handleSave} className="space-y-8">
        <section className="space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("sections.basics")}
          </h2>
          <FieldRow
            id="name"
            label={t("fields.name")}
            value={name}
            onChange={setName}
            placeholder={t("placeholders.name")}
          />
        </section>

        <div className="h-px bg-slate-200/70" />

        <section className="space-y-4">
          <SectionHeader
            title={t("sections.education")}
            onAdd={() =>
              setEducation((prev) => [
                ...prev,
                { ...EMPTY_EDUCATION, gradeText: "" },
              ])
            }
          />
          {education.length === 0 ? (
            <p className="text-sm text-slate-500">{t("empty.education")}</p>
          ) : (
            <div className="space-y-5">
              {education.map((edu, idx) => (
                <div key={idx} className="space-y-3 rounded-xl border border-slate-200/70 p-4">
                  <div className="grid gap-3 sm:grid-cols-[1fr_1.4fr_auto] sm:items-end">
                    <FieldRow
                      id={`edu-degree-${idx}`}
                      label={t("fields.degree")}
                      value={edu.degree}
                      onChange={(v) => updateAt(setEducation, idx, { degree: v })}
                      placeholder="BSc"
                    />
                    <FieldRow
                      id={`edu-school-${idx}`}
                      label={t("fields.school")}
                      value={edu.school}
                      onChange={(v) => updateAt(setEducation, idx, { school: v })}
                      placeholder={t("placeholders.school")}
                    />
                    <RemoveButton
                      onClick={() => removeAt(setEducation, idx)}
                      label={t("remove.education")}
                    />
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <FieldRow
                      id={`edu-major-${idx}`}
                      label={t("fields.major")}
                      value={edu.major}
                      onChange={(v) => updateAt(setEducation, idx, { major: v })}
                      placeholder={t("placeholders.major")}
                    />
                    <FieldRow
                      id={`edu-grade-${idx}`}
                      label={t("fields.gpa")}
                      value={edu.gradeText}
                      onChange={(v) => updateAt(setEducation, idx, { gradeText: v })}
                      placeholder="3.7"
                    />
                    <FieldRow
                      id={`edu-start-${idx}`}
                      label={t("fields.start")}
                      value={edu.start}
                      onChange={(v) => updateAt(setEducation, idx, { start: v })}
                      placeholder="2022-09"
                    />
                    <FieldRow
                      id={`edu-end-${idx}`}
                      label={t("fields.end")}
                      value={edu.end ?? ""}
                      onChange={(v) => updateAt(setEducation, idx, { end: v })}
                      placeholder="2026-06"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="h-px bg-slate-200/70" />

        <section className="space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("sections.skills")}
          </h2>
          <FieldRow
            id="skills"
            label={t("fields.skills")}
            value={skillsText}
            onChange={setSkillsText}
            placeholder={t("placeholders.skills")}
          />
          <FieldRow
            id="coursework"
            label={t("fields.coursework")}
            value={courseworkText}
            onChange={setCourseworkText}
            placeholder={t("placeholders.coursework")}
          />
        </section>

        <div className="h-px bg-slate-200/70" />

        <section className="space-y-4">
          <SectionHeader
            title={t("sections.internships")}
            onAdd={() =>
              setInternships((prev) => [...prev, { ...EMPTY_INTERNSHIP }])
            }
          />
          {internships.length === 0 ? (
            <p className="text-sm text-slate-500">{t("empty.internships")}</p>
          ) : (
            <div className="space-y-5">
              {internships.map((item, idx) => (
                <div key={idx} className="space-y-3 rounded-xl border border-slate-200/70 p-4">
                  <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
                    <FieldRow
                      id={`int-title-${idx}`}
                      label={t("fields.role")}
                      value={item.title}
                      onChange={(v) => updateAt(setInternships, idx, { title: v })}
                      placeholder={t("placeholders.role")}
                    />
                    <FieldRow
                      id={`int-company-${idx}`}
                      label={t("fields.company")}
                      value={item.company}
                      onChange={(v) => updateAt(setInternships, idx, { company: v })}
                      placeholder={t("placeholders.company")}
                    />
                    <RemoveButton
                      onClick={() => removeAt(setInternships, idx)}
                      label={t("remove.internship")}
                    />
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <FieldRow
                      id={`int-start-${idx}`}
                      label={t("fields.start")}
                      value={item.start}
                      onChange={(v) => updateAt(setInternships, idx, { start: v })}
                      placeholder="2025-06"
                    />
                    <FieldRow
                      id={`int-end-${idx}`}
                      label={t("fields.end")}
                      value={item.end ?? ""}
                      onChange={(v) => updateAt(setInternships, idx, { end: v })}
                      placeholder="2025-09"
                    />
                  </div>
                  <FieldRow
                    id={`int-desc-${idx}`}
                    label={t("fields.description")}
                    value={item.description}
                    onChange={(v) => updateAt(setInternships, idx, { description: v })}
                    placeholder={t("placeholders.internDesc")}
                  />
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="h-px bg-slate-200/70" />

        <section className="space-y-4">
          <SectionHeader
            title={t("sections.projects")}
            onAdd={() => setProjects((prev) => [...prev, { ...EMPTY_PROJECT }])}
          />
          {projects.length === 0 ? (
            <p className="text-sm text-slate-500">{t("empty.projects")}</p>
          ) : (
            <div className="space-y-5">
              {projects.map((item, idx) => (
                <div key={idx} className="space-y-3 rounded-xl border border-slate-200/70 p-4">
                  <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
                    <FieldRow
                      id={`proj-title-${idx}`}
                      label={t("fields.title")}
                      value={item.title}
                      onChange={(v) => updateAt(setProjects, idx, { title: v })}
                      placeholder={t("placeholders.projTitle")}
                    />
                    <RemoveButton
                      onClick={() => removeAt(setProjects, idx)}
                      label={t("remove.project")}
                    />
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <FieldRow
                      id={`proj-start-${idx}`}
                      label={t("fields.start")}
                      value={item.start}
                      onChange={(v) => updateAt(setProjects, idx, { start: v })}
                      placeholder="2025-09"
                    />
                    <FieldRow
                      id={`proj-end-${idx}`}
                      label={t("fields.end")}
                      value={item.end ?? ""}
                      onChange={(v) => updateAt(setProjects, idx, { end: v })}
                      placeholder="2025-12"
                    />
                  </div>
                  <FieldRow
                    id={`proj-desc-${idx}`}
                    label={t("fields.description")}
                    value={item.description}
                    onChange={(v) => updateAt(setProjects, idx, { description: v })}
                    placeholder={t("placeholders.projDesc")}
                  />
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="flex items-center justify-end gap-3 border-t border-slate-200/70 pt-5">
          {saved && (
            <span className="inline-flex items-center gap-1.5 text-sm font-medium text-green-700">
              <Check className="h-4 w-4" />
              {t("saved")}
            </span>
          )}
          <Link
            to="/"
            className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          >
            {t("back")}
          </Link>
          <button
            type="submit"
            className="inline-flex h-10 items-center justify-center rounded-lg bg-blue-600 px-5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            {t("save")}
          </button>
        </div>
      </form>
    </div>
  );
}
