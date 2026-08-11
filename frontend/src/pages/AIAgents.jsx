import PageIntro from "@/components/PageIntro";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Bot, MessageSquare, Sparkles } from "lucide-react";
import { onboardingApi } from "@/lib/api";
import { events } from "@/lib/analytics";
import EmptyState from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const accentBg = {
  brand: "from-brand-600/30",
  violet: "from-brand-600/30",
  emerald: "from-emerald-600/30",
  blue: "from-blue-600/30",
  amber: "from-amber-600/30",
};
const accentText = {
  brand: "text-brand-400",
  violet: "text-brand-400",
  emerald: "text-emerald-400",
  blue: "text-blue-400",
  amber: "text-amber-400",
};

/** Always return an array — never pass API error objects to .map(). */
function extractAgentsList(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && typeof payload === "object") {
    if (Array.isArray(payload.agents)) return payload.agents;
    if (Array.isArray(payload.data)) return payload.data;
    if (Array.isArray(payload.items)) return payload.items;
  }
  return [];
}

function normalizeAgents(payload, t) {
  const raw = extractAgentsList(payload);
  if (!Array.isArray(raw)) return [];
  return raw.filter((a) => a && typeof a === "object").map((a, i) => ({
    id: a.id || `agent-${i}`,
    name: a.name || t("aiAgents.untitled"),
    role: a.role || t("aiAgents.assistant"),
    description: a.description || "",
    avatar: a.avatar || "",
    accent: a.accent === "violet" ? "brand" : (a.accent || "brand"),
  }));
}

export default function AIAgents() {
  const { t } = useTranslation();
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const list = Array.isArray(agents) ? agents : [];

  const loadAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/agents`, { credentials: "include" });
      const data = await res.json().catch(() => null);
      const next = normalizeAgents(data, t);
      setAgents(Array.isArray(next) ? next : []);

      if (!res.ok) {
        const msg =
          (data && typeof data.detail === "string" && data.detail) ||
          (data && data.error && data.error.message) ||
          t("aiAgents.loadErrorStatus", { status: res.status });
        setError(msg);
        return;
      }
    } catch (e) {
      setAgents([]);
      setError(e?.message || t("aiAgents.loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    let cancelled = false;
    onboardingApi.flag("agents").catch(() => {});
    (async () => {
      if (cancelled) return;
      await loadAgents();
    })();
    return () => {
      cancelled = true;
    };
  }, [loadAgents]);

  const openAgent = (id, name) => {
    events.agentOpened({ agent_id: id });
    const prompt = t("aiAgents.openPrompt", { name: name || t("aiAgents.specialist") });
    navigate(`/ai-chat?q=${encodeURIComponent(prompt)}`);
  };

  return (
    <div className="space-y-5" data-testid="ai-agents-page">
      <PageIntro title={t("pages.aiAgents.title")} description={t("pages.aiAgents.description")} helpModule="agents" />

      <div className="max-w-2xl">
        <p className="text-sm text-zinc-400">
          <span className="font-medium text-zinc-200">{t("pages.aiAgents.title")}</span> {t("aiAgents.intro")}{" "}
          <button type="button" onClick={() => navigate("/ai-chat")} className="text-brand-400 hover:text-brand-300 underline-offset-2 hover:underline">
            Copilot
          </button>
          {t("aiAgents.introEnd")}
        </p>
        <p className="mt-2 text-xs text-zinc-600" data-testid="custom-agents-note">
          {t("aiAgents.customUnavailable")}
        </p>
      </div>

      {error && !loading && (
        <LoadError message={error} onRetry={loadAgents} testid="ai-agents-error" />
      )}

      {!error && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((a, i) => (
            <div
              key={a.id}
              style={{ animationDelay: `${i * 70}ms` }}
              className="group relative animate-fade-up overflow-hidden rounded-xl border border-white/10 bg-zinc-950 p-5 transition-all hover:border-brand-500/40"
              data-testid={`agent-card-${a.id}`}
            >
              <div className={`pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br ${accentBg[a.accent] || accentBg.brand} to-transparent blur-2xl opacity-60`} />
              <div className="relative flex items-start gap-3">
                {a.avatar ? (
                  <img src={a.avatar} alt="" className="h-12 w-12 rounded-xl border border-white/10 object-cover" />
                ) : (
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-zinc-900">
                    <Bot className={`h-5 w-5 ${accentText[a.accent] || accentText.brand}`} aria-hidden="true" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-zinc-100">{a.name}</p>
                  <p className={`text-xs font-medium ${accentText[a.accent] || accentText.brand}`}>{a.role}</p>
                </div>
                <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" /> {t("aiAgents.available")}
                </span>
              </div>
              <p className="relative mt-3 text-sm leading-relaxed text-zinc-400">
                {a.description || t("aiAgents.fallbackDescription", { name: a.name, role: a.role.toLowerCase() })}
              </p>
              <div className="relative mt-4">
                <button
                  type="button"
                  onClick={() => openAgent(a.id, a.name)}
                  data-testid={`chat-agent-${a.id}`}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-900 py-2 text-sm font-medium text-zinc-200 transition-all hover:bg-brand-600 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
                >
                  <MessageSquare className="h-4 w-4" aria-hidden="true" /> {t("aiAgents.chatWith", { name: a.name })}
                </button>
              </div>
            </div>
          ))}
          {loading && (
            <div className="col-span-full flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 py-16 text-zinc-600" data-testid="ai-agents-loading">
              <Bot className="h-8 w-8" aria-hidden="true" />
              <p className="mt-2 text-sm">{t("aiAgents.loading")}</p>
            </div>
          )}
          {!loading && list.length === 0 && (
            <div className="col-span-full">
              <EmptyState
                icon={Sparkles}
                title={t("aiAgents.empty.title")}
                description={t("aiAgents.empty.description")}
                why={t("aiAgents.empty.why")}
                actionLabel={t("aiAgents.empty.action")}
                onAction={() => navigate("/ai-chat")}
                testid="ai-agents-empty"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
