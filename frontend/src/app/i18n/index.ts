import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import alumniEn from "./locales/en/alumni.json";
import applicationsEn from "./locales/en/applications.json";
import authEn from "./locales/en/auth.json";
import coachingEn from "./locales/en/coaching.json";
import commonEn from "./locales/en/common.json";
import dashboardEn from "./locales/en/dashboard.json";
import jobsEn from "./locales/en/jobs.json";
import navEn from "./locales/en/nav.json";
import newGoalEn from "./locales/en/newGoal.json";
import onboardingEn from "./locales/en/onboarding.json";
import profileEn from "./locales/en/profile.json";
import settingsEn from "./locales/en/settings.json";
import trackingEn from "./locales/en/tracking.json";
import alumniZh from "./locales/zh-CN/alumni.json";
import applicationsZh from "./locales/zh-CN/applications.json";
import authZh from "./locales/zh-CN/auth.json";
import coachingZh from "./locales/zh-CN/coaching.json";
import commonZh from "./locales/zh-CN/common.json";
import dashboardZh from "./locales/zh-CN/dashboard.json";
import jobsZh from "./locales/zh-CN/jobs.json";
import navZh from "./locales/zh-CN/nav.json";
import newGoalZh from "./locales/zh-CN/newGoal.json";
import onboardingZh from "./locales/zh-CN/onboarding.json";
import profileZh from "./locales/zh-CN/profile.json";
import settingsZh from "./locales/zh-CN/settings.json";
import trackingZh from "./locales/zh-CN/tracking.json";

export const defaultNS = "common";
export const supportedLngs = ["en", "zh-CN"] as const;
export type Language = (typeof supportedLngs)[number];

// Endonyms — a language name is conventionally shown in its own language,
// so these stay the same regardless of the active UI language.
export const languageNames: Record<Language, string> = {
  en: "English",
  "zh-CN": "简体中文",
};

export const resources = {
  en: {
    common: commonEn,
    nav: navEn,
    auth: authEn,
    settings: settingsEn,
    dashboard: dashboardEn,
    jobs: jobsEn,
    applications: applicationsEn,
    coaching: coachingEn,
    alumni: alumniEn,
    newGoal: newGoalEn,
    tracking: trackingEn,
    profile: profileEn,
    onboarding: onboardingEn,
  },
  "zh-CN": {
    common: commonZh,
    nav: navZh,
    auth: authZh,
    settings: settingsZh,
    dashboard: dashboardZh,
    jobs: jobsZh,
    applications: applicationsZh,
    coaching: coachingZh,
    alumni: alumniZh,
    newGoal: newGoalZh,
    tracking: trackingZh,
    profile: profileZh,
    onboarding: onboardingZh,
  },
} as const;

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "en",
    supportedLngs: [...supportedLngs],
    defaultNS,
    ns: [
      "common",
      "nav",
      "auth",
      "settings",
      "dashboard",
      "jobs",
      "applications",
      "coaching",
      "alumni",
      "newGoal",
      "tracking",
      "profile",
      "onboarding",
    ],
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: "aichh:lang",
      caches: ["localStorage"],
    },
  });

export default i18n;
