import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Send, Sparkles, Bot } from "lucide-react";
import { getAccessToken } from "@/lib/api";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const suggestions = [
  "Draft a cold email for a SaaS prospect",
  "Summarize my priorities this week",
  "Write a project kickoff checklist",
  "Give me 3 pricing strategy ideas",
];

export default function AIChat() {
  const [params] = useSearchParams();
  const [agents, setAgents] = useState([]);
  const [agentId, setAgentId] = useState(params.get("agent") || "copilot");
  const [sessionId] = useState(() => `sess-${Date.now()}`);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/agents`, { headers: { Authorization: `Bearer ${getAccessToken()}` }, credentials: "include" }).then((r) => r.json()).then(setAgents).catch(() => {});
  }, []);

  useEffect(() => {
    const q = params.get("q");
    if (q) setInput(q);
  }, [params]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const activeAgent = agents.find((a) => a.id === agentId);

  const send = async (text) => {
    const content = (text ?? input).trim();
    if (!content || streaming) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content }]);
    setStreaming(true);
    setMessages((m) => [...m, { role: "assistant", content: "" }]);

    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getAccessToken()}` },
        credentials: "include",
        body: JSON.stringify({ session_id: sessionId, agent_id: agentId, message: content }),
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop();
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let data;
          try { data = JSON.parse(line.slice(6)); } catch { continue; }
          if (data.delta) {
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1] = { role: "assistant", content: copy[copy.length - 1].content + data.delta };
              return copy;
            });
          }
        }
      }
    } catch (e) {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = { role: "assistant", content: "Sorry, something went wrong. Please try again." };
        return copy;
      });
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-9rem)] flex-col" data-testid="ai-chat-page">
      {/* Agent selector */}
      <div className="mb-4 flex flex-wrap gap-2">
        {agents.map((a) => (
          <button
            key={a.id}
            onClick={() => setAgentId(a.id)}
            data-testid={`select-agent-${a.id}`}
            className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${agentId === a.id ? "border-violet-500 bg-violet-600/15 text-violet-300" : "border-white/10 bg-zinc-950 text-zinc-400 hover:text-zinc-200"}`}
          >
            <img src={a.avatar} alt={`${a.name || "AI agent"} avatar`} className="h-5 w-5 rounded-full object-cover" />
            {a.name}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-white/10 bg-zinc-950/50 p-4 sm:p-6">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-600 glow-violet">
              <Sparkles className="h-7 w-7 text-white" />
            </div>
            <h2 className="mt-4 text-xl font-semibold text-zinc-100">{activeAgent?.name || "Assistify Copilot"}</h2>
            <p className="mt-1 max-w-sm text-sm text-zinc-500">{activeAgent?.description || "How can I help you run your business today?"}</p>
            <div className="mt-6 grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  data-testid="chat-suggestion"
                  className="rounded-lg border border-white/10 bg-zinc-950 px-4 py-3 text-left text-sm text-zinc-300 transition-all hover:border-violet-500/40 hover:text-white"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`} data-testid={`chat-msg-${m.role}`}>
                {m.role === "assistant" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600/20 text-violet-400">
                    <Bot className="h-4 w-4" />
                  </div>
                )}
                <div className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user" ? "bg-violet-600 text-white" : "border border-white/10 bg-zinc-900 text-zinc-200"}`}>
                  {m.content || (streaming && i === messages.length - 1 ? <span className="inline-flex gap-1"><span className="h-2 w-2 animate-pulse-glow rounded-full bg-violet-400" /><span className="h-2 w-2 animate-pulse-glow rounded-full bg-violet-400" style={{ animationDelay: "0.2s" }} /><span className="h-2 w-2 animate-pulse-glow rounded-full bg-violet-400" style={{ animationDelay: "0.4s" }} /></span> : m.content)}
                </div>
              </div>
            ))}
            <div ref={endRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={(e) => { e.preventDefault(); send(); }} className="mt-4 mb-6 flex items-center gap-3" data-testid="chat-form">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Message ${activeAgent?.name || "Copilot"}…`}
          data-testid="chat-input"
          className="flex-1 rounded-xl border border-white/10 bg-zinc-950 px-4 py-3 text-sm text-zinc-100 outline-none transition-all placeholder:text-zinc-600 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          data-testid="chat-send"
          className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600 text-white transition-all hover:bg-violet-500 disabled:opacity-40 glow-violet"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
