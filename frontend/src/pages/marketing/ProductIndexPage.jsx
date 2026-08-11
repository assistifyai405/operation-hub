import { useEffect } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Bot, FileText, FolderKanban, Network, Users, Zap } from "lucide-react";
import { useTranslation } from "react-i18next";
import MarketingShell from "@/components/marketing/MarketingShell";
import SeoHead from "@/components/marketing/SeoHead";
import { track } from "@/lib/analytics";

const MODULES = [
  { slug: "copilot", icon: Bot },
  { slug: "crm", icon: Users },
  { slug: "projects", icon: FolderKanban },
  { slug: "automations", icon: Zap },
  { slug: "documents", icon: FileText },
];

export default function ProductIndexPage() {
  const { t } = useTranslation();

  useEffect(() => {
    track("product_page_opened", { product: "overview" });
  }, []);

  return (
    <MarketingShell>
      <SeoHead
        title={t("marketing.product.index.seo.title")}
        description={t("marketing.product.index.seo.description")}
        canonicalPath="/product"
      />
      <div data-testid="marketing-product-overview">
        <section className="relative overflow-hidden border-b border-white/10">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_10%,rgba(34,197,94,.18),transparent_42%)]" aria-hidden="true" />
          <div className="relative mx-auto max-w-5xl px-5 py-20 text-center sm:px-8 lg:py-28">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-brand-300">{t("marketing.product.index.eyebrow")}</p>
            <h1 className="mt-4 text-4xl font-black tracking-tight text-white sm:text-6xl">{t("marketing.product.index.title")}</h1>
            <p className="mx-auto mt-6 max-w-3xl text-lg leading-8 text-zinc-300">{t("marketing.product.index.intro")}</p>
            <Link to="/register" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white hover:bg-brand-500">
              {t("marketing.product.index.cta.button")} <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-24">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-300">{t("marketing.product.common.what")}</p>
          <h2 className="mt-3 max-w-3xl text-3xl font-bold text-white">{t("marketing.product.index.modulesTitle")}</h2>
          <p className="mt-4 max-w-3xl leading-7 text-zinc-400">{t("marketing.product.index.modulesIntro")}</p>
          <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {MODULES.map(({ slug, icon: Icon }) => (
              <Link
                key={slug}
                to={`/product/${slug}`}
                className="group rounded-2xl border border-white/10 bg-zinc-950 p-6 transition hover:border-brand-400/40 hover:bg-zinc-900"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-500/15 text-brand-300">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="mt-5 text-xl font-semibold text-white">{t(`marketing.product.details.${slug}.name`)}</h3>
                <p className="mt-3 text-sm leading-6 text-zinc-400">{t(`marketing.product.details.${slug}.summary`)}</p>
                <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-brand-300">
                  {t("marketing.product.common.learnMore")}
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" aria-hidden="true" />
                </span>
              </Link>
            ))}
          </div>
        </section>

        <section className="border-y border-white/10 bg-zinc-950/50">
          <div className="mx-auto grid max-w-7xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-2 lg:items-center lg:py-24">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-300">{t("marketing.product.common.why")}</p>
              <h2 className="mt-3 text-3xl font-bold text-white">{t("marketing.product.index.why.title")}</h2>
              <p className="mt-4 leading-7 text-zinc-400">{t("marketing.product.index.why.body")}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black p-7">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-300">{t("marketing.product.common.how")}</p>
              <h2 className="mt-3 text-2xl font-bold text-white">{t("marketing.product.index.how.title")}</h2>
              <p className="mt-4 leading-7 text-zinc-400">{t("marketing.product.index.how.body")}</p>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-5 py-16 sm:px-8 lg:py-24">
          <div className="flex flex-col gap-6 rounded-3xl border border-brand-400/20 bg-gradient-to-br from-brand-500/10 to-cyan-500/5 p-8 sm:p-10">
            <Network className="h-8 w-8 text-brand-300" aria-hidden="true" />
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-300">{t("marketing.product.common.connected")}</p>
            <h2 className="text-3xl font-bold text-white">{t("marketing.product.index.connected.title")}</h2>
            <p className="max-w-3xl leading-7 text-zinc-300">{t("marketing.product.index.connected.body")}</p>
          </div>
        </section>

        <section className="border-t border-white/10 px-5 py-20 text-center sm:px-8">
          <h2 className="text-3xl font-bold text-white">{t("marketing.product.index.cta.title")}</h2>
          <p className="mx-auto mt-4 max-w-2xl text-zinc-400">{t("marketing.product.index.cta.body")}</p>
          <Link to="/register" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white hover:bg-brand-500">
            {t("marketing.product.index.cta.button")} <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </section>
      </div>
    </MarketingShell>
  );
}
