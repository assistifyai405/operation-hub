import PageIntro from "@/components/PageIntro";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Search, Users, Loader2, Building2, ArrowRight, Clock, TrendingUp } from "lucide-react";
import { crmApi } from "@/lib/api";
import { fmtMoney } from "@/components/crm/crmShared";
import { useLocale } from "@/context/LocaleContext";
import { formatRelativeTime } from "@/i18n/format";

export default function CRM() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const navigate = useNavigate();
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [tag, setTag] = useState("");

  useEffect(() => { crmApi.contacts().then(setContacts).catch(() => setContacts([])).finally(() => setLoading(false)); }, []);

  const tags = useMemo(() => Array.from(new Set(contacts.flatMap((c) => c.tags || []))), [contacts]);
  const filtered = contacts.filter((c) => {
    const matchQ = !q || (c.name + " " + (c.contact || "") + " " + (c.email || "") + " " + (c.industry || "")).toLowerCase().includes(q.toLowerCase());
    const matchTag = !tag || (c.tags || []).includes(tag);
    return matchQ && matchTag;
  });

  return (
    <div className="space-y-5" data-testid="crm-page">
      <PageIntro title={t("pages.crm.title")} description={t("pages.crm.description")} helpModule="crm" />

      <div>
        <h1 className="flex items-center gap-2.5 text-3xl font-bold tracking-tight text-zinc-50">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 glow-brand"><Users className="h-5 w-5 text-white" /></span>
          {t("crm.title")}
        </h1>
        <p className="mt-1.5 text-sm text-zinc-400">
          {t("crm.intro")}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <input value={q} onChange={(e) => setQ(e.target.value)} data-testid="crm-search" placeholder={t("crm.search")}
            className="w-full rounded-lg border border-white/10 bg-zinc-900 py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-brand-500/50 focus:outline-none" />
        </div>
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            <button onClick={() => setTag("")} className={`rounded-full border px-2.5 py-1 text-xs ${!tag ? "border-brand-500 bg-brand-600/15 text-brand-200" : "border-white/10 bg-zinc-900 text-zinc-400"}`}>{t("crm.all")}</button>
            {tags.map((t) => <button key={t} onClick={() => setTag(t)} data-testid={`crm-tag-${t}`} className={`rounded-full border px-2.5 py-1 text-xs ${tag === t ? "border-brand-500 bg-brand-600/15 text-brand-200" : "border-white/10 bg-zinc-900 text-zinc-400 hover:text-zinc-200"}`}>{t}</button>)}
          </div>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24 text-zinc-600"><Loader2 className="h-7 w-7 animate-spin" /></div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 bg-zinc-950 px-4 py-16 text-center" data-testid="crm-empty">
          <Users className="mx-auto h-9 w-9 text-zinc-600" aria-hidden="true" />
          <p className="mt-3 text-sm font-semibold text-zinc-200">
            {contacts.length === 0 ? t("crm.empty.title") : t("crm.empty.filteredTitle")}
          </p>
          <p className="mx-auto mt-1 max-w-md text-xs text-zinc-500">
            {contacts.length === 0
              ? t("crm.empty.description")
              : t("crm.empty.filteredDescription")}
          </p>
          {contacts.length === 0 && (
            <button
              type="button"
              onClick={() => navigate("/clients")}
              data-testid="crm-empty-action"
              className="mt-5 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500"
            >
              {t("crm.empty.action")} <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((c) => (
            <button key={c.id} onClick={() => navigate(`/crm/${c.id}`)} data-testid="crm-contact-card"
              className="group flex flex-col rounded-2xl border border-white/10 bg-zinc-950 p-4 text-left transition-all hover:border-brand-500/40 animate-fade-up">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-600/15 text-brand-300 text-sm font-bold">{c.name.slice(0, 2).toUpperCase()}</span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-zinc-100">{c.name}</p>
                    <p className="truncate text-xs text-zinc-500">{c.industry || c.contact || t("crm.company")}</p>
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-zinc-700 transition-transform group-hover:translate-x-0.5 group-hover:text-brand-300" />
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-lg bg-zinc-900/60 p-2"><p className="text-zinc-500">{t("crm.openDeals")}</p><p className="font-bold text-zinc-200">{c.open_leads}</p></div>
                <div className="rounded-lg bg-zinc-900/60 p-2"><p className="text-zinc-500">{t("crm.pipeline")}</p><p className="font-bold text-emerald-300">{fmtMoney(c.pipeline_value, locale)}</p></div>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                {(c.tags || []).slice(0, 3).map((t) => <span key={t} className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-zinc-400">{t}</span>)}
              </div>
              <p className="mt-2.5 flex items-center gap-1 text-[11px] text-zinc-600"><Clock className="h-3 w-3" /> {t("crm.lastActivity", { time: formatRelativeTime(c.last_activity, locale, t) })}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
