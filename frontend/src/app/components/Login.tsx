import React from "react";
import { Link, useNavigate } from "react-router";
import { ArrowRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../lib/auth";
import { useProfile } from "../lib/profile";
import { AuthLayout, AuthField } from "./AuthLayout";

export function Login() {
  const navigate = useNavigate();
  const { t } = useTranslation("auth");
  const { login } = useAuth();
  const { refreshProfile } = useProfile();

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  const [submitting, setSubmitting] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const result = await login(email, password);
    setSubmitting(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    const nextProfile = await refreshProfile();
    navigate(nextProfile ? "/" : "/onboarding", { replace: true });
  };

  return (
    <AuthLayout
      title={t("login.title")}
      subtitle={t("login.subtitle")}
      footer={
        <>
          {t("login.newHere")}{" "}
          <Link to="/register" className="font-medium text-blue-700 hover:underline">
            {t("login.createAccount")}
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <AuthField
          id="email"
          label={t("fields.email")}
          type="email"
          value={email}
          onChange={setEmail}
          placeholder={t("fields.emailPlaceholder")}
          autoComplete="email"
        />
        <AuthField
          id="password"
          label={t("fields.password")}
          type="password"
          value={password}
          onChange={setPassword}
          placeholder={t("fields.passwordPlaceholder")}
          autoComplete="current-password"
        />

        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          {submitting ? t("login.submitting") : t("login.submit")}
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>
    </AuthLayout>
  );
}
