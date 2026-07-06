import { Globe } from "lucide-react";
import { useTranslation } from "react-i18next";
import { languageNames, supportedLngs, type Language } from "../i18n";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";

export function LanguageSelect({ className }: { className?: string }) {
  const { i18n, t } = useTranslation("common");
  const current = (i18n.resolvedLanguage ?? i18n.language) as Language;

  return (
    <Select value={current} onValueChange={(lng) => void i18n.changeLanguage(lng)}>
      <SelectTrigger className={className} aria-label={t("language.label")}>
        <Globe className="h-4 w-4 shrink-0" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {supportedLngs.map((lng) => (
          <SelectItem key={lng} value={lng}>
            {languageNames[lng]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
