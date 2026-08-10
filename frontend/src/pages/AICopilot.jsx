import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles, Send, Loader2, Check, X, Receipt, TriangleAlert, Clock, FolderKanban,
  Users, User, Wand2, ArrowRight,
} from "lucide-react";
import { copilotApi, onboardingApi } from "@/lib/api";
import { asArray } from "@/lib/safe";
import { events } from "@/lib/analytics";
import { toast } from "sonner";

const SESSION_KEY = "copilot_session";
const icons = { receipt: Receipt, alert: TriangleAlert, clock: Clock, folder: FolderKanban, sparkles: Sparkles, users: Users };

const TOOL_LABEL = {
  create_client: "Create Client", create_project: "Create Project", generate_plan: "Generate AI Plan",
  generate_proposal: "Generate Proposal", generate_contract: "Generate Contract", generate_invoice: "Generate Invoice",
};

function ActionCard({ action, onConfirm, onCancel, busy, done }) {
  return (
    <div className="mt-2 rounded-xl border border-violet-500/30 bg-violet-600/10 p-4" data-testid="copilot-action-card">
      <div className="flex items-center gap-2">
        <Wand2 className="h-4 w-4 text-violet-400" />
        <p className="text-sm font-semibold text-zinc-100">{TOOL_LABEL[action.tool] || "Action"}</p>
      </div>
      <p className="mt-2 text-xs text-zinc-400">I'm about to create:</p>
      <ul className="mt-1 space-y-1">
        {(asArray(action.preview)).map((p, i) => <li key={i} className="text-sm text-zinc-200">• {p}</li>)}
      </ul>
      {done ? (
        <p className="mt-3 flex items-center gap-1.5 text-sm text-emerald-400"><Check className="h-4 w-4" /> Done</p>
      ) : (
        <div className="mt-3 flex items-center gap-2">
          <button onClick={onConfirm} disabled={busy} data-testid="copilot-confirm" className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-60">
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />} Confirm
          </button>
          <button onClick={onCancel} disabled={busy} data-testid="copilot-cancel" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-300 transition-all hover:text-white">
            <X className="h-3.5 w-3.5" /> Cancel
          </button>
        </div>
      )}
    </div>
  );
}

