import React from "react";
import { Link, useNavigate } from "react-router";
import { ArrowRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../lib/auth";
import { AuthLayout, AuthField } from "./AuthLayout";

export function Register() {
  const navigate = useNavigate();
  const { t } = useTranslation("auth");
  const { register } = useAuth();

  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const result = await register({ name, email, password });
    setSubmitting(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    navigate("/onboarding", { replace: true });
  };

  return (
    <AuthLayout
      title={t("register.title")}
      subtitle={t("register.subtitle")}
      footer={
        <>
          {t("register.haveAccount")}{" "}
          <Link to="/login" className="font-medium text-blue-700 hover:underline">
            {t("register.signIn")}
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <AuthField
          id="name"
          label={t("fields.name")}
          value={name}
          onChange={setName}
          placeholder={t("fields.namePlaceholder")}
          autoComplete="name"
        />
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
          placeholder={t("fields.newPasswordPlaceholder")}
          autoComplete="new-password"
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
          {submitting ? t("register.submitting") : t("register.submit")}
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>
    </AuthLayout>
  );
}
