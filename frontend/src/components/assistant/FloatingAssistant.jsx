import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Sparkles, X, Send, Check, Undo2, Copy, RefreshCw, Wand2, Clock, Gauge,
  ChevronDown, CornerDownLeft, Loader2, CircleSlash,
} from "lucide-react";
import { toast } from "sonner";
import { assistantApi, getAccessToken } from "@/lib/api";
import { useAssistant } from "@/context/AssistantContext";
import { Markdown } from "@/components/assistant/Markdown";

const SLASH = {
  rewrite: "rewrite", summarize: "summarize", improve: "improve", email: "email",
  translate: "translate", pricing: "pricing", timeline: "timeline", review: "tone", brainstorm: "brainstorm",
};
const SLASH_HINTS = Object.keys(SLASH).map((s) => `/${s}`);
let _mid = 0;
const nextId = () => `m${Date.now()}_${_mid++}`;

function Report({ report }) {
  if (!report) return null;
  const hasDetail = report.what || report.why || report.impact;
  return (
    <div className="mt-2.5 rounded-lg border border-violet-500/20 bg-violet-500/[0.05] p-3" data-testid="assistant-report">
      {hasDetail && (
        <div className="space-y-1.5">
          {report.what && <p className="text-xs text-zinc-300"><span className="font-semibold text-violet-300">What: </span>{report.what}</p>}
          {report.why && <p className="text-xs text-zinc-300"><span className="font-semibold text-violet-300">Why: </span>{report.why}</p>}
          {report.impact && <p className="text-xs text-zinc-300"><span className="font-semibold text-violet-300">Impact: </span>{report.impact}</p>}
        </div>
      )}
      <div className="mt-2 flex items-center gap-3 text-[11px] text-zinc-400">
        {report.time_saved != null && <span className="inline-flex items-center gap-1"><Clock className="h-3 w-3 text-emerald-400" /> Saved ~{report.time_saved}m</span>}
        {report.confidence != null && <span className="inline-flex items-center gap-1"><Gauge className="h-3 w-3 text-cyan-400" /> {report.confidence}% confidence</span>}
      </div>
    </div>
  );
}