export default function AICopilot() {
  const navigate = useNavigate();
  const [sessionId] = useState(() => {
    let s = sessionStorage.getItem(SESSION_KEY);
    if (!s) { s = `cp-${Date.now()}`; sessionStorage.setItem(SESSION_KEY, s); }
    return s;
  });
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [execBusy, setExecBusy] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    copilotApi.suggestions().then((s) => setSuggestions(asArray(s))).catch(() => setSuggestions([]));
    copilotApi.history(sessionId).then((h) => {
      if (Array.isArray(h) && h.length) setMessages(h.map((m) => ({ role: m.role, content: m.content, action: m.action, done: Boolean(m.action) })));
    }).catch(() => {});
  }, [sessionId]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setLoading(true);
    events.copilotUsed();
    onboardingApi.flag("copilot").catch(() => {});
    try {
      const res = await copilotApi.message(sessionId, msg);
      setMessages((m) => [...m, { role: "assistant", content: res.reply, action: res.action, done: false }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: `⚠️ ${e.message}`, error: true }]);
    } finally { setLoading(false); }
  };

  const confirmAction = async (idx, action) => {
    setExecBusy(idx);
    try {
      const res = await copilotApi.execute(sessionId, action.action_id);
      setMessages((m) => m.map((msg, i) => i === idx ? { ...msg, done: true } : msg));
      setMessages((m) => [...m, { role: "assistant", content: res.reply, navigate: res.navigate }]);
      copilotApi.suggestions().then((s) => setSuggestions(asArray(s))).catch(() => setSuggestions([]));
      toast.success(res.reply);
    } catch (e) { toast.error(e.message); }
    finally { setExecBusy(null); }
  };

  const cancelAction = (idx) => setMessages((m) => m.map((msg, i) => i === idx ? { ...msg, action: null, content: msg.content + "\n\n(Action cancelled.)" } : msg));

  const empty = messages.length === 0;

  return (
    <div className="mx-auto flex h-[calc(100vh-9rem)] max-w-3xl flex-col" data-testid="copilot-page">
      {empty ? (
        <div className="flex flex-1 flex-col items-center justify-center px-2 text-center" data-testid="copilot-empty">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-600 glow-violet" aria-hidden="true"><Sparkles className="h-8 w-8 text-white" /></div>
          <h1 className="mt-5 text-2xl font-bold tracking-tight text-zinc-50">Assistify Copilot</h1>
          <p className="mt-2 max-w-md text-sm text-zinc-400">
            Your day-to-day AI assistant across the whole workspace. Ask it to summarize a client, draft an email,
            create a project plan, prepare a proposal, or analyze recent activity.
          </p>
          <p className="mt-2 max-w-md text-xs text-zinc-600">
            Copilot is for quick questions and actions. For specialized roles, open AI Agents. For everything AI has already created, use AI Workspace.
          </p>
          <div className="mt-6 grid w-full max-w-xl grid-cols-1 gap-2 sm:grid-cols-2">
            {(asArray(suggestions).length
              ? asArray(suggestions)
              : [
                  { text: "Summarize my top clients", prompt: "Summarize my top clients and what needs attention.", icon: "users" },
                  { text: "Draft a follow-up email", prompt: "Draft a polite follow-up email for a recent proposal.", icon: "sparkles" },
                  { text: "Create a project plan", prompt: "Help me create a project plan for a new engagement.", icon: "folder" },
                  { text: "Prepare a proposal outline", prompt: "Outline a proposal for a mid-size consulting project.", icon: "sparkles" },
                ]
            ).map((s, i) => {
              const Icon = icons[s.icon] || Sparkles;
              return (
                <button key={i} type="button" onClick={() => send(s.prompt)} data-testid={`copilot-suggestion-${i}`}
                  className="flex items-center gap-3 rounded-xl border border-white/10 bg-zinc-950 p-3 text-left transition-all hover:border-violet-500/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600/15 text-violet-400"><Icon className="h-4 w-4" aria-hidden="true" /></span>
                  <span className="text-sm text-zinc-200">{s.text}</span>
                  <ArrowRight className="ml-auto h-4 w-4 text-zinc-600" aria-hidden="true" />
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="flex-1 space-y-4 overflow-y-auto pb-4" data-testid="copilot-messages">
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
              {m.role === "assistant" && <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600/15 text-violet-400"><Sparkles className="h-4 w-4" /></div>}
              <div className={`max-w-[80%] ${m.role === "user" ? "order-1" : ""}`}>
                <div className={`rounded-2xl px-4 py-2.5 text-sm ${m.role === "user" ? "bg-violet-600 text-white" : m.error ? "border border-red-500/30 bg-red-500/10 text-red-200" : "border border-white/10 bg-zinc-950 text-zinc-200"}`}
                  data-testid={m.role === "user" ? "copilot-user-msg" : "copilot-assistant-msg"}>
                  <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                </div>
                {m.action && <ActionCard action={m.action} busy={execBusy === i} done={m.done} onConfirm={() => confirmAction(i, m.action)} onCancel={() => cancelAction(i)} />}
                {m.navigate && <button onClick={() => navigate(m.navigate)} data-testid="copilot-open-result" className="mt-2 flex items-center gap-1.5 text-xs font-medium text-violet-400 hover:text-violet-300">Open <ArrowRight className="h-3.5 w-3.5" /></button>}
              </div>
              {m.role === "user" && <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-800 text-zinc-400"><User className="h-4 w-4" /></div>}
            </div>
          ))}
          {loading && <div className="flex gap-3"><div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600/15 text-violet-400"><Sparkles className="h-4 w-4" /></div><div className="rounded-2xl border border-white/10 bg-zinc-950 px-4 py-3"><Loader2 className="h-4 w-4 animate-spin text-violet-400" /></div></div>}
          <div ref={endRef} />
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); send(); }} className="mt-2 flex items-center gap-2 rounded-xl border border-white/10 bg-zinc-950 p-2">
        <label htmlFor="copilot-input" className="sr-only">Message Copilot</label>
        <input id="copilot-input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask anything or say 'Create a project for…'" data-testid="copilot-input"
          className="flex-1 bg-transparent px-3 py-2 text-sm text-zinc-100 outline-none placeholder:text-zinc-600" />
        <button type="submit" disabled={loading || !input.trim()} data-testid="copilot-send" aria-label="Send message" className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-600 text-white transition-all hover:bg-violet-500 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50">
          <Send className="h-4 w-4" aria-hidden="true" />
        </button>
      </form>
    </div>
  );
}
