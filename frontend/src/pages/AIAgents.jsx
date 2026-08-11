import PageIntro from "@/components/PageIntro";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Bot, MessageSquare, Sparkles } from "lucide-react";
import { onboardingApi } from "@/lib/api";
import { events } from "@/lib/analytics";
import EmptyState from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const accentBg = {
  violet: "from-brand-600/30",
  emerald: "from-emerald-600/30",
  blue: "from-blue-600/30",
  amber: "from-amber-600/30",
};
const accentText = {
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

function normalizeAgents(payload) {
  const raw = extractAgentsList(payload);
  if (!Array.isArray(raw)) return [];
  return raw.filter((a) => a && typeof a === "object").map((a, i) => ({
    id: a.id || `agent-${i}`,
    name: a.name || "Untitled agent",
    role: a.role || "Assistant",
    description: a.description || "",
    avatar: a.avatar || "",
    accent: a.accent || "violet",
  }));
}

export default function AIAgents() {
  const { t } = useTranslation();
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const list = Array.isArray(agents) ? agents : [];

  const loadAgents = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/agents`, { credentials: "include" });
      const data = await res.json().catch(() => null);
      const next = normalizeAgents(data);
      setAgents(Array.isArray(next) ? next : []);

      if (!res.ok) {
        const msg =
          (data && typeof data.detail === "string" && data.detail) ||
          (data && data.error && data.error.message) ||
          `Could not load agents (${res.status})`;
        setError(msg);
        return;
      }
    } catch (e) {
      setAgents([]);
      setError(e?.message || "Could not load agents");
    } finally {
      setLoading(false);
    }
  };

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
  }, []);

  const openAgent = (id, name) => {
    events.agentOpened({ agent_id: id });
    const prompt = `I'd like help from the ${name || "specialist"} agent.`;
    navigate(`/ai-chat?q=${encodeURIComponent(prompt)}`);
  };

  return (
    <div className="space-y-5" data-testid="ai-agents-page">
      <PageIntro title={t("pages.aiAgents.title")} description={t("pages.aiAgents.description")} help={t("help.aiAgents")} />

      <div className="max-w-2xl">
        <p className="text-sm text-zinc-400">
          <span className="font-medium text-zinc-200">AI Agents</span> are specialists for a role —
          sales, operations, writing, and more. Chat with a built-in specialist below.
          For quick questions across your whole business, use{" "}
          <button type="button" onClick={() => navigate("/ai-chat")} className="text-brand-400 hover:text-brand-300 underline-offset-2 hover:underline">
            Copilot
          </button>
          .
        </p>
        <p className="mt-2 text-xs text-zinc-600" data-testid="custom-agents-note">
          Custom agent creation is not available in this release — built-in specialists are ready to use.
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
              <div className={`pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br ${accentBg[a.accent] || accentBg.violet} to-transparent blur-2xl opacity-60`} />
              <div className="relative flex items-start gap-3">
                {a.avatar ? (
                  <img src={a.avatar} alt="" className="h-12 w-12 rounded-xl border border-white/10 object-cover" />
                ) : (
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-zinc-900">
                    <Bot className={`h-5 w-5 ${accentText[a.accent] || accentText.violet}`} aria-hidden="true" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-zinc-100">{a.name}</p>
                  <p className={`text-xs font-medium ${accentText[a.accent] || accentText.violet}`}>{a.role}</p>
                </div>
                <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" /> Available
                </span>
              </div>
              <p className="relative mt-3 text-sm leading-relaxed text-zinc-400">
                {a.description || `${a.name} specializes in ${a.role.toLowerCase()} work inside your Assistify workspace.`}
              </p>
              <div className="relative mt-4">
                <button
                  type="button"
                  onClick={() => openAgent(a.id, a.name)}
                  data-testid={`chat-agent-${a.id}`}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-900 py-2 text-sm font-medium text-zinc-200 transition-all hover:bg-brand-600 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
                >
                  <MessageSquare className="h-4 w-4" aria-hidden="true" /> Chat with {a.name}
                </button>
              </div>
            </div>
          ))}
          {loading && (
            <div className="col-span-full flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 py-16 text-zinc-600" data-testid="ai-agents-loading">
              <Bot className="h-8 w-8" aria-hidden="true" />
              <p className="mt-2 text-sm">Loading agents…</p>
            </div>
          )}
          {!loading && list.length === 0 && (
            <div className="col-span-full">
              <EmptyState
                icon={Sparkles}
                title="No AI agents available yet"
                description="Agents are specialists you can chat with for a specific job — like writing or sales follow-up."
                why="When agents are enabled for your workspace, they appear here. Meanwhile, Copilot can help across your business."
                actionLabel="Ask Copilot"
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
