import { useMemo, useState } from "react";
import {
  ArrowRight,
  Bot,
  BrainCircuit,
  Check,
  FileCheck2,
  FileSignature,
  FolderKanban,
  Lightbulb,
  Receipt,
  Repeat2,
  ShieldCheck,
  Sparkles,
  Target,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLocale } from "@/context/LocaleContext";
import MarketingShell from "@/components/marketing/MarketingShell";
import CtaButton from "@/components/marketing/CtaButton";
import JsonLd from "@/components/marketing/JsonLd";
import { DashboardMock, ShowcaseMock } from "@/components/marketing/ProductFrame";
import SectionHeading from "@/components/marketing/SectionHeading";
import SeoHead from "@/components/marketing/SeoHead";
import { marketingEvents } from "@/pages/marketing/marketingAnalytics";
import { BILLING_ENABLED } from "@/lib/config";

const SHOWCASE_TABS = ["crm", "projects", "copilot", "proposals", "automations", "opportunities"];
const CAPABILITY_KEYS = ["clients", "work", "proposals", "plan", "knowledge", "followups", "repetitive", "drafts"];
const AI_EXAMPLES = ["summarize", "plan", "email", "proposal", "attention", "tasks"];
const WORKFLOW_KEYS = ["freelancer", "agency", "smallBusiness"];
const MODULES = [
  ["copilot", "/product/copilot", Bot],
  ["crm", "/product/crm", Users],
  ["projects", "/product/projects", FolderKanban],
  ["agents", "/product/agents", BrainCircuit],
  ["proposals", "/product/proposals", FileCheck2],
  ["contracts", "/product/contracts", FileSignature],
  ["invoices", "/product/invoices", Receipt],
  ["automations", "/product/automations", Repeat2],
  ["knowledge", "/product/knowledge", Lightbulb],
  ["opportunities", "/product/opportunities", Target],
];
const STEPS = ["connect", "understand", "move"];
const WITHOUT_TOOLS = ["email", "spreadsheets", "ai", "tasks", "docs", "crm", "notes"];
const PLAN_KEYS = ["starter", "pro", "business"];

function asList(value) {
  return Array.isArray(value) ? value : [];
}

