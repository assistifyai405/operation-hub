import { useMemo } from "react";
import {
  ArrowRight,
  Bot,
  BrainCircuit,
  BriefcaseBusiness,
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
  X,
  Zap,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLocale } from "@/context/LocaleContext";
import MarketingShell from "@/components/marketing/MarketingShell";
import CtaButton from "@/components/marketing/CtaButton";
import JsonLd from "@/components/marketing/JsonLd";
import { DashboardMock } from "@/components/marketing/ProductFrame";
import SectionHeading from "@/components/marketing/SectionHeading";
import SeoHead from "@/components/marketing/SeoHead";
import { marketingEvents } from "@/pages/marketing/marketingAnalytics";

const pillars = [
  ["unified", BriefcaseBusiness],
  ["ai", Sparkles],
  ["control", ShieldCheck],
  ["focus", Zap],
];

const steps = ["connect", "understand", "move"];

const modules = [
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

const useCases = [
  ["freelancer", "/solutions#freelancers"],
  ["agency", "/solutions#agencies"],
  ["smallBusiness", "/solutions#small-business"],
];

export default function HomePage() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const structuredData = useMemo(() => ({
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "Assistify",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    description: t("marketing.seo.homeDescription"),
    inLanguage: locale,
  }), [locale, t]);

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

      <div data-testid="marketing-home">
        <section
          className="relative isolate overflow-hidden border-b border-white/10"
          data-testid="marketing-hero"
        >
          <div className="absolute inset-0 -z-20 grid-bg opacity-80" aria-hidden="true" />
          <div className="absolute left-1/2 top-0 -z-10 h-[520px] w-[760px] -translate-x-1/2 rounded-full bg-brand-700/20 blur-[120px]" aria-hidden="true" />
          <div className="mx-auto grid max-w-7xl items-center gap-14 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-[0.9fr_1.1fr] lg:px-8 lg:py-32">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border border-brand-500/20 bg-brand-500/10 px-3 py-1 text-xs font-semibold text-brand-300">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                {t("marketing.hero.eyebrow")}
              </p>
              <h1 className="mt-6 max-w-3xl text-5xl font-bold leading-[1.05] tracking-[-0.04em] text-white sm:text-6xl lg:text-7xl">
                {t("marketing.hero.headline")}
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-8 text-zinc-300">
                {t("marketing.hero.body")}
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <CtaButton
                  to="/register"
                  showArrow
                  onClick={() => {
                    trackHero("primary", "/register");
                    trackRegister("hero");
                  }}
                  className="sm:px-6"
                >
                  {t("marketing.hero.primary")}
                </CtaButton>
                <CtaButton
                  to="/#how-it-works"
                  variant="secondary"
                  onClick={() => trackHero("secondary", "#how-it-works")}
                  className="sm:px-6"
                >
                  {t("marketing.hero.secondary")}
                </CtaButton>
              </div>
            </div>
            <div className="relative lg:pl-4">
              <div className="absolute -inset-4 rounded-[2rem] bg-brand-500/10 blur-3xl" aria-hidden="true" />
              <DashboardMock t={t} />
            </div>
          </div>
        </section>

        <section className="border-b border-white/10 bg-zinc-950/50 py-20 sm:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.pillars.eyebrow")}
              title={t("marketing.pillars.title")}
              body={t("marketing.pillars.body")}
            />
            <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
              {pillars.map(([key, Icon]) => (
                <article key={key} className="bg-zinc-950 p-6 sm:p-7">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-brand-500/20 bg-brand-500/10 text-brand-300">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <h3 className="mt-5 text-lg font-semibold text-white">{t(`marketing.pillars.items.${key}.title`)}</h3>
                  <p className="mt-2 text-sm leading-6 text-zinc-400">{t(`marketing.pillars.items.${key}.body`)}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="scroll-mt-24 py-20 sm:py-28">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.howItWorks.eyebrow")}
              title={t("marketing.howItWorks.title")}
              body={t("marketing.howItWorks.body")}
            />
            <div className="relative mt-14">
              <div className="absolute left-[16.6%] right-[16.6%] top-7 hidden h-px bg-gradient-to-r from-brand-700/20 via-brand-400/60 to-brand-700/20 lg:block" aria-hidden="true" />
              <ol className="relative grid gap-6 lg:grid-cols-3">
                {steps.map((key, index) => (
                  <li key={key} className="relative rounded-2xl border border-white/10 bg-zinc-950 p-7">
                    <span className="relative z-10 flex h-14 w-14 items-center justify-center rounded-2xl border border-brand-500/30 bg-black text-lg font-bold text-brand-300">
                      {index + 1}
                    </span>
                    <h3 className="mt-6 text-xl font-semibold text-white">{t(`marketing.howItWorks.steps.${key}.title`)}</h3>
                    <p className="mt-3 text-sm leading-6 text-zinc-400">{t(`marketing.howItWorks.steps.${key}.body`)}</p>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section className="border-y border-white/10 bg-zinc-950/50 py-20 sm:py-28" data-testid="marketing-modules">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.modules.eyebrow")}
              title={t("marketing.modules.title")}
              body={t("marketing.modules.body")}
            />
            <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {modules.map(([key, path, Icon]) => (
                <Link
                  key={key}
                  to={path}
                  className="group rounded-2xl border border-white/10 bg-black p-6 transition-all hover:-translate-y-0.5 hover:border-brand-500/30 hover:bg-brand-500/[0.04]"
                >
                  <div className="flex items-start justify-between gap-4">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/[0.05] text-brand-300 transition-colors group-hover:bg-brand-500/10">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </span>
                    <ArrowRight className="h-4 w-4 text-zinc-600 transition-all group-hover:translate-x-1 group-hover:text-brand-300" aria-hidden="true" />
                  </div>
                  <h3 className="mt-5 text-lg font-semibold text-white">{t(`marketing.modules.${key}.title`)}</h3>
                  <p className="mt-2 text-sm leading-6 text-zinc-400">{t(`marketing.modules.${key}.body`)}</p>
                  <span className="sr-only">
                    {t("marketing.modules.explore", { module: t(`marketing.modules.${key}.title`) })}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20 sm:py-28">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.beforeAfter.eyebrow")}
              title={t("marketing.beforeAfter.title")}
              body={t("marketing.beforeAfter.body")}
            />
            <div className="mx-auto mt-14 grid max-w-5xl gap-5 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-zinc-950 p-7">
                <h3 className="text-lg font-semibold text-zinc-300">{t("marketing.beforeAfter.beforeTitle")}</h3>
                <ul className="mt-5 space-y-4">
                  {["one", "two", "three"].map((key) => (
                    <li key={key} className="flex gap-3 text-sm leading-6 text-zinc-500">
                      <X className="mt-1 h-4 w-4 shrink-0 text-zinc-600" aria-hidden="true" />
                      {t(`marketing.beforeAfter.before.${key}`)}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl border border-brand-500/25 bg-brand-500/[0.06] p-7">
                <h3 className="text-lg font-semibold text-brand-200">{t("marketing.beforeAfter.afterTitle")}</h3>
                <ul className="mt-5 space-y-4">
                  {["one", "two", "three"].map((key) => (
                    <li key={key} className="flex gap-3 text-sm leading-6 text-zinc-300">
                      <Check className="mt-1 h-4 w-4 shrink-0 text-brand-400" aria-hidden="true" />
                      {t(`marketing.beforeAfter.after.${key}`)}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-white/10 bg-zinc-950/50 py-20 sm:py-28">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow={t("marketing.useCases.eyebrow")}
              title={t("marketing.useCases.title")}
              body={t("marketing.useCases.body")}
            />
            <div className="mt-12 grid gap-5 md:grid-cols-3">
              {useCases.map(([key, path]) => (
                <Link key={key} to={path} className="group rounded-2xl border border-white/10 bg-black p-7 hover:border-brand-500/30">
                  <h3 className="text-xl font-semibold text-white">{t(`marketing.useCases.${key}.title`)}</h3>
                  <p className="mt-3 text-sm leading-6 text-zinc-400">{t(`marketing.useCases.${key}.body`)}</p>
                  <span className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-brand-300">
                    {t("marketing.useCases.explore")}
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" aria-hidden="true" />
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20 sm:py-28">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 sm:px-6 lg:grid-cols-[0.8fr_1.2fr] lg:items-center lg:px-8">
            <div className="flex justify-center">
              <div className="relative flex h-56 w-56 items-center justify-center rounded-[3rem] border border-brand-500/20 bg-brand-500/[0.06]">
                <div className="absolute inset-8 rounded-[2rem] border border-brand-500/20" />
                <ShieldCheck className="h-20 w-20 text-brand-300" aria-hidden="true" />
              </div>
            </div>
            <div>
              <SectionHeading
                eyebrow={t("marketing.aiTrust.eyebrow")}
                title={t("marketing.aiTrust.title")}
                body={t("marketing.aiTrust.body")}
                align="left"
              />
              <ul className="mt-7 grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
                {["pointOne", "pointTwo", "pointThree"].map((key) => (
                  <li key={key} className="flex gap-2 text-sm text-zinc-300">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-brand-400" aria-hidden="true" />
                    {t(`marketing.aiTrust.${key}`)}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <section className="px-4 pb-20 sm:px-6 sm:pb-28 lg:px-8">
          <div className="relative mx-auto max-w-6xl overflow-hidden rounded-3xl border border-brand-500/20 bg-gradient-to-br from-brand-900/50 via-zinc-950 to-black px-6 py-14 text-center sm:px-12 sm:py-20">
            <div className="absolute left-1/2 top-0 h-48 w-96 -translate-x-1/2 bg-brand-500/20 blur-[100px]" aria-hidden="true" />
            <div className="relative">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-300">{t("marketing.finalCta.eyebrow")}</p>
              <h2 className="mx-auto mt-4 max-w-3xl text-3xl font-bold tracking-tight text-white sm:text-5xl">{t("marketing.finalCta.title")}</h2>
              <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-zinc-300">{t("marketing.finalCta.body")}</p>
              <CtaButton to="/register" showArrow className="mt-8 sm:px-7" onClick={() => trackRegister("final_cta")}>
                {t("marketing.finalCta.button")}
              </CtaButton>
            </div>
          </div>
        </section>
      </div>
    </MarketingShell>
  );
}
