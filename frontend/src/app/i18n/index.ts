import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import applicationsEn from "./locales/en/applications.json";
import authEn from "./locales/en/auth.json";
import commonEn from "./locales/en/common.json";
import dashboardEn from "./locales/en/dashboard.json";
import jobsEn from "./locales/en/jobs.json";
import navEn from "./locales/en/nav.json";
import settingsEn from "./locales/en/settings.json";
import applicationsZh from "./locales/zh-CN/applications.json";
import authZh from "./locales/zh-CN/auth.json";
import commonZh from "./locales/zh-CN/common.json";
import dashboardZh from "./locales/zh-CN/dashboard.json";
import jobsZh from "./locales/zh-CN/jobs.json";
import navZh from "./locales/zh-CN/nav.json";
import settingsZh from "./locales/zh-CN/settings.json";

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
  },
  "zh-CN": {
    common: commonZh,
    nav: navZh,
    auth: authZh,
    settings: settingsZh,
    dashboard: dashboardZh,
    jobs: jobsZh,
    applications: applicationsZh,
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
    ns: ["common", "nav", "auth", "settings", "dashboard", "jobs", "applications"],
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: "aichh:lang",
      caches: ["localStorage"],
    },
  });

export default i18n;
