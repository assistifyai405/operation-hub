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
    <Link to="/" className="inline-flex items-center gap-2 text-base font-bold tracking-tight text-[var(--theme-text-primary)]">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--theme-brand)] shadow-brand-soft">
        <Sparkles className="h-4 w-4 text-white" aria-hidden="true" />
      </span>
      <span>Assistify</span>
    </Link>
  );
}

function LanguageSwitcher({ locale, setLocale, testIdPrefix = "marketing-lang" }) {
  return (
    <div className="inline-flex rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-0.5" aria-label="Language">
      {["nl", "en"].map((language) => (
        <button
          key={language}
          type="button"
          onClick={() => setLocale(language)}
          aria-pressed={locale === language}
          data-testid={`${testIdPrefix}-${language}`}
          className={`rounded-md px-2.5 py-1.5 text-xs font-semibold uppercase transition-colors ${
            locale === language
              ? "bg-[var(--theme-brand)] text-white"
              : "text-[var(--theme-text-secondary)] hover:text-[var(--theme-text-primary)]"
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
    document.documentElement.setAttribute("data-theme", "light");
    return () => {
      // Leave light for other marketing routes; App shell will re-apply dark on authenticated views if needed.
    };
  }, []);

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
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const closeMobile = () => setMobileOpen(false);

  return (
    <div className="min-h-screen overflow-x-hidden bg-[var(--theme-background)] text-[var(--theme-text-primary)]" data-theme="light">
      <header
        className="sticky top-0 z-50 border-b border-[var(--theme-border)] bg-[color-mix(in_srgb,var(--theme-background)_88%,white)] backdrop-blur-xl"
        data-testid="marketing-nav"
      >
        <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8" aria-label="Main navigation">
          <div className="flex items-center gap-3">
            <Brand />
            {betaMode ? (
              <span className="rounded-full border border-[var(--theme-brand-border)] bg-[var(--theme-brand-soft)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[var(--theme-brand)]">
                {t("marketing.betaBanner")}
              </span>
            ) : null}
          </div>

          <div className="hidden items-center gap-1 lg:flex">
            <details className="group relative">
              <summary className="flex cursor-pointer list-none items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-[var(--theme-text-secondary)] transition-colors hover:bg-[var(--theme-surface-muted)] hover:text-[var(--theme-text-primary)]">
                {t("marketing.nav.product")}
                <ChevronDown className="h-3.5 w-3.5 transition-transform group-open:rotate-180" aria-hidden="true" />
              </summary>
              <div className="absolute left-0 top-full mt-2 w-64 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-2 shadow-soft">
                {productLinks.map(([key, path]) => (
                  <Link
                    key={key}
                    to={path}
                    className="block rounded-lg px-3 py-2.5 transition-colors hover:bg-[var(--theme-surface-muted)]"
                  >
                    <span className="block text-sm font-medium text-[var(--theme-text-primary)]">
                      {t(`marketing.modules.${key}.title`)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-[var(--theme-text-secondary)]">
                      {t(`marketing.modules.${key}.body`)}
                    </span>
                  </Link>
                ))}
              </div>
            </details>
            <Link to="/pricing" className="rounded-lg px-3 py-2 text-sm font-medium text-[var(--theme-text-secondary)] hover:bg-[var(--theme-surface-muted)] hover:text-[var(--theme-text-primary)]">
              {t("marketing.nav.pricing")}
            </Link>
            <Link to="/security" className="rounded-lg px-3 py-2 text-sm font-medium text-[var(--theme-text-secondary)] hover:bg-[var(--theme-surface-muted)] hover:text-[var(--theme-text-primary)]">
              {t("marketing.nav.security")}
            </Link>
            <Link to="/faq" className="rounded-lg px-3 py-2 text-sm font-medium text-[var(--theme-text-secondary)] hover:bg-[var(--theme-surface-muted)] hover:text-[var(--theme-text-primary)]">
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
            className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-[var(--theme-border)] text-[var(--theme-text-primary)] hover:bg-[var(--theme-surface-muted)] lg:hidden"
            onClick={() => setMobileOpen((open) => !open)}
            aria-expanded={mobileOpen}
            aria-controls="marketing-mobile-menu"
            aria-label={t(mobileOpen ? "marketing.nav.menuClose" : "marketing.nav.menuOpen")}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </nav>

        {mobileOpen ? (
          <div id="marketing-mobile-menu" className="border-t border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-5 lg:hidden">
            <div className="mx-auto max-w-7xl space-y-1">
              <p className="px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wider text-[var(--theme-text-muted)]">
                {t("marketing.nav.product")}
              </p>
              {productLinks.map(([key, path]) => (
                <Link key={key} to={path} onClick={closeMobile} className="block rounded-lg px-3 py-2 text-sm text-[var(--theme-text-primary)] hover:bg-[var(--theme-surface-muted)]">
                  {t(`marketing.modules.${key}.title`)}
                </Link>
              ))}
              {[
                ["marketing.nav.pricing", "/pricing"],
                ["marketing.nav.security", "/security"],
                ["marketing.nav.faq", "/faq"],
              ].map(([key, path]) => (
                <Link key={path} to={path} onClick={closeMobile} className="block rounded-lg px-3 py-2 text-sm text-[var(--theme-text-primary)] hover:bg-[var(--theme-surface-muted)]">
                  {t(key)}
                </Link>
              ))}
              <div className="flex flex-wrap items-center gap-2 border-t border-[var(--theme-border)] pt-4">
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

      <footer className="border-t border-[var(--theme-border)] bg-[var(--theme-surface)]" data-testid="marketing-footer">
        <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
          <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.4fr_repeat(4,1fr)]">
            <div>
              <Brand />
              <p className="mt-4 max-w-xs text-sm leading-6 text-[var(--theme-text-secondary)]">{t("marketing.footer.tagline")}</p>
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
                <p className="text-sm font-semibold text-[var(--theme-text-primary)]">{t(group.title)}</p>
                <ul className="mt-4 space-y-3">
                  {group.links.map(([label, path]) => (
                    <li key={path}>
                      <Link to={path} className="text-sm text-[var(--theme-text-secondary)] transition-colors hover:text-[var(--theme-brand)]">
                        {t(label)}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="mt-12 flex flex-col gap-4 border-t border-[var(--theme-border)] pt-6 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-[var(--theme-text-muted)]">{t("marketing.footer.copyright", { year: new Date().getFullYear() })}</p>
            <div className="flex items-center gap-3">
              <span className="text-xs text-[var(--theme-text-secondary)]">{t("marketing.footer.language")}</span>
              <LanguageSwitcher locale={locale} setLocale={setLocale} testIdPrefix="marketing-footer-lang" />
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
