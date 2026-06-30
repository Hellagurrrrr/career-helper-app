import { formatPeriod, latestEducation, type Profile } from "./profile";
import type { JobListing } from "./jobs";

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** AI-style tailored résumé text for a specific role (mock content, editable by user). */
export function buildTailoredCvText(
  profile: Profile | null,
  job: JobListing,
  goalTitle: string
): string {
  const name = profile?.name?.trim() || "[Your name]";
  const email = "[your.email@university.edu]";
  const phone = "[phone]";
  const edu = latestEducation(profile);
  const uni = edu?.school?.trim() || "[University]";
  const major = edu?.major?.trim() || "[Major]";
  const degree = edu?.degree?.trim() || "[Degree]";
  const skills = profile?.skills?.length
    ? profile.skills.join(", ")
    : job.skills.slice(0, 5).join(", ");
  const topSkills = job.skills.join(", ");

  const expBlock =
    profile?.internships?.length
      ? profile.internships
          .map((e) => {
            const period = formatPeriod(e.start, e.end);
            const headline = `• ${e.title} — ${e.company}${period ? ` (${period})` : ""}`;
            const detail = e.description?.trim()
              ? `  ${e.description.trim()}`
              : `  Focus: outcomes aligned with ${job.company}'s stack and pace.`;
            return `${headline}\n${detail}`;
          })
          .join("\n")
      : `• [Add your internships here — emphasize impact metrics relevant to ${job.title}.]`;

  const projectsBlock =
    profile?.projects?.length
      ? profile.projects
          .map((p) => {
            const period = formatPeriod(p.start, p.end);
            const headline = `• ${p.title}${period ? ` (${period})` : ""}`;
            return p.description?.trim()
              ? `${headline}\n  ${p.description.trim()}`
              : headline;
          })
          .join("\n")
      : `• [Summarize 1–2 projects with metrics — tie bullets to ${job.title} responsibilities.]`;

  const educationBlock =
    profile?.education?.length
      ? profile.education
          .map((e) => {
            const period = formatPeriod(e.start, e.end);
            const base = `${e.school || "[School]"} — ${e.degree || "[Degree]"}, ${e.major || "[Major]"}`;
            const extras = [
              period,
              e.grade != null ? `GPA ${e.grade}` : "",
            ].filter(Boolean);
            return extras.length ? `${base} (${extras.join(" · ")})` : base;
          })
          .join("\n")
      : `${uni} — ${degree}, ${major}`;

  return [
    `${name}`,
    `${email} · ${phone}`,
    `${uni} · ${major} · ${degree}`,
    "",
    `TARGET ROLE (tailored)`,
    `${job.title} — ${job.company} (${job.type}, ${job.location})`,
    `Career goal context: ${goalTitle} · Match emphasis: ${topSkills}`,
    "",
    `PROFESSIONAL SUMMARY`,
    `Motivated candidate tailoring narrative toward ${job.title} at ${job.company}. Highlights strengths in ${skills} with explicit alignment to this posting's focus on ${job.skills.slice(0, 3).join(", ")}. Framed for ${job.partner ? "referral-forward review by the hiring team" : "recruiter screening and hiring-manager review"}.`,
    "",
    `CORE SKILLS (role-aligned)`,
    `${job.skills.map((s) => `• ${s}`).join("\n")}`,
    `Also: ${skills}`,
    "",
    `SELECTED INTERNSHIPS`,
    expBlock,
    "",
    `PROJECTS`,
    projectsBlock,
    "",
    `EDUCATION`,
    educationBlock,
    profile?.coursework?.length
      ? `Relevant coursework: ${profile.coursework.slice(0, 6).join(", ")}`
      : "",
    "",
    `CLOSING`,
    `References and links available on request. This version was auto-generated for this application and should be edited to reflect your authentic voice and facts.`,
  ]
    .filter(Boolean)
    .join("\n");
}

export function downloadCvAsWord(cvText: string, baseFileName: string) {
  const safe = baseFileName.replace(/[^\w\-]+/g, "-").slice(0, 60);
  const body = escapeHtml(cvText).replace(/\n/g, "<br/>");
  const html = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40"><head><meta charset="utf-8"><title>CV</title></head><body><div style="font-family:Calibri,Arial,sans-serif;font-size:11pt;line-height:1.4">${body}</div></body></html>`;
  const blob = new Blob(["\ufeff", html], {
    type: "application/msword;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${safe}-tailored-cv.doc`;
  a.click();
  URL.revokeObjectURL(url);
}

/** Opens a print-friendly page so the user can Save as PDF from the browser. */
export function openCvPrintPreview(title: string, cvText: string) {
  const w = window.open("", "_blank", "noopener,noreferrer");
  if (!w) return;
  const body = escapeHtml(cvText);
  w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
  <style>
    body { font-family: system-ui, Segoe UI, sans-serif; padding: 2rem; max-width: 720px; margin: 0 auto; line-height: 1.5; color: #0f172a; }
    h1 { font-size: 1.15rem; margin-bottom: 1rem; }
    pre { white-space: pre-wrap; font-family: inherit; margin: 0; }
    .bar { margin-bottom: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
    button { padding: 0.5rem 0.75rem; border-radius: 8px; border: 1px solid #cbd5e1; background: #fff; cursor: pointer; font-size: 14px; }
    button.primary { background: #2563eb; color: #fff; border-color: #2563eb; }
    @media print { .bar { display: none; } body { padding: 0; } }
  </style></head><body>
  <div class="bar">
    <button type="button" class="primary" onclick="window.print()">Print / Save as PDF</button>
    <button type="button" onclick="window.close()">Close</button>
  </div>
  <h1>${escapeHtml(title)}</h1>
  <pre>${body}</pre>
  </body></html>`);
  w.document.close();
}

function wrapCanvasLines(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number
): string[] {
  const out: string[] = [];
  for (const paragraph of text.split("\n")) {
    const words = paragraph.split(/\s+/).filter(Boolean);
    let line = "";
    for (const w of words) {
      const test = line ? `${line} ${w}` : w;
      if (ctx.measureText(test).width > maxWidth && line) {
        out.push(line);
        line = w;
      } else {
        line = test;
      }
    }
    if (line) out.push(line);
    out.push("");
  }
  return out;
}

export function downloadCvAsPng(cvText: string, baseFileName: string) {
  const safe = baseFileName.replace(/[^\w\-]+/g, "-").slice(0, 60);
  const pad = 48;
  const width = 612;
  const lineHeight = 20;
  const font = '14px system-ui, "Segoe UI", sans-serif';
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.font = font;
  const maxTextWidth = width - pad * 2;
  const lines = wrapCanvasLines(ctx, cvText, maxTextWidth);
  const height = Math.min(
    12000,
    Math.max(792, pad * 2 + lines.length * lineHeight + 24)
  );
  canvas.width = width;
  canvas.height = height;
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "#0f172a";
  ctx.font = font;
  let y = pad + lineHeight;
  for (const line of lines) {
    if (y > height - pad) break;
    ctx.fillText(line, pad, y);
    y += lineHeight;
  }
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${safe}-tailored-cv.png`;
    a.click();
    URL.revokeObjectURL(url);
  }, "image/png");
}
