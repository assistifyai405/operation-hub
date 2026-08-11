import { useEffect, useRef, useState } from "react";
import { ChevronDown, Menu, Sparkles, X } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { publicConfigApi } from "@/lib/api";
import { BETA_MODE_BUILD } from "@/lib/config";
import { marketingEvents } from "@/pages/marketing/marketingAnalytics";
import CtaButton from "@/components/marketing/CtaButton";

let publicConfigRequest;

function getPublicConfigOnce() {
  if (!publicConfigRequest) publicConfigRequest = publicConfigApi.get();
  return publicConfigRequest;
}

function Brand() {
  return (
    <Link to="/" className="inline-flex items-center gap-2 text-base font-bold tracking-tight text-white">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 shadow-brand">
        <Sparkles className="h-4 w-4 text-white" aria-hidden="true" />
      </span>
      <span>Assistify</span>
    </Link>
  );
}

function LanguageSwitcher({ locale, setLocale, testIdPrefix = "marketing-lang" }) {
  return (
    <div className="inline-flex rounded-lg border border-white/10 bg-black/30 p-0.5" aria-label="Language">
      {["nl", "en"].map((language) => (
        <button
          key={language}
          type="button"
          onClick={() => setLocale(language)}
          aria-pressed={locale === language}
          data-testid={`${testIdPrefix}-${language}`}
          className={`rounded-md px-2.5 py-1.5 text-xs font-semibold uppercase transition-colors ${
            locale === language ? "bg-brand-600 text-white" : "text-zinc-400 hover:text-white"
          }`}
        >
          {language}
        </button>
      ))}
    </div>
  );
}

const productLinks = [
  ["copilot", "/product/copilot"],
  ["crm", "/product/crm"],
  ["projects", "/product/projects"],
  ["automations", "/product/automations"],
];

