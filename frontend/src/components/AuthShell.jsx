import { Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";

export function AuthShell({ title, subtitle, children, footer }) {
  const { t } = useTranslation();
  return (
    <div className="grid min-h-screen grid-cols-1 bg-black lg:grid-cols-2">
      <div className="relative hidden overflow-hidden border-r border-white/10 lg:flex lg:flex-col lg:justify-between grid-bg p-12">
        <div className="absolute -left-32 top-1/3 h-96 w-96 rounded-full bg-brand-600/20 blur-[120px]" />
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 glow-brand">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <p className="text-lg font-bold tracking-tight">{t("app.name")} <span className="text-brand-400">OS</span></p>
        </div>
        <div className="relative z-10 max-w-md">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-400">{t("app.name")} OS</p>
          <h2 className="mt-3 text-4xl font-bold leading-tight tracking-tight text-zinc-50">
            {t("auth.heroTitle")}
          </h2>
          <p className="mt-4 text-base leading-relaxed text-zinc-400">
            {t("auth.heroBody")}
          </p>
          <div className="mt-8 flex flex-col gap-2 text-sm font-medium text-zinc-300">
            <div>{t("auth.heroPoints.one")}</div>
            <div>{t("auth.heroPoints.two")}</div>
            <div>{t("auth.heroPoints.three")}</div>
          </div>
        </div>
        <p className="relative z-10 text-xs text-zinc-600">
          © 2026 {t("app.name")} ·{" "}
          <a href="/privacy" className="hover:text-zinc-400">{t("legal.privacy")}</a>
          {" · "}
          <a href="/terms" className="hover:text-zinc-400">{t("legal.terms")}</a>
          {" · "}
          <a href="/beta-notice" className="hover:text-zinc-400">{t("legal.betaNotice")}</a>
        </p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="mb-8 lg:hidden flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 glow-brand">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <p className="text-lg font-bold tracking-tight">{t("app.name")} <span className="text-brand-400">OS</span></p>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-50">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-zinc-400">{subtitle}</p>}
          {children}
          {footer}
        </div>
      </div>
    </div>
  );
}

export const inputClass =
  "w-full rounded-lg border border-white/10 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-100 outline-none transition-all placeholder:text-zinc-600 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40";
