#!/usr/bin/env node
/**
 * i18n consistency check.
 *
 * Verifies every non-base locale matches the base (English) locale on:
 *   1. the set of namespace files,
 *   2. the set of message keys (plural suffixes like _one/_other collapse to
 *      their base, so English _one/_other and Chinese _other are treated equal),
 *   3. the {{interpolation}} placeholders of keys present in both locales.
 *
 * Exits non-zero (with a report) on any mismatch so CI can gate on it.
 */
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const localesDir = join(here, "..", "src", "app", "i18n", "locales");
const BASE = "en";

const PLURAL_SUFFIX = /_(zero|one|two|few|many|other)$/;
const stripPlural = (key) => key.replace(PLURAL_SUFFIX, "");
const placeholders = (value) =>
  [...String(value).matchAll(/\{\{\s*([\w-]+)/g)].map((m) => m[1]).sort().join(",");

function flatten(obj, prefix = "", out = {}) {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object") flatten(v, key, out);
    else out[key] = v;
  }
  return out;
}

function loadLocale(lng) {
  const dir = join(localesDir, lng);
  const byNs = {};
  for (const file of readdirSync(dir).filter((f) => f.endsWith(".json"))) {
    const ns = file.replace(/\.json$/, "");
    byNs[ns] = flatten(JSON.parse(readFileSync(join(dir, file), "utf8")));
  }
  return byNs;
}

let errors = 0;
const fail = (msg) => {
  errors += 1;
  console.error(`  ✗ ${msg}`);
};

const base = loadLocale(BASE);
const others = readdirSync(localesDir).filter((d) => d !== BASE);

for (const lng of others) {
  const other = loadLocale(lng);
  const baseNs = Object.keys(base).sort();
  const otherNs = Object.keys(other).sort();

  for (const ns of baseNs) {
    if (!otherNs.includes(ns)) fail(`${lng}: missing namespace file ${ns}.json`);
  }
  for (const ns of otherNs) {
    if (!baseNs.includes(ns)) fail(`${lng}: extra namespace file ${ns}.json`);
  }

  for (const ns of baseNs) {
    if (!other[ns]) continue;
    const baseKeys = new Set(Object.keys(base[ns]).map(stripPlural));
    const otherKeys = new Set(Object.keys(other[ns]).map(stripPlural));
    for (const k of baseKeys) if (!otherKeys.has(k)) fail(`${lng}/${ns}: missing key "${k}"`);
    for (const k of otherKeys) if (!baseKeys.has(k)) fail(`${lng}/${ns}: extra key "${k}"`);

    for (const [k, value] of Object.entries(base[ns])) {
      if (other[ns][k] === undefined) continue; // e.g. English-only _one form
      const a = placeholders(value);
      const b = placeholders(other[ns][k]);
      if (a !== b) fail(`${lng}/${ns}: placeholders differ for "${k}" (en:[${a}] ${lng}:[${b}])`);
    }
  }
}

if (errors) {
  console.error(`\n${errors} i18n consistency error(s).`);
  process.exit(1);
}
console.log(`i18n locales are consistent (${others.join(", ")} vs ${BASE}).`);
