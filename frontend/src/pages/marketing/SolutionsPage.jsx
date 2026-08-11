import { ArrowRight, BriefcaseBusiness, Building2, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import MarketingShell from "@/components/marketing/MarketingShell";
import SeoHead from "@/components/marketing/SeoHead";

const AUDIENCES = [
  { key: "freelancers", icon: BriefcaseBusiness },
  { key: "agencies", icon: Users },
  { key: "smallBusinesses", icon: Building2 },
];

export default function SolutionsPage() {
  const { t } = useTranslation();

  return (
    <MarketingShell>
      <SeoHead
        title={t("marketing.solutions.seo.title")}
        description={t("marketing.solutions.seo.description")}
        canonicalPath="/solutions"
      />
      <div data-testid="marketing-solutions">
        <section className="relative overflow-hidden border-b border-[var(--theme-border)]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(34,197,94,.16),transparent_44%)]" aria-hidden="true" />
          <div className="relative mx-auto max-w-5xl px-5 py-20 text-center sm:px-8 lg:py-28">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--theme-brand)]">{t("marketing.solutions.eyebrow")}</p>
            <h1 className="mt-4 text-4xl font-black tracking-tight text-[var(--theme-text-primary)] sm:text-6xl">{t("marketing.solutions.title")}</h1>
            <p className="mx-auto mt-6 max-w-3xl text-lg leading-8 text-[var(--theme-text-secondary)]">{t("marketing.solutions.intro")}</p>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-24">
          <div className="grid gap-6 lg:grid-cols-3">
            {AUDIENCES.map(({ key, icon: Icon }) => {
              const useCases = t(`marketing.solutions.audiences.${key}.useCases`, { returnObjects: true });
              return (
                <article key={key} className="flex flex-col rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-7">
                  <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-500/15 text-[var(--theme-brand)]">
                    <Icon className="h-6 w-6" aria-hidden="true" />
                  </span>
                  <h2 className="mt-6 text-2xl font-bold text-[var(--theme-text-primary)]">{t(`marketing.solutions.audiences.${key}.title`)}</h2>
                  <p className="mt-3 text-sm leading-6 text-[var(--theme-text-secondary)]">{t(`marketing.solutions.audiences.${key}.body`)}</p>
                  <h3 className="mt-7 text-xs font-bold uppercase tracking-[0.14em] text-[var(--theme-brand)]">{t("marketing.solutions.useCases")}</h3>
                  <ul className="mt-4 space-y-3">
                    {(Array.isArray(useCases) ? useCases : []).map((useCase) => (
                      <li key={useCase} className="border-l-2 border-brand-500/40 pl-3 text-sm leading-6 text-[var(--theme-text-secondary)]">
                        {useCase}
                      </li>
                    ))}
                  </ul>
                </article>
              );
            })}
          </div>
        </section>

        <section className="border-y border-[var(--theme-border)] bg-[var(--theme-surface)]/50">
          <div className="mx-auto max-w-5xl px-5 py-16 text-center sm:px-8 lg:py-20">
            <h2 className="text-3xl font-bold text-[var(--theme-text-primary)]">{t("marketing.solutions.workflow.title")}</h2>
            <p className="mx-auto mt-4 max-w-3xl leading-7 text-[var(--theme-text-secondary)]">{t("marketing.solutions.workflow.body")}</p>
          </div>
        </section>

        <section className="mx-auto max-w-4xl px-5 py-20 text-center sm:px-8 lg:py-28">
          <h2 className="text-3xl font-bold text-[var(--theme-text-primary)]">{t("marketing.solutions.cta.title")}</h2>
          <p className="mx-auto mt-4 max-w-2xl leading-7 text-[var(--theme-text-secondary)]">{t("marketing.solutions.cta.body")}</p>
          <Link to="/register" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-[var(--theme-text-primary)] hover:bg-brand-500">
            {t("marketing.solutions.cta.button")} <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </section>
      </div>
    </MarketingShell>
  );
}
