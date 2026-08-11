import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowLeft, Loader2, MailCheck } from "lucide-react";
import { authApi } from "@/lib/api";
import { AuthShell, inputClass } from "@/components/AuthShell";

export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [devLink, setDevLink] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.forgotPassword(email.trim());
      setDevLink(res.resetLink || "");
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title={t("auth.forgotTitle")}
      subtitle={t("auth.forgotSubtitle")}
      footer={
        <p className="mt-6 text-center text-xs text-zinc-500">
          <Link to="/login" className="inline-flex items-center gap-1 text-brand-400 hover:text-brand-300" data-testid="back-to-login">
            <ArrowLeft className="h-3 w-3" /> {t("auth.backToSignIn")}
          </Link>
        </p>
      }
    >
      {sent ? (
        <div className="mt-8 space-y-4" data-testid="forgot-sent">
          <div className="flex items-center gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
            <MailCheck className="h-5 w-5 shrink-0" /> {t("auth.resetSent")}
          </div>
          {devLink && (
            <div className="rounded-lg border border-white/10 bg-zinc-950 p-3">
              <p className="mb-1 text-xs font-medium text-zinc-500">{t("auth.devResetLink")}</p>
              <Link to={devLink.replace(/^https?:\/\/[^/]+/, "")} className="break-all text-xs text-brand-400 hover:text-brand-300" data-testid="dev-reset-link">{devLink}</Link>
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-8 space-y-4" data-testid="forgot-form">
          {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</div>}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("auth.email")}</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="forgot-email" className={inputClass} placeholder={t("auth.emailPlaceholder")} />
          </div>
          <button type="submit" disabled={loading} data-testid="forgot-submit" className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-60 glow-brand">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t("auth.sendResetLink")}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
