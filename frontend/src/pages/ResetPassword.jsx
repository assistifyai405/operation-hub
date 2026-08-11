import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Loader2, CheckCircle2 } from "lucide-react";
import { authApi } from "@/lib/api";
import { AuthShell, inputClass } from "@/components/AuthShell";

export default function ResetPassword() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) { setError(t("auth.passwordMin")); return; }
    if (password !== confirm) { setError(t("auth.passwordMismatch")); return; }
    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
      setTimeout(() => navigate("/login"), 1800);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <AuthShell title={t("auth.invalidResetTitle")} subtitle={t("auth.invalidResetSubtitle")}>
        <p className="mt-6 text-sm text-zinc-400"><Link to="/forgot-password" className="text-brand-400 hover:text-brand-300">{t("auth.requestNewLink")}</Link></p>
      </AuthShell>
    );
  }

  return (
    <AuthShell title={t("auth.resetTitle")} subtitle={t("auth.resetSubtitle")}>
      {done ? (
        <div className="mt-8 flex items-center gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300" data-testid="reset-success">
          <CheckCircle2 className="h-5 w-5" /> {t("auth.passwordUpdated")}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-8 space-y-4" data-testid="reset-form">
          {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300" data-testid="reset-error">{error}</div>}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("auth.newPassword")}</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required data-testid="reset-password" className={inputClass} placeholder={t("auth.passwordMinPlaceholder")} />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("auth.confirmPassword")}</label>
            <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required data-testid="reset-confirm" className={inputClass} placeholder={t("auth.confirmPasswordPlaceholder")} />
          </div>
          <button type="submit" disabled={loading} data-testid="reset-submit" className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-60 glow-brand">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t("auth.updatePassword")}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
