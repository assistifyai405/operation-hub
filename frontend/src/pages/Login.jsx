import { useState } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { AuthShell, inputClass } from "@/components/AuthShell";
import { DEMO_LOGIN_ENABLED } from "@/lib/config";

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const inviteToken = params.get("invite") || sessionStorage.getItem("pending_invite_token") || "";
  const { login, demo } = useAuth();
  const [email, setEmail] = useState(params.get("email") || "");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(email, password, remember);
      if (inviteToken) {
        navigate(`/invite/${inviteToken}`);
        return;
      }
      navigate(data?.user?.onboardingCompleted === false ? "/onboarding" : "/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDemo = async () => {
    setError("");
    setDemoLoading(true);
    try {
      await demo();
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <AuthShell
      title={t("auth.loginTitle")}
      subtitle={inviteToken ? t("auth.inviteLoginSubtitle") : t("auth.loginSubtitle")}
      footer={
        <p className="mt-6 text-center text-xs text-zinc-500">
          {t("auth.noAccount")}{" "}
          <Link
            to={inviteToken ? `/register?invite=${encodeURIComponent(inviteToken)}&email=${encodeURIComponent(email)}` : "/register"}
            className="text-brand-400 hover:text-brand-300"
            data-testid="go-register-link"
          >
            {t("auth.createAccount")}
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="mt-8 space-y-4" data-testid="login-form">
        {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300" data-testid="login-error">{error}</div>}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("auth.email")}</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email" className={inputClass} placeholder={t("auth.emailPlaceholder")} />
        </div>
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <label className="block text-xs font-medium text-zinc-400">{t("auth.password")}</label>
            <Link to="/forgot-password" className="text-xs text-brand-400 hover:text-brand-300" data-testid="forgot-link">{t("auth.forgotPassword")}</Link>
          </div>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password" className={inputClass} placeholder="••••••••" />
        </div>
        <label className="flex items-center gap-2 text-xs text-zinc-400">
          <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} data-testid="remember-me" className="h-4 w-4 rounded border-white/10 bg-zinc-950 accent-brand-600" />
          {t("auth.rememberMe")}
        </label>
        <button type="submit" disabled={loading || demoLoading} data-testid="login-submit" className="group flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-60 glow-brand">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <>{t("auth.signIn")} <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" /></>}
        </button>
        {!inviteToken && DEMO_LOGIN_ENABLED && (
          <>
            <div className="flex items-center gap-3 py-1">
              <div className="h-px flex-1 bg-white/10" />
              <span className="text-[11px] uppercase tracking-wide text-zinc-600">{t("common.or")}</span>
              <div className="h-px flex-1 bg-white/10" />
            </div>
            <button type="button" onClick={handleDemo} disabled={loading || demoLoading} data-testid="explore-demo-btn" className="flex w-full items-center justify-center gap-2 rounded-lg border border-brand-500/40 bg-brand-500/10 py-2.5 text-sm font-semibold text-brand-200 transition-all hover:bg-brand-500/20 disabled:opacity-60">
              {demoLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Sparkles className="h-4 w-4" /> {t("auth.exploreDemo")}</>}
            </button>
            <p className="text-center text-[11px] text-zinc-600">{t("auth.demoHint")}</p>
          </>
        )}
      </form>
    </AuthShell>
  );
}