export default function HomePage() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const [showcaseTab, setShowcaseTab] = useState("crm");
  const pricingMode = BILLING_ENABLED ? "available" : "beta";

  const structuredData = useMemo(() => ({
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "Assistify",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    description: t("marketing.seo.homeDescription"),
    inLanguage: locale,
  }), [locale, t]);

  const faqPreview = asList(t("marketing.faq.questions", { returnObjects: true })).slice(0, 4);
  const showcaseActions = asList(t(`marketing.showcase.items.${showcaseTab}.actions`, { returnObjects: true }));
  const showcasePath = t(`marketing.showcase.items.${showcaseTab}.path`, { defaultValue: "/product" });

  const trackHero = (action, destination) => {
    marketingEvents.heroCtaClicked({ action, destination, locale });
  };

  const trackRegister = (placement) => {
    marketingEvents.registerCtaClicked({ placement, destination: "/register", locale });
  };

  return (
    <MarketingShell>
      <SeoHead
        title={t("marketing.seo.homeTitle")}
        description={t("marketing.seo.homeDescription")}
        canonicalPath="/"
      />
      <JsonLd data={structuredData} />

      <div data-testid="marketing-home" className="bg-[var(--theme-background)]">
        {/* 1 Hero */}
        <section className="relative isolate overflow-hidden border-b border-[var(--theme-border)]" data-testid="marketing-hero">
          <div className="absolute inset-0 -z-20 marketing-grid-bg opacity-90" aria-hidden="true" />
          <div className="absolute inset-0 -z-10 marketing-soft-green" aria-hidden="true" />
          <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[0.95fr_1.05fr] lg:px-8 lg:py-28">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border border-[var(--theme-brand-border)] bg-[var(--theme-brand-soft)] px-3 py-1 text-xs font-semibold text-[var(--theme-brand)]">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                {t("marketing.hero.eyebrow")}
              </p>
              <h1 className="mt-6 max-w-3xl text-4xl font-bold leading-[1.08] tracking-[-0.04em] text-[var(--theme-text-primary)] sm:text-5xl lg:text-6xl">
                {t("marketing.hero.headline")}
              </h1>
              <p className="mt-5 max-w-xl text-lg leading-8 text-[var(--theme-text-secondary)]">
                {t("marketing.hero.body")}
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <CtaButton
                  to="/register"
                  showArrow
                  data-testid="hero-cta-primary"
                  onClick={() => {
                    trackHero("primary", "/register");
                    trackRegister("hero");
                  }}
                >
                  {t("marketing.hero.primary")}
                </CtaButton>
                <CtaButton
                  to="/#product-showcase"
                  variant="secondary"
                  data-testid="hero-cta-secondary"
                  onClick={() => trackHero("secondary", "#product-showcase")}
                >
                  {t("marketing.hero.secondary")}
                </CtaButton>
              </div>
              <p className="mt-5 text-sm text-[var(--theme-text-muted)]">{t("marketing.hero.trust")}</p>
            </div>
            <div className="relative lg:pl-2">
              <DashboardMock t={t} />
            </div>
          </div>
        </section>

        {/* 2 What is Assistify */}
        <section className="border-b border-[var(--theme-border)] py-16 sm:py-20" data-testid="what-is-assistify" id="what-is-assistify">
          <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.whatIs.eyebrow")}
              title={t("marketing.whatIs.title")}
              body={t("marketing.whatIs.lead")}
            />
            <div className="mt-8 space-y-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6 shadow-soft sm:p-8">
              <p className="text-base leading-7 text-[var(--theme-text-primary)]">{t("marketing.whatIs.p1")}</p>
              <p className="text-base leading-7 text-[var(--theme-text-secondary)]">{t("marketing.whatIs.p2")}</p>
              <p className="text-base leading-7 text-[var(--theme-text-secondary)]">{t("marketing.whatIs.p3")}</p>
            </div>
          </div>
        </section>

        {/* 3 Without vs With */}
        <section className="border-b border-[var(--theme-border)] bg-[var(--theme-surface)] py-16 sm:py-20" data-testid="without-with">
          <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.withoutWith.eyebrow")}
              title={t("marketing.withoutWith.title")}
              body={t("marketing.withoutWith.body")}
            />
            <div className="mt-12 grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-background)] p-6">
                <h3 className="text-lg font-semibold text-[var(--theme-text-secondary)]">{t("marketing.withoutWith.withoutTitle")}</h3>
                <div className="mt-5 flex flex-wrap gap-2">
                  {WITHOUT_TOOLS.map((key) => (
                    <span
                      key={key}
                      className="rounded-lg border border-dashed border-[var(--theme-border-strong)] bg-[var(--theme-surface)] px-3 py-2 text-sm text-[var(--theme-text-secondary)]"
                    >
                      {t(`marketing.withoutWith.tools.${key}`)}
                    </span>
                  ))}
                </div>
                <p className="mt-5 text-sm text-[var(--theme-text-muted)]">{t("marketing.withoutWith.withoutNote")}</p>
              </div>
              <div className="rounded-2xl border border-[var(--theme-brand-border)] bg-[var(--theme-brand-soft)] p-6">
                <h3 className="text-lg font-semibold text-[var(--theme-brand)]">{t("marketing.withoutWith.withTitle")}</h3>
                <div className="mt-5 flex flex-col items-center gap-3 text-center">
                  <span className="rounded-xl bg-[var(--theme-brand)] px-4 py-2 text-sm font-bold text-white">ASSISTIFY</span>
                  <ArrowRight className="h-4 w-4 rotate-90 text-[var(--theme-brand)]" aria-hidden="true" />
                  <p className="text-sm font-medium text-[var(--theme-text-primary)]">{t("marketing.withoutWith.withModules")}</p>
                  <ArrowRight className="h-4 w-4 rotate-90 text-[var(--theme-brand)]" aria-hidden="true" />
                  <span className="rounded-xl border border-[var(--theme-brand-border)] bg-[var(--theme-surface)] px-4 py-2 text-sm font-semibold text-[var(--theme-brand)]">
                    {t("marketing.withoutWith.aiContext")}
                  </span>
                </div>
                <p className="mt-5 text-center text-sm font-medium text-[var(--theme-text-primary)]">{t("marketing.withoutWith.message")}</p>
              </div>
            </div>
          </div>
        </section>

        {/* 4 Interactive showcase */}
        <section id="product-showcase" className="scroll-mt-24 border-b border-[var(--theme-border)] py-16 sm:py-24" data-testid="product-showcase">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.showcase.eyebrow")}
              title={t("marketing.showcase.title")}
              body={t("marketing.showcase.body")}
            />
            <div className="mt-10 flex flex-wrap gap-2" role="tablist" aria-label={t("marketing.showcase.title")}>
              {SHOWCASE_TABS.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={showcaseTab === tab}
                  data-testid={`showcase-tab-${tab}`}
                  onClick={() => setShowcaseTab(tab)}
                  className={`rounded-xl px-3.5 py-2 text-sm font-semibold transition-colors ${
                    showcaseTab === tab
                      ? "bg-[var(--theme-brand)] text-white"
                      : "border border-[var(--theme-border)] bg-[var(--theme-surface)] text-[var(--theme-text-secondary)] hover:text-[var(--theme-text-primary)]"
                  }`}
                >
                  {t(`marketing.showcase.items.${tab}.label`)}
                </button>
              ))}
            </div>
            <div className="mt-8 grid gap-8 lg:grid-cols-2 lg:items-start">
              <div>
                <h3 className="text-2xl font-semibold text-[var(--theme-text-primary)]" data-testid="showcase-title">
                  {t(`marketing.showcase.items.${showcaseTab}.headline`)}
                </h3>
                <p className="mt-3 text-base leading-7 text-[var(--theme-text-secondary)]">
                  {t(`marketing.showcase.items.${showcaseTab}.summary`)}
                </p>
                <ul className="mt-6 space-y-3">
                  {showcaseActions.map((action) => (
                    <li key={action} className="flex gap-2 text-sm text-[var(--theme-text-primary)]">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--theme-brand)]" aria-hidden="true" />
                      {action}
                    </li>
                  ))}
                </ul>
                <CtaButton to={showcasePath} variant="secondary" className="mt-7" data-testid="showcase-learn-more">
                  {t("marketing.cta.learnMore")}
                </CtaButton>
              </div>
              <ShowcaseMock tab={showcaseTab} t={t} />
            </div>
          </div>
        </section>

        {/* 5 How it works */}
        <section id="how-it-works" className="scroll-mt-24 border-b border-[var(--theme-border)] bg-[var(--theme-surface)] py-16 sm:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.howItWorks.eyebrow")}
              title={t("marketing.howItWorks.title")}
              body={t("marketing.howItWorks.body")}
            />
            <ol className="mt-12 grid gap-5 lg:grid-cols-3">
              {STEPS.map((key, index) => (
                <li key={key} className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-background)] p-7 shadow-soft">
                  <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--theme-brand-soft)] text-lg font-bold text-[var(--theme-brand)]">
                    {index + 1}
                  </span>
                  <h3 className="mt-5 text-xl font-semibold text-[var(--theme-text-primary)]">{t(`marketing.howItWorks.steps.${key}.title`)}</h3>
                  <p className="mt-3 text-sm leading-6 text-[var(--theme-text-secondary)]">{t(`marketing.howItWorks.steps.${key}.body`)}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* 6 AI context */}
        <section className="border-b border-[var(--theme-border)] py-16 sm:py-24" data-testid="ai-context">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.aiContext.eyebrow")}
              title={t("marketing.aiContext.title")}
              body={t("marketing.aiContext.body")}
            />
            <div className="mt-12 grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6">
                <h3 className="text-lg font-semibold text-[var(--theme-text-secondary)]">{t("marketing.aiContext.genericTitle")}</h3>
                <p className="mt-3 text-sm leading-6 text-[var(--theme-text-muted)]">{t("marketing.aiContext.genericBody")}</p>
              </div>
              <div className="rounded-2xl border border-[var(--theme-brand-border)] bg-[var(--theme-brand-soft)] p-6">
                <h3 className="text-lg font-semibold text-[var(--theme-brand)]">{t("marketing.aiContext.assistifyTitle")}</h3>
                <ul className="mt-4 space-y-2">
                  {["clients", "projects", "tasks", "knowledge", "business"].map((key) => (
                    <li key={key} className="flex gap-2 text-sm text-[var(--theme-text-primary)]">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--theme-brand)]" aria-hidden="true" />
                      {t(`marketing.aiContext.sources.${key}`)}
                    </li>
                  ))}
                </ul>
                <p className="mt-4 text-xs leading-5 text-[var(--theme-text-secondary)]">{t("marketing.aiContext.caveat")}</p>
              </div>
            </div>
            <div className="mt-10">
              <h3 className="text-center text-lg font-semibold text-[var(--theme-text-primary)]">{t("marketing.aiExamples.title")}</h3>
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                {AI_EXAMPLES.map((key) => (
                  <span
                    key={key}
                    className="rounded-full border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-2 text-sm text-[var(--theme-text-primary)] shadow-soft"
                  >
                    “{t(`marketing.aiExamples.items.${key}`)}”
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* 7 Capabilities */}
        <section className="border-b border-[var(--theme-border)] bg-[var(--theme-surface)] py-16 sm:py-24" data-testid="capabilities">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.capabilities.eyebrow")}
              title={t("marketing.capabilities.title")}
              body={t("marketing.capabilities.body")}
            />
            <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {CAPABILITY_KEYS.map((key) => (
                <Link
                  key={key}
                  to={t(`marketing.capabilities.items.${key}.path`)}
                  className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-background)] p-5 transition-colors hover:border-[var(--theme-brand-border)]"
                >
                  <h3 className="text-base font-semibold text-[var(--theme-text-primary)]">{t(`marketing.capabilities.items.${key}.title`)}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--theme-text-secondary)]">{t(`marketing.capabilities.items.${key}.body`)}</p>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* 8 Use cases / workflows */}
        <section className="border-b border-[var(--theme-border)] py-16 sm:py-24" data-testid="use-case-workflows">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.workflows.eyebrow")}
              title={t("marketing.workflows.title")}
              body={t("marketing.workflows.body")}
            />
            <div className="mt-12 grid gap-5 lg:grid-cols-3">
              {WORKFLOW_KEYS.map((key) => {
                const steps = asList(t(`marketing.workflows.${key}.steps`, { returnObjects: true }));
                return (
                  <article key={key} className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6 shadow-soft">
                    <h3 className="text-xl font-semibold text-[var(--theme-text-primary)]">{t(`marketing.workflows.${key}.title`)}</h3>
                    <p className="mt-2 text-sm text-[var(--theme-text-secondary)]">{t(`marketing.workflows.${key}.body`)}</p>
                    <ol className="mt-5 space-y-2">
                      {steps.map((step, idx) => (
                        <li key={step} className="flex items-center gap-2 text-sm text-[var(--theme-text-primary)]">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--theme-brand-soft)] text-[11px] font-bold text-[var(--theme-brand)]">{idx + 1}</span>
                          {step}
                          {idx < steps.length - 1 ? <ArrowRight className="ml-auto h-3.5 w-3.5 text-[var(--theme-text-muted)]" aria-hidden="true" /> : null}
                        </li>
                      ))}
                    </ol>
                    <Link to={`/solutions#${key === "smallBusiness" ? "small-business" : `${key}s`}`} className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-[var(--theme-brand)]">
                      {t("marketing.useCases.explore")}
                      <ArrowRight className="h-4 w-4" aria-hidden="true" />
                    </Link>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        {/* 9 Modules */}
        <section className="border-b border-[var(--theme-border)] bg-[var(--theme-surface)] py-16 sm:py-24" data-testid="marketing-modules">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.modules.eyebrow")}
              title={t("marketing.modules.title")}
              body={t("marketing.modules.body")}
            />
            <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {MODULES.map(([key, path, Icon]) => (
                <Link
                  key={key}
                  to={path}
                  className="group rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-background)] p-6 transition-all hover:-translate-y-0.5 hover:border-[var(--theme-brand-border)] hover:shadow-soft"
                >
                  <div className="flex items-start justify-between gap-4">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--theme-brand-soft)] text-[var(--theme-brand)]">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </span>
                    <ArrowRight className="h-4 w-4 text-[var(--theme-text-muted)] transition-all group-hover:translate-x-1 group-hover:text-[var(--theme-brand)]" aria-hidden="true" />
                  </div>
                  <h3 className="mt-5 text-lg font-semibold text-[var(--theme-text-primary)]">{t(`marketing.modules.${key}.title`)}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--theme-text-secondary)]">{t(`marketing.modules.${key}.body`)}</p>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* 10 Trust */}
        <section className="border-b border-[var(--theme-border)] py-16 sm:py-24" data-testid="trust-facts">
          <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.trust.eyebrow")}
              title={t("marketing.trust.title")}
              body={t("marketing.trust.body")}
            />
            <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {["workspace", "auth", "ai", "beta", "locale", "billing"].map((key) => (
                <li key={key} className="flex gap-3 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5">
                  <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-[var(--theme-brand)]" aria-hidden="true" />
                  <span className="text-sm leading-6 text-[var(--theme-text-primary)]">{t(`marketing.trust.points.${key}`)}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* 11 Pricing preview */}
        <section className="border-b border-[var(--theme-border)] bg-[var(--theme-surface)] py-16 sm:py-24" data-testid="pricing-preview">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.pricing.eyebrow")}
              title={t(`marketing.pricing.${pricingMode}.title`)}
              body={t(`marketing.pricing.${pricingMode}.intro`)}
            />
            <div className="mt-12 grid gap-5 lg:grid-cols-3">
              {PLAN_KEYS.map((planKey) => {
                const key = `marketing.pricing.plans.${planKey}`;
                const features = asList(t(`${key}.features`, { returnObjects: true }));
                return (
                  <article key={planKey} className="flex flex-col rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-background)] p-6 shadow-soft">
                    <p className="text-sm font-semibold text-[var(--theme-brand)]">{t(`${key}.audience`)}</p>
                    <h3 className="mt-2 text-2xl font-bold text-[var(--theme-text-primary)]">{t(`${key}.name`)}</h3>
                    <p className="mt-3 text-sm leading-6 text-[var(--theme-text-secondary)]">{t(`${key}.description`)}</p>
                    <ul className="mt-5 flex-1 space-y-2">
                      {features.slice(0, 4).map((feature) => (
                        <li key={feature} className="flex gap-2 text-sm text-[var(--theme-text-primary)]">
                          <Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--theme-brand)]" aria-hidden="true" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                    <CtaButton to="/register" className="mt-6" onClick={() => trackRegister("pricing_preview")}>
                      {t(`marketing.pricing.${pricingMode}.action`)}
                    </CtaButton>
                  </article>
                );
              })}
            </div>
            <p className="mt-8 text-center text-sm text-[var(--theme-text-muted)]">{t("marketing.pricing.disclaimer")}</p>
            <div className="mt-6 text-center">
              <Link to="/pricing" className="text-sm font-semibold text-[var(--theme-brand)]">{t("marketing.cta.learnMore")}</Link>
            </div>
          </div>
        </section>

        {/* 12 FAQ preview */}
        <section className="border-b border-[var(--theme-border)] py-16 sm:py-24" data-testid="faq-preview">
          <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.faq.eyebrow")}
              title={t("marketing.faq.title")}
              body={t("marketing.faq.intro")}
            />
            <div className="mt-10 space-y-4">
              {faqPreview.map((item) => (
                <details key={item.question} className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-5 py-4">
                  <summary className="cursor-pointer list-none text-base font-semibold text-[var(--theme-text-primary)]">{item.question}</summary>
                  <p className="mt-3 text-sm leading-6 text-[var(--theme-text-secondary)]">{item.answer}</p>
                </details>
              ))}
            </div>
            <div className="mt-8 text-center">
              <CtaButton to="/faq" variant="secondary">{t("marketing.cta.learnMore")}</CtaButton>
            </div>
          </div>
        </section>

        {/* 13 Final CTA */}
        <section className="px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
          <div className="relative mx-auto max-w-5xl overflow-hidden rounded-3xl border border-[var(--theme-brand-border)] bg-[var(--theme-surface)] px-6 py-14 text-center shadow-brand-soft sm:px-12">
            <div className="absolute inset-0 marketing-soft-green opacity-70" aria-hidden="true" />
            <div className="relative">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--theme-brand)]">{t("marketing.finalCta.eyebrow")}</p>
              <h2 className="mx-auto mt-4 max-w-3xl text-3xl font-bold tracking-tight text-[var(--theme-text-primary)] sm:text-4xl">{t("marketing.finalCta.title")}</h2>
              <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-[var(--theme-text-secondary)]">{t("marketing.finalCta.body")}</p>
              <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <CtaButton to="/register" showArrow onClick={() => trackRegister("final_cta")}>
                  {t("marketing.finalCta.button")}
                </CtaButton>
                <CtaButton to="/#product-showcase" variant="secondary">
                  {t("marketing.hero.secondary")}
                </CtaButton>
              </div>
            </div>
          </div>
        </section>
      </div>
    </MarketingShell>
  );
}
