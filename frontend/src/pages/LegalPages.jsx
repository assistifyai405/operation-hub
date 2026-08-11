import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { publicConfigApi } from "@/lib/api";

function LegalShell({ title, children }) {
  return (
    <div className="min-h-screen bg-black text-zinc-100">
      <header className="border-b border-white/10 px-6 py-5">
        <Link to="/login" className="inline-flex items-center gap-2 text-sm font-semibold text-zinc-100">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600">
            <Sparkles className="h-4 w-4 text-white" />
          </span>
          Assistify
        </Link>
      </header>
      <main className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm text-amber-200/90" data-testid="legal-placeholder-notice">
          Placeholder document — not legal advice. Company details below are configuration placeholders until filled after KVK registration.
        </p>
        <div className="prose prose-invert mt-8 max-w-none space-y-4 text-sm leading-relaxed text-zinc-300">
          {children}
        </div>
        <p className="mt-10 text-xs text-zinc-600">
          <Link to="/privacy" className="underline hover:text-zinc-400">Privacy</Link>
          {" · "}
          <Link to="/terms" className="underline hover:text-zinc-400">Terms</Link>
          {" · "}
          <Link to="/beta-notice" className="underline hover:text-zinc-400">Beta notice</Link>
        </p>
      </main>
    </div>
  );
}

function CompanyBlock({ legal }) {
  const placeholders = legal?.placeholders !== false;
  const rows = [
    ["Legal / business name", legal?.companyName],
    ["Trade name", legal?.tradeName],
    ["KVK number", legal?.kvkNumber],
    ["VAT number", legal?.vatNumber],
    ["Business contact email", legal?.contactEmail],
    ["Privacy contact", legal?.privacyEmail],
    ["Business address", legal?.address],
  ];
  return (
    <div className="rounded-xl border border-dashed border-white/15 bg-zinc-950/80 p-4" data-testid="legal-company-block">
      <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
        {placeholders ? "Company information (not yet configured)" : "Company information"}
      </p>
      <dl className="mt-3 space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex flex-col gap-0.5 sm:flex-row sm:gap-4">
            <dt className="w-48 shrink-0 text-xs text-zinc-500">{label}</dt>
            <dd className="text-sm text-zinc-200">{value || "[To be filled after KVK registration]"}</dd>
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
  const legal = useLegal();
  return (
    <LegalShell title="Privacy">
      <p>
        Assistify is an AI-powered business operating system. During closed beta we process account,
        workspace, and usage data needed to operate the product for invited users.
      </p>
      <p>
        This page is a <strong>placeholder</strong>. It does not invent a legal entity, KVK number,
        VAT number, or registered address. Replace placeholders after company registration.
      </p>
      <CompanyBlock legal={legal} />
      <p>
        For privacy questions, contact the privacy email above when configured, or your beta operator.
      </p>
    </LegalShell>
  );
}

export function TermsPage() {
  const legal = useLegal();
  return (
    <LegalShell title="Terms of use">
      <p>
        These terms are a <strong>placeholder</strong> for closed beta access. They are not finalized
        legal terms and are not legal advice.
      </p>
      <p>
        Assistify helps businesses manage clients, projects, tasks, AI-assisted work,
        proposals/contracts/invoices, and day-to-day workflow. Beta access may change without notice.
      </p>
      <CompanyBlock legal={legal} />
      <p>
        Billing and paid subscriptions are not available during beta. Do not rely on this page as a
        commercial contract until replaced with counsel-reviewed terms.
      </p>
    </LegalShell>
  );
}

export function BetaNoticePage() {
  const legal = useLegal();
  return (
    <LegalShell title="Beta notice">
      <p>
        Assistify is in <strong>closed beta</strong>. Features may be incomplete, change, or break.
        Data may be reset if operators announce a migration.
      </p>
      <ul className="list-disc space-y-2 pl-5">
        <li>Not a production SLA — use for evaluation and early workflows.</li>
        <li>AI features use the operator&apos;s configured provider; outputs can be wrong.</li>
        <li>Billing / Stripe is intentionally disabled.</li>
        <li>Email delivery and OAuth may be disabled depending on configuration.</li>
        <li>Please use <em>Send feedback</em> in the product to report bugs or confusion.</li>
      </ul>
      <CompanyBlock legal={legal} />
    </LegalShell>
  );
}
