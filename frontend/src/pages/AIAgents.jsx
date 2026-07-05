import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bot, MessageSquare, Zap, Plus } from "lucide-react";

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

export default function AIAgents() {
  const [agents, setAgents] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${API}/agents`).then((r) => r.json()).then(setAgents).catch(() => {});
  }, []);

  return (
    <div className="space-y-5" data-testid="ai-agents-page">
      <div className="flex items-center justify-between">
        <p className="text-sm text-zinc-400">Deploy specialized AI agents for every part of your business.</p>
        <button data-testid="new-agent-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">
          <Plus className="h-4 w-4" /> New Agent
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {agents.map((a, i) => (
          <div
            key={a.id}
            style={{ animationDelay: `${i * 70}ms` }}
            className="group relative animate-fade-up overflow-hidden rounded-xl border border-white/10 bg-zinc-950 p-5 transition-all hover:border-violet-500/40"
            data-testid={`agent-card-${a.id}`}
          >
            <div className={`pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br ${accentBg[a.accent] || accentBg.violet} to-transparent blur-2xl opacity-60`} />
            <div className="relative flex items-start gap-3">
              <img src={a.avatar} alt={a.name} className="h-12 w-12 rounded-xl border border-white/10 object-cover" />
              <div className="flex-1">
                <p className="text-sm font-semibold text-zinc-100">{a.name}</p>
                <p className={`text-xs font-medium ${accentText[a.accent] || accentText.violet}`}>{a.role}</p>
              </div>
              <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse-glow" /> Active
              </span>
            </div>
            <p className="relative mt-3 text-sm leading-relaxed text-zinc-400">{a.description}</p>
            <div className="relative mt-4 flex items-center gap-2">
              <button
                onClick={() => navigate(`/ai-chat?agent=${a.id}`)}
                data-testid={`chat-agent-${a.id}`}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-zinc-900 py-2 text-sm font-medium text-zinc-200 transition-all hover:bg-violet-600 hover:text-white"
              >
                <MessageSquare className="h-4 w-4" /> Chat
              </button>
              <button className="flex items-center justify-center rounded-lg border border-white/10 px-3 py-2 text-zinc-400 transition-all hover:text-violet-400">
                <Zap className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
        {agents.length === 0 && (
          <div className="col-span-full flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 py-16 text-zinc-600">
            <Bot className="h-8 w-8" />
            <p className="mt-2 text-sm">Loading agents…</p>
          </div>
        )}
      </div>
    </div>
  );
}
