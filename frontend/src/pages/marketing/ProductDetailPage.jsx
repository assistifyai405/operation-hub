import { useEffect } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import {
  ArrowRight,
  Bot,
  Check,
  FileText,
  FolderKanban,
  Network,
  Users,
  Zap,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import MarketingShell from "@/components/marketing/MarketingShell";
import ProductFrame from "@/components/marketing/ProductFrame";
import SeoHead from "@/components/marketing/SeoHead";
import { track } from "@/lib/analytics";

const PRODUCT_META = {
  copilot: { icon: Bot, accent: "from-brand-500/25 to-cyan-500/10" },
  crm: { icon: Users, accent: "from-cyan-500/20 to-brand-500/10" },
  projects: { icon: FolderKanban, accent: "from-emerald-500/20 to-brand-500/10" },
  automations: { icon: Zap, accent: "from-amber-500/20 to-brand-500/10" },
  documents: { icon: FileText, accent: "from-blue-500/20 to-brand-500/10" },
  agents: { icon: Bot, accent: "from-brand-500/20 to-emerald-500/10" },
  knowledge: { icon: Network, accent: "from-cyan-500/20 to-brand-500/10" },
  opportunities: { icon: Zap, accent: "from-amber-500/15 to-brand-500/10" },
};

function translatedList(t, key) {
  const value = t(key, { returnObjects: true });
  return Array.isArray(value) ? value : [];
}

export default function ProductDetailPage({ slug: explicitSlug }) {
  const params = useParams();
  const slug = explicitSlug || params.slug;
  const meta = PRODUCT_META[slug];
  const { t } = useTranslation();

  useEffect(() => {
    if (meta) track("product_page_opened", { product: slug });
  }, [meta, slug]);

  if (!meta) return <Navigate to="/product" replace />;

  const key = `marketing.product.details.${slug}`;
  const Icon = meta.icon;
  const steps = translatedList(t, `${key}.how.steps`);
  const capabilities = translatedList(t, `${key}.capabilities.items`);

  return (
    <MarketingShell>
      <SeoHead
        title={t(`${key}.seo.title`)}
        description={t(`${key}.seo.description`)}
        canonicalPath={`/product/${slug}`}
      />
      <div data-testid={`marketing-product-${slug}`}>
        <section className="relative overflow-hidden border-b border-[var(--theme-border)]">
          <div className={`absolute inset-0 bg-gradient-to-br ${meta.accent}`} aria-hidden="true" />
          <div className="relative mx-auto grid max-w-7xl gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:py-28">
            <div>
              <Link to="/product" className="text-sm font-medium text-[var(--theme-brand)] hover:text-[var(--theme-brand)]">
                ← {t("marketing.product.common.allProducts")}
              </Link>
              <div className="mt-8 flex h-12 w-12 items-center justify-center rounded-2xl border border-[var(--theme-brand-border)] bg-brand-500/15 text-[var(--theme-brand)]">
                <Icon className="h-6 w-6" aria-hidden="true" />
              </div>
              <p className="mt-6 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--theme-brand)]">
                {t(`${key}.eyebrow`)}
              </p>
              <h1 className="mt-3 max-w-3xl text-4xl font-black tracking-tight text-[var(--theme-text-primary)] sm:text-6xl">
                {t(`${key}.title`)}
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-[var(--theme-text-secondary)]">
                {t(`${key}.intro`)}
              </p>
              <Link to="/register" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-[var(--theme-text-primary)] hover:bg-brand-500">
                {t(`${key}.cta.button`)} <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>

            <ProductFrame
              title={t(`${key}.frame.title`)}
              subtitle={t(`${key}.frame.subtitle`)}
              alt={t(`${key}.frame.alt`)}
            >
              <div className="space-y-3">
                {capabilities.slice(0, 3).map((item, index) => (
                  <div key={item} className="flex items-start gap-3 rounded-xl border border-[var(--theme-border)] bg-zinc-900/80 p-3.5">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-500/15 text-xs font-bold text-[var(--theme-brand)]">
                      {index + 1}
                    </span>
                    <p className="text-sm leading-6 text-[var(--theme-text-secondary)]">{item}</p>
                  </div>
                ))}
              </div>
            </ProductFrame>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-6 px-5 py-16 sm:px-8 lg:grid-cols-2 lg:py-24">
          <article className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-7">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--theme-brand)]">{t("marketing.product.common.what")}</p>
            <h2 className="mt-3 text-2xl font-bold text-[var(--theme-text-primary)]">{t(`${key}.what.title`)}</h2>
            <p className="mt-4 leading-7 text-[var(--theme-text-secondary)]">{t(`${key}.what.body`)}</p>
          </article>
          <article className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-7">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--theme-brand)]">{t("marketing.product.common.why")}</p>
            <h2 className="mt-3 text-2xl font-bold text-[var(--theme-text-primary)]">{t(`${key}.why.title`)}</h2>
            <p className="mt-4 leading-7 text-[var(--theme-text-secondary)]">{t(`${key}.why.body`)}</p>
          </article>
        </section>

        <section className="border-y border-[var(--theme-border)] bg-[var(--theme-surface)]/50">
          <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-24">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--theme-brand)]">{t("marketing.product.common.how")}</p>
            <h2 className="mt-3 text-3xl font-bold text-[var(--theme-text-primary)]">{t(`${key}.how.title`)}</h2>
            <div className="mt-9 grid gap-5 md:grid-cols-3">
              {steps.map((step, index) => (
                <article key={step.title} className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-background)] p-6">
                  <span className="text-sm font-bold text-[var(--theme-brand)]">0{index + 1}</span>
                  <h3 className="mt-4 text-lg font-semibold text-[var(--theme-text-primary)]">{step.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-[var(--theme-text-secondary)]">{step.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-12 px-5 py-16 sm:px-8 lg:grid-cols-[.9fr_1.1fr] lg:py-24">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--theme-brand)]">{t("marketing.product.common.capabilities")}</p>
            <h2 className="mt-3 text-3xl font-bold text-[var(--theme-text-primary)]">{t(`${key}.capabilities.title`)}</h2>
            <p className="mt-4 leading-7 text-[var(--theme-text-secondary)]">{t(`${key}.capabilities.intro`)}</p>
            {slug === "documents" ? (
              <p className="mt-6 rounded-xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-6 text-amber-100">
                {t(`${key}.disclaimer`)}
              </p>
            ) : null}
          </div>
          <ul className="grid gap-3 sm:grid-cols-2">
            {capabilities.map((item) => (
              <li key={item} className="flex gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 text-sm leading-6 text-[var(--theme-text-secondary)]">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-brand-400" aria-hidden="true" />
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section className="border-y border-[var(--theme-border)] bg-gradient-to-r from-brand-950/30 via-zinc-950 to-cyan-950/20">
          <div className="mx-auto flex max-w-5xl flex-col items-start gap-6 px-5 py-14 sm:px-8 md:flex-row md:items-center">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-brand-500/15 text-[var(--theme-brand)]">
              <Network className="h-6 w-6" aria-hidden="true" />
            </span>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--theme-brand)]">{t("marketing.product.common.connected")}</p>
              <h2 className="mt-2 text-2xl font-bold text-[var(--theme-text-primary)]">{t(`${key}.connected.title`)}</h2>
              <p className="mt-3 leading-7 text-[var(--theme-text-secondary)]">{t(`${key}.connected.body`)}</p>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-4xl px-5 py-20 text-center sm:px-8 lg:py-28">
          <h2 className="text-3xl font-bold text-[var(--theme-text-primary)] sm:text-4xl">{t(`${key}.cta.title`)}</h2>
          <p className="mx-auto mt-4 max-w-2xl leading-7 text-[var(--theme-text-secondary)]">{t(`${key}.cta.body`)}</p>
          <Link to="/register" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-[var(--theme-text-primary)] hover:bg-brand-500">
            {t(`${key}.cta.button`)} <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </section>
      </div>
    </MarketingShell>
  );
}
