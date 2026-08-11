import { useEffect } from "react";
import { Check } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import MarketingShell from "@/components/marketing/MarketingShell";
import SeoHead from "@/components/marketing/SeoHead";
import { track } from "@/lib/analytics";
import { BILLING_ENABLED } from "@/lib/config";

const PLAN_KEYS = ["starter", "pro", "business"];

function asList(value) {
  return Array.isArray(value) ? value : [];
}

export default function PricingPage() {
  const { t } = useTranslation();
  const mode = BILLING_ENABLED ? "available" : "beta";

  useEffect(() => {
    track("pricing_viewed", { billing_enabled: BILLING_ENABLED });
  }, []);

  return (
    <MarketingShell>
      <SeoHead
        title={t("marketing.pricing.seo.title")}
        description={t("marketing.pricing.seo.description")}
        canonicalPath="/pricing"
      />
      <div data-testid="marketing-pricing">
        <section className="relative overflow-hidden border-b border-white/10">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(34,197,94,.16),transparent_42%)]" aria-hidden="true" />
          <div className="relative mx-auto max-w-4xl px-5 py-20 text-center sm:px-8 lg:py-28">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-brand-300">{t("marketing.pricing.eyebrow")}</p>
            <h1 className="mt-4 text-4xl font-black tracking-tight text-white sm:text-6xl">
              {t(`marketing.pricing.${mode}.title`)}
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-zinc-300">
              {t(`marketing.pricing.${mode}.intro`)}
            </p>
            {!BILLING_ENABLED ? (
              <p className="mx-auto mt-7 max-w-2xl rounded-xl border border-brand-400/20 bg-brand-400/10 px-5 py-4 text-sm leading-6 text-brand-100">
                {t("marketing.pricing.beta.notice")}
              </p>
            ) : null}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-24">
          <div className="grid gap-6 lg:grid-cols-3">
            {PLAN_KEYS.map((planKey) => {
              const key = `marketing.pricing.plans.${planKey}`;
              const features = asList(t(`${key}.features`, { returnObjects: true }));
              return (
                <article key={planKey} className="flex flex-col rounded-2xl border border-white/10 bg-zinc-950 p-7">
                  <p className="text-sm font-semibold text-brand-300">{t(`${key}.audience`)}</p>
                  <h2 className="mt-3 text-2xl font-bold text-white">{t(`${key}.name`)}</h2>
                  <p className="mt-3 min-h-12 text-sm leading-6 text-zinc-400">{t(`${key}.description`)}</p>
                  <p className="mt-7 border-y border-white/10 py-4 text-sm font-medium text-zinc-300">
                    {t(`marketing.pricing.${mode}.planStatus`)}
                  </p>
                  <ul className="mt-6 flex-1 space-y-3">
                    {features.map((feature) => (
                      <li key={feature} className="flex gap-3 text-sm leading-6 text-zinc-300">
                        <Check className="mt-1 h-4 w-4 shrink-0 text-brand-400" aria-hidden="true" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <Link
                    to="/register"
                    className="mt-8 block rounded-xl border border-brand-400/30 bg-brand-500/10 px-4 py-3 text-center text-sm font-semibold text-brand-200 hover:bg-brand-500/20"
                  >
                    {t(`marketing.pricing.${mode}.action`)}
                  </Link>
                </article>
              );
            })}
          </div>
          <p className="mx-auto mt-10 max-w-3xl text-center text-sm leading-6 text-zinc-500">
            {t("marketing.pricing.disclaimer")}
          </p>
        </section>
      </div>
    </MarketingShell>
  );
}
