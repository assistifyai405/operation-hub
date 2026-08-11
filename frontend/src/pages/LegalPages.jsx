import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Trans, useTranslation } from "react-i18next";
import { Sparkles } from "lucide-react";
import { publicConfigApi } from "@/lib/api";

function LegalShell({ title, children }) {
  const { t } = useTranslation();
  return (
    <div className="min-h-screen bg-black text-zinc-100">
      <header className="border-b border-white/10 px-6 py-5">
        <Link to="/login" className="inline-flex items-center gap-2 text-sm font-semibold text-zinc-100">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
            <Sparkles className="h-4 w-4 text-white" />
          </span>
          {t("app.name")}
        </Link>
      </header>
      <main className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm text-amber-200/90" data-testid="legal-placeholder-notice">
          {t("legal.placeholderNotice")}
        </p>
        <div className="prose prose-invert mt-8 max-w-none space-y-4 text-sm leading-relaxed text-zinc-300">
          {children}
        </div>
        <p className="mt-10 text-xs text-zinc-600">
          <Link to="/privacy" className="underline hover:text-zinc-400">{t("legal.privacy")}</Link>
          {" · "}
          <Link to="/terms" className="underline hover:text-zinc-400">{t("legal.terms")}</Link>
          {" · "}
          <Link to="/beta-notice" className="underline hover:text-zinc-400">{t("legal.betaNotice")}</Link>
        </p>
      </main>
    </div>
  );
}

function CompanyBlock({ legal }) {
  const { t } = useTranslation();
  const placeholders = legal?.placeholders !== false;
  const rows = [
    ["legal.fields.companyName", legal?.companyName],
    ["legal.fields.tradeName", legal?.tradeName],
    ["legal.fields.kvkNumber", legal?.kvkNumber],
    ["legal.fields.vatNumber", legal?.vatNumber],
    ["legal.fields.contactEmail", legal?.contactEmail],
    ["legal.fields.privacyEmail", legal?.privacyEmail],
    ["legal.fields.address", legal?.address],
  ];
  return (
    <div className="rounded-xl border border-dashed border-white/15 bg-zinc-950/80 p-4" data-testid="legal-company-block">
      <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
        {placeholders ? t("legal.companyBlock") : t("legal.companyBlockConfigured")}
      </p>
      <dl className="mt-3 space-y-2">
        {rows.map(([labelKey, value]) => (
          <div key={labelKey} className="flex flex-col gap-0.5 sm:flex-row sm:gap-4">
            <dt className="w-48 shrink-0 text-xs text-zinc-500">{t(labelKey)}</dt>
            <dd className="text-sm text-zinc-200">{value || t("legal.toBeFilled")}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function useLegal() {
  const [legal, setLegal] = useState(null);
  useEffect(() => {
    publicConfigApi.get().then((c) => setLegal(c.legal || {})).catch(() => setLegal({ placeholders: true }));
  }, []);
  return legal;
}

export function PrivacyPage() {
  const { t } = useTranslation();
  const legal = useLegal();
  return (
    <LegalShell title={t("legal.privacy")}>
      <p>{t("legal.privacyBody")}</p>
      <p><Trans i18nKey="legal.privacyPlaceholderBody" components={{ strong: <strong /> }} /></p>
      <CompanyBlock legal={legal} />
      <p>{t("legal.privacyContact")}</p>
    </LegalShell>
  );
}

export function TermsPage() {
  const { t } = useTranslation();
  const legal = useLegal();
  return (
    <LegalShell title={t("legal.termsTitle")}>
      <p><Trans i18nKey="legal.termsPlaceholderBody" components={{ strong: <strong /> }} /></p>
      <p>{t("legal.termsBody")}</p>
      <CompanyBlock legal={legal} />
      <p>{t("legal.termsBilling")}</p>
    </LegalShell>
  );
}

export function BetaNoticePage() {
  const { t } = useTranslation();
  const legal = useLegal();
  return (
    <LegalShell title={t("legal.betaNotice")}>
      <p><Trans i18nKey="legal.betaBody" components={{ strong: <strong /> }} /></p>
      <ul className="list-disc space-y-2 pl-5">
        <li>{t("legal.betaItems.sla")}</li>
        <li>{t("legal.betaItems.ai")}</li>
        <li>{t("legal.betaItems.billing")}</li>
        <li>{t("legal.betaItems.email")}</li>
        <li><Trans i18nKey="legal.betaItems.feedback" components={{ em: <em /> }} /></li>
      </ul>
      <CompanyBlock legal={legal} />
    </LegalShell>
  );
}
