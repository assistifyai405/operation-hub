import {
  Activity,
  Bot,
  Cookie,
  KeyRound,
  LockKeyhole,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import MarketingShell from "@/components/marketing/MarketingShell";
import SeoHead from "@/components/marketing/SeoHead";

const PRACTICES = [
  { key: "cookies", icon: Cookie },
  { key: "csrf", icon: ShieldCheck },
  { key: "isolation", icon: UsersRound },
  { key: "tokens", icon: LockKeyhole },
  { key: "secrets", icon: KeyRound },
  { key: "ai", icon: Bot },
  { key: "monitoring", icon: Activity },
];

export default function SecurityPage() {
  const { t } = useTranslation();

  return (
    <MarketingShell>
      <SeoHead
        title={t("marketing.security.seo.title")}
        description={t("marketing.security.seo.description")}
        canonicalPath="/security"
      />
      <div data-testid="marketing-security">
        <section className="relative overflow-hidden border-b border-[var(--theme-border)]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(34,197,94,.15),transparent_45%)]" aria-hidden="true" />
          <div className="relative mx-auto max-w-4xl px-5 py-20 text-center sm:px-8 lg:py-28">
            <ShieldCheck className="mx-auto h-11 w-11 text-[var(--theme-brand)]" aria-hidden="true" />
            <p className="mt-6 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--theme-brand)]">{t("marketing.security.eyebrow")}</p>
            <h1 className="mt-4 text-4xl font-black tracking-tight text-[var(--theme-text-primary)] sm:text-6xl">{t("marketing.security.title")}</h1>
            <p className="mx-auto mt-6 max-w-3xl text-lg leading-8 text-[var(--theme-text-secondary)]">{t("marketing.security.intro")}</p>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-24">
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {PRACTICES.map(({ key, icon: Icon }) => (
              <article key={key} className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-500/15 text-[var(--theme-brand)]">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h2 className="mt-5 text-lg font-semibold text-[var(--theme-text-primary)]">{t(`marketing.security.practices.${key}.title`)}</h2>
                <p className="mt-3 text-sm leading-6 text-[var(--theme-text-secondary)]">{t(`marketing.security.practices.${key}.body`)}</p>
              </article>
            ))}
          </div>

          <div className="mx-auto mt-12 max-w-3xl rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-7 text-center">
            <h2 className="text-xl font-semibold text-[var(--theme-text-primary)]">{t("marketing.security.scope.title")}</h2>
            <p className="mt-3 text-sm leading-7 text-[var(--theme-text-secondary)]">{t("marketing.security.scope.body")}</p>
          </div>
        </section>
      </div>
    </MarketingShell>
  );
}