export default function MarketingShell({ children }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { locale, setLocale } = useLocale();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [betaMode, setBetaMode] = useState(BETA_MODE_BUILD);
  const lastTrackedPath = useRef(null);
  const authenticated = Boolean(user && typeof user === "object");
  const primaryPath = authenticated ? "/dashboard" : "/register";
  const primaryLabel = authenticated ? t("marketing.cta.openAssistify") : t("marketing.cta.getStarted");

  useEffect(() => {
    if (lastTrackedPath.current === location.pathname) return;
    lastTrackedPath.current = location.pathname;
    marketingEvents.pageView(location.pathname);
  }, [location.pathname]);

  useEffect(() => {
    let active = true;
    getPublicConfigOnce()
      .then((config) => {
        if (active) setBetaMode(BETA_MODE_BUILD || config?.betaMode === true);
      })
      .catch(() => {
        // The build-time flag remains the safe fallback.
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const closeMobile = () => setMobileOpen(false);

  return (
    <div className="min-h-screen overflow-x-hidden bg-black text-zinc-100">
      <header
        className="sticky top-0 z-50 border-b border-white/10 bg-black/80 backdrop-blur-xl"
        data-testid="marketing-nav"
      >
        <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8" aria-label="Main navigation">
          <div className="flex items-center gap-3">
            <Brand />
            {betaMode ? (
              <span className="rounded-full border border-brand-500/30 bg-brand-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-brand-300">
                {t("marketing.betaBanner")}
              </span>
            ) : null}
          </div>

          <div className="hidden items-center gap-1 lg:flex">
            <details className="group relative">
              <summary className="flex cursor-pointer list-none items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/[0.05] hover:text-white">
                {t("marketing.nav.product")}
                <ChevronDown className="h-3.5 w-3.5 transition-transform group-open:rotate-180" aria-hidden="true" />
              </summary>
              <div className="absolute left-0 top-full mt-2 w-64 rounded-xl border border-white/10 bg-zinc-950 p-2 shadow-2xl">
                {productLinks.map(([key, path]) => (
                  <Link
                    key={key}
                    to={path}
                    className="block rounded-lg px-3 py-2.5 transition-colors hover:bg-white/[0.06]"
                  >
                    <span className="block text-sm font-medium text-zinc-100">
                      {t(`marketing.modules.${key}.title`)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-zinc-500">
                      {t(`marketing.modules.${key}.body`)}
                    </span>
                  </Link>
                ))}
              </div>
            </details>
            <Link to="/pricing" className="rounded-lg px-3 py-2 text-sm font-medium text-zinc-300 hover:bg-white/[0.05] hover:text-white">
              {t("marketing.nav.pricing")}
            </Link>
            <Link to="/security" className="rounded-lg px-3 py-2 text-sm font-medium text-zinc-300 hover:bg-white/[0.05] hover:text-white">
              {t("marketing.nav.security")}
            </Link>
            <Link to="/faq" className="rounded-lg px-3 py-2 text-sm font-medium text-zinc-300 hover:bg-white/[0.05] hover:text-white">
              {t("marketing.nav.faq")}
            </Link>
          </div>

          <div className="hidden items-center gap-2 lg:flex">
            <LanguageSwitcher locale={locale} setLocale={setLocale} />
            {!authenticated ? (
              <CtaButton to="/login" variant="ghost" data-testid="marketing-cta-login">
                {t("marketing.cta.login")}
              </CtaButton>
            ) : null}
            <CtaButton to={primaryPath} data-testid="marketing-cta-primary">
              {primaryLabel}
            </CtaButton>
          </div>

          <button
            type="button"
            className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 text-zinc-200 hover:bg-white/[0.06] lg:hidden"
            onClick={() => setMobileOpen((open) => !open)}
            aria-expanded={mobileOpen}
            aria-controls="marketing-mobile-menu"
            aria-label={t(mobileOpen ? "marketing.nav.menuClose" : "marketing.nav.menuOpen")}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </nav>

        {mobileOpen ? (
          <div id="marketing-mobile-menu" className="border-t border-white/10 bg-zinc-950 px-4 py-5 lg:hidden">
            <div className="mx-auto max-w-7xl space-y-1">
              <p className="px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                {t("marketing.nav.product")}
              </p>
              {productLinks.map(([key, path]) => (
                <Link key={key} to={path} onClick={closeMobile} className="block rounded-lg px-3 py-2 text-sm text-zinc-200 hover:bg-white/[0.06]">
                  {t(`marketing.modules.${key}.title`)}
                </Link>
              ))}
              {[
                ["marketing.nav.pricing", "/pricing"],
                ["marketing.nav.security", "/security"],
                ["marketing.nav.faq", "/faq"],
              ].map(([key, path]) => (
                <Link key={path} to={path} onClick={closeMobile} className="block rounded-lg px-3 py-2 text-sm text-zinc-200 hover:bg-white/[0.06]">
                  {t(key)}
                </Link>
              ))}
              <div className="flex flex-wrap items-center gap-2 border-t border-white/10 pt-4">
                <LanguageSwitcher locale={locale} setLocale={setLocale} testIdPrefix="marketing-mobile-lang" />
                {!authenticated ? (
                  <CtaButton to="/login" variant="secondary" onClick={closeMobile}>
                    {t("marketing.cta.login")}
                  </CtaButton>
                ) : null}
                <CtaButton to={primaryPath} onClick={closeMobile}>
                  {primaryLabel}
                </CtaButton>
              </div>
            </div>
          </div>
        ) : null}
      </header>

      <main>{children}</main>

      <footer className="border-t border-white/10 bg-zinc-950/70" data-testid="marketing-footer">
        <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
          <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.4fr_repeat(4,1fr)]">
            <div>
              <Brand />
              <p className="mt-4 max-w-xs text-sm leading-6 text-zinc-500">{t("marketing.footer.tagline")}</p>
            </div>
            {[
              {
                title: "marketing.footer.company",
                links: [
                  ["marketing.footer.solutions", "/solutions"],
                  ["marketing.footer.security", "/security"],
                  ["marketing.footer.faq", "/faq"],
                ],
              },
              {
                title: "marketing.footer.product",
                links: [
                  ["marketing.nav.copilot", "/product/copilot"],
                  ["marketing.nav.crm", "/product/crm"],
                  ["marketing.nav.projects", "/product/projects"],
                  ["marketing.nav.automations", "/product/automations"],
                  ["marketing.footer.documents", "/product/documents"],
                ],
              },
              {
                title: "marketing.footer.legal",
                links: [
                  ["marketing.footer.privacy", "/privacy"],
                  ["marketing.footer.terms", "/terms"],
                  ["marketing.footer.betaNotice", "/beta-notice"],
                ],
              },
              {
                title: "marketing.footer.account",
                links: authenticated
                  ? [["marketing.footer.dashboard", "/dashboard"]]
                  : [
                    ["marketing.footer.login", "/login"],
                    ["marketing.footer.register", "/register"],
                  ],
              },
            ].map((group) => (
              <div key={group.title}>
                <p className="text-sm font-semibold text-zinc-200">{t(group.title)}</p>
                <ul className="mt-4 space-y-3">
                  {group.links.map(([label, path]) => (
                    <li key={path}>
                      <Link to={path} className="text-sm text-zinc-500 transition-colors hover:text-brand-300">
                        {t(label)}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="mt-12 flex flex-col gap-4 border-t border-white/10 pt-6 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-zinc-600">{t("marketing.footer.copyright", { year: new Date().getFullYear() })}</p>
            <div className="flex items-center gap-3">
              <span className="text-xs text-zinc-500">{t("marketing.footer.language")}</span>
              <LanguageSwitcher locale={locale} setLocale={setLocale} testIdPrefix="marketing-footer-lang" />
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
