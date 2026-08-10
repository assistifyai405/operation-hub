import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bot, MessageSquare, Plus, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { onboardingApi } from "@/lib/api";
import { events } from "@/lib/analytics";
import EmptyState from "@/components/EmptyState";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const accentBg = {
  violet: "from-violet-600/30",
  emerald: "from-emerald-600/30",
  blue: "from-blue-600/30",
  amber: "from-amber-600/30",
};
const accentText = {
  violet: "text-violet-400",
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
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const list = Array.isArray(agents) ? agents : [];

  useEffect(() => {
    let cancelled = false;
    onboardingApi.flag("agents").catch(() => {});

    async function loadAgents() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API}/agents`, { credentials: "include" });
        const data = await res.json().catch(() => null);
        if (cancelled) return;

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
        if (!Array.isArray(data) && !(data && Array.isArray(data.agents))) {
          if (next.length === 0) setError("Unexpected agents response");
        }
      } catch (e) {
        if (!cancelled) {
          setAgents([]);
          setError(e?.message || "Could not load agents");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadAgents();
    return () => {
      cancelled = true;
    };
  }, []);

  const openAgent = (id) => {
    events.agentOpened({ agent_id: id });
    navigate(`/ai-chat?agent=${id}`);
  };

  return (
    <div className="space-y-5" data-testid="ai-agents-page">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-2xl">
          <p className="text-sm text-zinc-400">
            <span className="font-medium text-zinc-200">AI Agents</span> are specialists for a role —
            sales, operations, writing, and more. Use them when you want focused help.
            For quick questions across your whole business, use{" "}
            <button type="button" onClick={() => navigate("/ai-chat")} className="text-violet-400 hover:text-violet-300 underline-offset-2 hover:underline">
              Copilot
            </button>
            .
          </p>
        </div>
        <button
          type="button"
          data-testid="new-agent-btn"
          disabled
          title="Custom agents will be available in a later release"
          aria-disabled="true"
          onClick={() => toast.info("Custom agents are coming later. Chat with a built-in specialist below.")}
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm font-semibold text-zinc-500 cursor-not-allowed"
        >
          <Plus className="h-4 w-4" aria-hidden="true" /> New Agent
          <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] font-medium text-zinc-400">Soon</span>
        </button>
      </div>

      {error && (
        <div
          className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200"
          data-testid="ai-agents-error"
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {list.map((a, i) => (
          <div
            key={a.id}
            style={{ animationDelay: `${i * 70}ms` }}
            className="group relative animate-fade-up overflow-hidden rounded-xl border border-white/10 bg-zinc-950 p-5 transition-all hover:border-violet-500/40"
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
                onClick={() => openAgent(a.id)}
                data-testid={`chat-agent-${a.id}`}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-900 py-2 text-sm font-medium text-zinc-200 transition-all hover:bg-violet-600 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50"
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
        {!loading && !error && list.length === 0 && (
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
    </div>
  );
}