export default function FloatingAssistant() {
  const A = useAssistant();
  const { open, setOpen, effectiveContext, hasDocument, buildPayload } = A;
  const sessionRef = useRef(`asst-${Date.now()}`);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [targetKey, setTargetKey] = useState("");   // "" = whole document
  const [sections, setSections] = useState([]);
  const lastReq = useRef(null);
  const scrollRef = useRef(null);
  const ctxLabel = effectiveContext?.label || "your workspace";

  const updateMsg = (id, patch) => setMessages((ms) => ms.map((m) => (m.id === id ? { ...m, ...patch } : m)));

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, busy]);

  // Refresh suggestions + section list when the panel opens or the context changes.
  useEffect(() => {
    if (!open) return;
    const scope = effectiveContext?.scope || "generic";
    const dt = effectiveContext?.documentType || "";
    assistantApi.suggestions(scope, dt).then(setSuggestions).catch(() => setSuggestions([]));
    if (hasDocument) {
      const p = buildPayload();
      setSections((p.sections || []).map((s) => ({ key: s.key, label: s.label })));
    } else {
      setSections([]); setTargetKey("");
    }
    // eslint-disable-next-line
  }, [open, effectiveContext?.scope, effectiveContext?.documentType, hasDocument]);

  const typeOut = (id, full) => {
    let i = 0;
    const step = Math.max(2, Math.round(full.length / 45));
    const timer = setInterval(() => {
      i += step;
      updateMsg(id, { content: full.slice(0, i) });
      if (i >= full.length) { clearInterval(timer); updateMsg(id, { content: full, typing: false }); }
    }, 22);
  };

  const runAction = useCallback(async (command, opts = {}) => {
    if (busy) return;
    lastReq.current = { kind: "action", command, opts };
    const { instruction = "", arg = "" } = opts;
    const spec = suggestions.find((s) => s.command === command);
    const userLabel = spec ? spec.label : `/${command}`;
    setMessages((ms) => [...ms, { id: nextId(), role: "user", content: instruction ? `${userLabel}: ${instruction}` : userLabel }]);
    const aid = nextId();
    setMessages((ms) => [...ms, { id: aid, role: "assistant", content: "", typing: true }]);
    setBusy(true);
    try {
      const payload = { session_id: sessionRef.current, command, instruction, arg, context: buildPayload(opts.targetKey) };
      const res = await assistantApi.action(payload);
      updateMsg(aid, { report: res.report, apply: res.apply, typing: true });
      typeOut(aid, res.answer || "Done.");
    } catch (e) {
      updateMsg(aid, { content: "", typing: false, error: e.message || "The assistant couldn't complete that." });
    } finally { setBusy(false); }
  }, [busy, suggestions, buildPayload]); // eslint-disable-line react-hooks/exhaustive-deps

  const sendChat = useCallback(async (message) => {
    if (busy || !message.trim()) return;
    lastReq.current = { kind: "chat", message };
    setMessages((ms) => [...ms, { id: nextId(), role: "user", content: message }]);
    const aid = nextId();
    setMessages((ms) => [...ms, { id: aid, role: "assistant", content: "", typing: true }]);
    setBusy(true);
    try {
      const res = await fetch(assistantApi.streamUrl(), {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getAccessToken()}` },
        credentials: "include",
        body: JSON.stringify({ session_id: sessionRef.current, message, context: buildPayload() }),
      });
      if (!res.ok || !res.body) throw new Error("The assistant is unavailable right now.");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "", full = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n"); buffer = parts.pop();
        for (const line of parts) {
          if (!line.startsWith("data: ")) continue;
          let d; try { d = JSON.parse(line.slice(6)); } catch { continue; }
          if (d.delta) { full += d.delta; updateMsg(aid, { content: full }); }
          else if (d.error) { updateMsg(aid, { error: d.error }); }
          else if (d.done) { updateMsg(aid, { report: d.report, typing: false }); }
        }
      }
      updateMsg(aid, { typing: false });
    } catch (e) {
      updateMsg(aid, { content: "", typing: false, error: e.message });
    } finally { setBusy(false); }
  }, [busy, buildPayload]);

  const onSend = () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    if (text.startsWith("/")) {
      const [tok, ...rest] = text.slice(1).split(" ");
      const cmd = SLASH[tok.toLowerCase()];
      if (cmd) {
        const extra = rest.join(" ").trim();
        return runAction(cmd, cmd === "translate" ? { arg: extra || "Spanish" } : { instruction: extra, targetKey });
      }
    }
    sendChat(text);
  };

  const applyMsg = (m) => {
    const ok = A.applyChange(m.apply);
    if (ok) { updateMsg(m.id, { applied: true }); toast.success("Changes applied to the document"); }
    else toast.error("Open the document you want to edit, then apply.");
  };
  const undo = (m) => { if (A.undoLast()) { updateMsg(m.id, { applied: false }); toast.success("Reverted the last change"); } };
  const copy = (m) => { navigator.clipboard?.writeText(m.content || ""); toast.success("Copied"); };
  const regenerate = () => {
    const r = lastReq.current; if (!r || busy) return;
    if (r.kind === "action") runAction(r.command, r.opts); else sendChat(r.message);
  };

  const isTransform = (cmd) => { const s = suggestions.find((x) => x.command === cmd); return s?.mode === "transform"; };

  return (
    <>
      <AnimatePresence>
        {!open && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.06 }} whileTap={{ scale: 0.94 }}
            onClick={() => setOpen(true)} data-testid="assistant-fab"
            className="fixed bottom-20 right-6 z-[60] flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-600 text-white shadow-lg shadow-violet-900/40 glow-violet"
            aria-label="Open Assistify Assistant">
            <Sparkles className="h-6 w-6" />
            <span className="absolute inset-0 rounded-2xl bg-violet-500/40 animate-ping-slow" />
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ x: 460, opacity: 0.4 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 460, opacity: 0 }}
            transition={{ type: "spring", stiffness: 320, damping: 34 }}
            className="fixed bottom-0 right-0 top-0 z-[60] flex w-full max-w-[440px] flex-col border-l border-white/10 bg-zinc-950/95 backdrop-blur-xl sm:bottom-4 sm:right-4 sm:top-4 sm:max-h-[calc(100vh-2rem)] sm:rounded-2xl sm:border"
            data-testid="assistant-panel">
            {/* Header */}
            <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3.5">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-600 glow-violet"><Sparkles className="h-5 w-5 text-white" /></span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-zinc-50">Assistify Assistant</p>
                <p className="truncate text-xs text-zinc-500" data-testid="assistant-context-line">I see you're on <span className="text-violet-300">{ctxLabel}</span></p>
              </div>
              <button onClick={() => setOpen(false)} data-testid="assistant-close" aria-label="Close assistant" className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/5 hover:text-white"><X className="h-5 w-5" /></button>
            </div>

            {/* Section target selector */}
            {hasDocument && sections.length > 0 && (
              <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2">
                <Wand2 className="h-3.5 w-3.5 text-violet-400" />
                <span className="text-xs text-zinc-500">Apply to</span>
                <div className="relative flex-1">
                  <select value={targetKey} onChange={(e) => setTargetKey(e.target.value)} data-testid="assistant-section-select"
                    className="w-full appearance-none rounded-lg border border-white/10 bg-zinc-900 py-1.5 pl-2.5 pr-7 text-xs text-zinc-200 focus:border-violet-500/50 focus:outline-none">
                    <option value="">Whole document</option>
                    {sections.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-500" />
                </div>
              </div>
            )}

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-4" data-testid="assistant-messages">
              {messages.length === 0 && (
                <div className="rounded-xl border border-white/10 bg-zinc-900/40 p-4 text-center" data-testid="assistant-welcome">
                  <p className="text-sm font-semibold text-zinc-200">How can I help?</p>
                  <p className="mx-auto mt-1 max-w-[16rem] text-xs text-zinc-500">Pick a suggestion below, type <span className="text-violet-300">/</span> for commands, or ask me anything about {ctxLabel}.</p>
                </div>
              )}
              {messages.map((m) => (
                <div key={m.id} className={m.role === "user" ? "flex justify-end" : ""} data-testid={`assistant-msg-${m.role}`}>
                  {m.role === "user" ? (
                    <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-violet-600 px-3.5 py-2 text-sm text-white">{m.content}</div>
                  ) : (
                    <div className="max-w-[92%]">
                      {m.error ? (
                        <div className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300" data-testid="assistant-error"><CircleSlash className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {m.error}</div>
                      ) : (
                        <div className="rounded-2xl rounded-bl-sm border border-white/10 bg-zinc-900/70 px-3.5 py-3">
                          {m.content ? <Markdown>{m.content}</Markdown> : <span className="inline-flex gap-1"><span className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-400" /><span className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-400" style={{ animationDelay: "0.15s" }} /><span className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-400" style={{ animationDelay: "0.3s" }} /></span>}
                          {!m.typing && <Report report={m.report} />}
                          {!m.typing && (m.content || m.apply) && (
                            <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                              {m.apply && !m.applied && (
                                <button onClick={() => applyMsg(m)} data-testid="assistant-apply-btn" className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-2.5 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-violet-500"><Check className="h-3.5 w-3.5" /> Apply to document</button>
                              )}
                              {m.apply && m.applied && (
                                <button onClick={() => undo(m)} data-testid="assistant-undo-btn" className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-2.5 py-1.5 text-xs font-medium text-zinc-300 hover:text-white"><Undo2 className="h-3.5 w-3.5" /> Undo</button>
                              )}
                              {m.content && <button onClick={() => copy(m)} data-testid="assistant-copy-btn" className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-2.5 py-1.5 text-xs font-medium text-zinc-400 hover:text-white"><Copy className="h-3.5 w-3.5" /> Copy</button>}
                              <button onClick={regenerate} data-testid="assistant-regenerate-btn" className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-2.5 py-1.5 text-xs font-medium text-zinc-400 hover:text-white"><RefreshCw className="h-3.5 w-3.5" /> Regenerate</button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Suggested actions */}
            {suggestions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 border-t border-white/10 px-4 py-2.5" data-testid="assistant-suggestions">
                {suggestions.map((s) => (
                  <button key={s.command} disabled={busy}
                    onClick={() => (s.mode === "transform" ? runAction(s.command, { targetKey }) : runAction(s.command))}
                    data-testid={`assistant-chip-${s.command}`}
                    className="inline-flex items-center gap-1 rounded-full border border-violet-500/25 bg-violet-500/[0.06] px-2.5 py-1 text-xs font-medium text-violet-200 transition-all hover:border-violet-500/50 hover:bg-violet-500/15 disabled:opacity-50">
                    <Sparkles className="h-3 w-3" /> {s.label}
                  </button>
                ))}
              </div>
            )}

            {/* Input */}
            <div className="border-t border-white/10 p-3">
              <div className="relative flex items-end gap-2 rounded-xl border border-white/10 bg-zinc-900 p-1.5 focus-within:border-violet-500/50">
                <textarea value={input} onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); } }}
                  data-testid="assistant-input" rows={1} placeholder="Ask anything, or type / for commands…"
                  className="max-h-28 min-h-[36px] flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none" />
                <button onClick={onSend} disabled={busy || !input.trim()} data-testid="assistant-send"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-violet-600 text-white transition-colors hover:bg-violet-500 disabled:opacity-40">
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </button>
              </div>
              <div className="mt-1.5 flex items-center gap-2 px-1 text-[10px] text-zinc-600">
                <CornerDownLeft className="h-3 w-3" /> to send · {SLASH_HINTS.slice(0, 5).join(" ")}…
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
