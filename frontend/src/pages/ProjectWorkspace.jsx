import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft, Loader2, Users, CircleDot, Calendar, TrendingUp, Plus, Trash2,
  Send, Bot, Sparkles, FileText, FolderOpen, CheckSquare, Clock, StickyNote,
  FilePlus2, FileUp, CheckCircle2, Rocket, ScrollText, RotateCcw, Receipt,
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { projectsApi, tasksApi, documentsApi, proposalsApi, activitiesApi, getAccessToken } from "@/lib/api";
import EmptyState from "@/components/EmptyState";
import AIPlanner from "@/components/workspace/AIPlanner";
import ProposalWriter from "@/components/workspace/ProposalWriter";
import ContractWriter from "@/components/workspace/ContractWriter";
import InvoiceWriter from "@/components/workspace/InvoiceWriter";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const statusStyle = {
  "In Progress": "bg-violet-500/10 text-violet-400 border-violet-500/20",
  Review: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  Completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Blocked: "bg-red-500/10 text-red-400 border-red-500/20",
};
const priorityDot = { High: "bg-red-400", Medium: "bg-amber-400", Low: "bg-zinc-500" };
const fmtDate = (d) => d ? new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "No date";

/* ---------------- Overview ---------------- */
function Overview({ project, tasks, documents, goTab }) {
  const meta = [
    { label: "Client", value: project.client_name || "No client", icon: Users },
    { label: "Status", value: project.status, icon: CircleDot },
    { label: "Deadline", value: fmtDate(project.due), icon: Calendar },
    { label: "Progress", value: `${project.progress}%`, icon: TrendingUp },
  ];
  return (
    <div className="space-y-6" data-testid="tab-overview">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {meta.map((m) => (
          <div key={m.label} className="rounded-xl border border-white/10 bg-zinc-950 p-4">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-zinc-500"><m.icon className="h-3.5 w-3.5" />{m.label}</div>
            <p className="mt-2 truncate text-lg font-semibold text-zinc-100">{m.value}</p>
          </div>
        ))}
      </div>
      <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-zinc-300">Overall progress</span><span className="text-zinc-400">{project.progress}%</span>
        </div>
        <Progress value={project.progress} className="h-2 bg-zinc-800 [&>div]:bg-violet-500" />
      </div>
      <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
        <h3 className="mb-2 text-sm font-semibold text-zinc-100">Description</h3>
        <p className="text-sm leading-relaxed text-zinc-400" data-testid="overview-description">{project.description || "No description yet. Edit the project to add details."}</p>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-100"><CheckSquare className="h-4 w-4 text-violet-400" /> Linked Tasks</h3>
            <button onClick={() => goTab("tasks")} className="text-xs font-medium text-violet-400 hover:text-violet-300">Manage</button>
          </div>
          {tasks.length === 0 ? <p className="py-4 text-center text-sm text-zinc-600">No tasks linked yet</p> : (
            <div className="space-y-2">
              {tasks.slice(0, 5).map((t) => (
                <div key={t.id} className="flex items-center gap-2 text-sm">
                  <span className={`h-2 w-2 shrink-0 rounded-full ${priorityDot[t.priority]}`} />
                  <span className={`truncate ${t.done ? "text-zinc-500 line-through" : "text-zinc-200"}`}>{t.title}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-100"><FolderOpen className="h-4 w-4 text-violet-400" /> Linked Documents</h3>
            <button onClick={() => goTab("documents")} className="text-xs font-medium text-violet-400 hover:text-violet-300">Manage</button>
          </div>
          {documents.length === 0 ? <p className="py-4 text-center text-sm text-zinc-600">No documents linked yet</p> : (
            <div className="space-y-2">
              {documents.slice(0, 5).map((d) => (
                <div key={d.id} className="flex items-center gap-2 text-sm text-zinc-200"><FileText className="h-4 w-4 shrink-0 text-zinc-500" /><span className="truncate">{d.name}</span></div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------------- Project Chat ---------------- */
function ProjectChat({ projectId, projectName }) {
  const sessionId = `project-${projectId}`;
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/chat/history/${sessionId}`, { headers: { Authorization: `Bearer ${getAccessToken()}` }, credentials: "include" }).then((r) => r.json())
      .then((h) => setMessages(Array.isArray(h) ? h.map((m) => ({ role: m.role, content: m.content })) : []))
      .catch(() => {}).finally(() => setLoaded(true));
  }, [sessionId]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streaming]);

  const send = async () => {
    const content = input.trim();
    if (!content || streaming) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content }, { role: "assistant", content: "" }]);
    setStreaming(true);
    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${getAccessToken()}` },
        credentials: "include",
        body: JSON.stringify({ session_id: sessionId, agent_id: "copilot", message: `Project context: "${projectName}". ${content}` }),
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
          let data; try { data = JSON.parse(line.slice(6)); } catch { continue; }
          if (data.delta) setMessages((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: c[c.length - 1].content + data.delta }; return c; });
        }
      }
    } catch {
      setMessages((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: "Sorry, something went wrong." }; return c; });
    } finally { setStreaming(false); }
  };

  return (
    <div className="flex h-[calc(100vh-16rem)] flex-col" data-testid="tab-chat">
      <div className="mb-3 flex items-center gap-2 rounded-lg border border-violet-500/20 bg-violet-600/10 px-3 py-2 text-xs text-violet-300">
        <Sparkles className="h-4 w-4" /> This AI chat is dedicated to <b className="font-semibold">{projectName}</b> and remembers your conversation history.
      </div>
      <div className="flex-1 overflow-y-auto rounded-xl border border-white/10 bg-zinc-950/50 p-4">
        {loaded && messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-600 glow-violet"><Bot className="h-6 w-6 text-white" /></div>
            <p className="mt-3 text-sm text-zinc-400">Ask anything about this project — planning, drafts, next steps.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`} data-testid={`chat-msg-${m.role}`}>
                {m.role === "assistant" && <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600/20 text-violet-400"><Bot className="h-4 w-4" /></div>}
                <div className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user" ? "bg-violet-600 text-white" : "border border-white/10 bg-zinc-900 text-zinc-200"}`}>
                  {m.content || (streaming && i === messages.length - 1 ? <Loader2 className="h-4 w-4 animate-spin text-violet-400" /> : m.content)}
                </div>
              </div>
            ))}
            <div ref={endRef} />
          </div>
        )}
      </div>
      <form onSubmit={(e) => { e.preventDefault(); send(); }} className="mt-3 mb-6 flex items-center gap-3">
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Message project copilot…" data-testid="chat-input"
          className="flex-1 rounded-xl border border-white/10 bg-zinc-950 px-4 py-3 text-sm text-zinc-100 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
        <button type="submit" disabled={streaming || !input.trim()} data-testid="chat-send" className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600 text-white transition-all hover:bg-violet-500 disabled:opacity-40 glow-violet"><Send className="h-4 w-4" /></button>
      </form>
    </div>
  );
}

/* ---------------- Tasks ---------------- */
function TasksTab({ projectId, tasks, reload }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("Medium");
  const [due, setDue] = useState("");
  const [saving, setSaving] = useState(false);

  const add = async () => {
    if (!title.trim()) { toast.error("Task title is required"); return; }
    setSaving(true);
    try { await tasksApi.create({ title: title.trim(), project_id: projectId, priority, due, done: false }); toast.success("Task created"); setOpen(false); setTitle(""); setPriority("Medium"); setDue(""); reload(); }
    catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };
  const toggle = async (t) => { try { await tasksApi.update(t.id, { title: t.title, project_id: t.project_id, priority: t.priority, due: t.due, done: !t.done }); reload(); } catch (e) { toast.error(e.message); } };
  const del = async (t) => { try { await tasksApi.remove(t.id); toast.success("Task deleted"); reload(); } catch (e) { toast.error(e.message); } };

  return (
    <div className="space-y-4" data-testid="tab-tasks">
      <div className="flex justify-end">
        <button onClick={() => setOpen(true)} data-testid="ws-add-task-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet"><Plus className="h-4 w-4" /> Add Task</button>
      </div>
      {tasks.length === 0 ? <EmptyState icon={CheckSquare} title="No tasks yet" description="Add tasks to break this project into actionable steps." actionLabel="Add Task" onAction={() => setOpen(true)} testid="ws-tasks-empty" /> : (
        <div className="overflow-hidden rounded-xl border border-white/10 bg-zinc-950">
          {tasks.map((t) => (
            <div key={t.id} className="group flex items-center gap-4 border-b border-white/5 px-5 py-3.5 transition-colors last:border-0 hover:bg-zinc-900/40" data-testid={`ws-task-${t.id}`}>
              <Checkbox checked={t.done} onCheckedChange={() => toggle(t)} data-testid={`ws-task-check-${t.id}`} className="border-white/20 data-[state=checked]:border-violet-500 data-[state=checked]:bg-violet-600" />
              <div className="min-w-0 flex-1"><p className={`text-sm ${t.done ? "text-zinc-500 line-through" : "text-zinc-100"}`}>{t.title}</p>{t.due && <p className="text-xs text-zinc-500">{fmtDate(t.due)}</p>}</div>
              <span className={`h-2 w-2 rounded-full ${priorityDot[t.priority]}`} />
              <button onClick={() => del(t)} data-testid={`ws-delete-task-${t.id}`} className="rounded-md p-1.5 text-zinc-500 opacity-0 transition-all hover:bg-zinc-800 hover:text-red-400 group-hover:opacity-100"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="border-white/10 bg-zinc-950 text-zinc-100 sm:max-w-md" data-testid="ws-task-dialog">
          <DialogHeader><DialogTitle>New Task</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <input value={title} onChange={(e) => setTitle(e.target.value)} data-testid="ws-task-title-input" placeholder="Task title" className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
            <div className="grid grid-cols-2 gap-3">
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger data-testid="ws-task-priority-trigger" className="border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
                <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">{["High", "Medium", "Low"].map((s) => <SelectItem key={s} value={s} data-testid={`ws-task-priority-${s}`}>{s}</SelectItem>)}</SelectContent>
              </Select>
              <input type="date" value={due} onChange={(e) => setDue(e.target.value)} data-testid="ws-task-due-input" className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
            </div>
          </div>
          <DialogFooter>
            <button onClick={() => setOpen(false)} className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-300 hover:text-white">Cancel</button>
            <button onClick={add} disabled={saving} data-testid="ws-task-save-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50">{saving && <Loader2 className="h-4 w-4 animate-spin" />}Create</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* ---------------- Documents ---------------- */
function DocumentsTab({ projectId, documents, reload }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("Doc");
  const [saving, setSaving] = useState(false);

  const add = async () => {
    if (!name.trim()) { toast.error("Document name is required"); return; }
    setSaving(true);
    try { await documentsApi.create({ name: name.trim(), type, project_id: projectId, size: "—" }); toast.success("Document uploaded"); setOpen(false); setName(""); setType("Doc"); reload(); }
    catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };
  const del = async (d) => { try { await documentsApi.remove(d.id); toast.success("Document deleted"); reload(); } catch (e) { toast.error(e.message); } };

  return (
    <div className="space-y-4" data-testid="tab-documents">
      <div className="flex justify-end">
        <button onClick={() => setOpen(true)} data-testid="ws-add-doc-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet"><FileUp className="h-4 w-4" /> Add Document</button>
      </div>
      {documents.length === 0 ? <EmptyState icon={FolderOpen} title="No documents yet" description="Attach documents and files relevant to this project." actionLabel="Add Document" onAction={() => setOpen(true)} testid="ws-docs-empty" /> : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {documents.map((d) => (
            <div key={d.id} className="group relative rounded-xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-violet-500/40" data-testid={`ws-doc-${d.id}`}>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-violet-600/15 text-violet-400"><FileText className="h-6 w-6" /></div>
              <p className="mt-3 truncate text-sm font-medium text-zinc-100" title={d.name}>{d.name}</p>
              <p className="mt-0.5 text-xs text-zinc-500">{d.type}</p>
              <button onClick={() => del(d)} data-testid={`ws-delete-doc-${d.id}`} className="absolute right-2 top-2 rounded-md p-1.5 text-zinc-500 opacity-0 transition-all hover:bg-zinc-800 hover:text-red-400 group-hover:opacity-100"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="border-white/10 bg-zinc-950 text-zinc-100 sm:max-w-md" data-testid="ws-doc-dialog">
          <DialogHeader><DialogTitle>Add Document</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <input value={name} onChange={(e) => setName(e.target.value)} data-testid="ws-doc-name-input" placeholder="e.g. Statement of Work.pdf" className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
            <Select value={type} onValueChange={setType}>
              <SelectTrigger data-testid="ws-doc-type-trigger" className="border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">{["Doc", "PDF", "Sheet", "Image", "Archive"].map((s) => <SelectItem key={s} value={s} data-testid={`ws-doc-type-${s}`}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <button onClick={() => setOpen(false)} className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-300 hover:text-white">Cancel</button>
            <button onClick={add} disabled={saving} data-testid="ws-doc-save-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50">{saving && <Loader2 className="h-4 w-4 animate-spin" />}Upload</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* ---------------- Proposals ---------------- */
function ProposalsTab({ projectId, proposals, reload }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: "", amount: "", status: "Draft", content: "" });
  const [saving, setSaving] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const add = async () => {
    if (!form.title.trim()) { toast.error("Proposal title is required"); return; }
    setSaving(true);
    try { await proposalsApi.create({ ...form, title: form.title.trim(), project_id: projectId }); toast.success("Proposal generated"); setOpen(false); setForm({ title: "", amount: "", status: "Draft", content: "" }); reload(); }
    catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };
  const del = async (p) => { try { await proposalsApi.remove(p.id); toast.success("Proposal deleted"); reload(); } catch (e) { toast.error(e.message); } };

  const st = { Draft: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20", Sent: "bg-violet-500/10 text-violet-400 border-violet-500/20", Accepted: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", Rejected: "bg-red-500/10 text-red-400 border-red-500/20" };

  return (
    <div className="space-y-4" data-testid="tab-proposals">
      <div className="flex justify-end">
        <button onClick={() => setOpen(true)} data-testid="ws-add-proposal-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet"><FilePlus2 className="h-4 w-4" /> New Proposal</button>
      </div>
      {proposals.length === 0 ? <EmptyState icon={FileText} title="No proposals yet" description="Generate a proposal to send to your client for this project." actionLabel="New Proposal" onAction={() => setOpen(true)} testid="ws-proposals-empty" /> : (
        <div className="space-y-3">
          {proposals.map((p) => (
            <div key={p.id} className="group flex items-center gap-4 rounded-xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-violet-500/40" data-testid={`ws-proposal-${p.id}`}>
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-violet-600/15 text-violet-400"><FileText className="h-5 w-5" /></div>
              <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-zinc-100">{p.title}</p>{p.content && <p className="truncate text-xs text-zinc-500">{p.content}</p>}</div>
              {p.amount && <span className="hidden text-sm font-semibold text-zinc-200 sm:block">{p.amount}</span>}
              <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${st[p.status]}`}>{p.status}</span>
              <button onClick={() => del(p)} data-testid={`ws-delete-proposal-${p.id}`} className="rounded-md p-1.5 text-zinc-500 opacity-0 transition-all hover:bg-zinc-800 hover:text-red-400 group-hover:opacity-100"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="border-white/10 bg-zinc-950 text-zinc-100 sm:max-w-md" data-testid="ws-proposal-dialog">
          <DialogHeader><DialogTitle>New Proposal</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <input value={form.title} onChange={(e) => set("title", e.target.value)} data-testid="ws-proposal-title-input" placeholder="Proposal title" className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
            <div className="grid grid-cols-2 gap-3">
              <input value={form.amount} onChange={(e) => set("amount", e.target.value)} data-testid="ws-proposal-amount-input" placeholder="$24,000" className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
              <Select value={form.status} onValueChange={(v) => set("status", v)}>
                <SelectTrigger data-testid="ws-proposal-status-trigger" className="border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
                <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">{["Draft", "Sent", "Accepted", "Rejected"].map((s) => <SelectItem key={s} value={s} data-testid={`ws-proposal-status-${s}`}>{s}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <textarea value={form.content} onChange={(e) => set("content", e.target.value)} data-testid="ws-proposal-content-input" placeholder="Summary / scope (optional)" rows={3} className="w-full resize-none rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
          </div>
          <DialogFooter>
            <button onClick={() => setOpen(false)} className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-300 hover:text-white">Cancel</button>
            <button onClick={add} disabled={saving} data-testid="ws-proposal-save-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50">{saving && <Loader2 className="h-4 w-4 animate-spin" />}Generate</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* ---------------- Notes ---------------- */
function NotesTab({ project, reload }) {
  const [notes, setNotes] = useState(project.notes || "");
  const [saving, setSaving] = useState(false);
  const save = async () => {
    setSaving(true);
    try {
      await projectsApi.update(project.id, {
        name: project.name, client_id: project.client_id, status: project.status,
        progress: project.progress, due: project.due, members: project.members,
        description: project.description || "", notes,
      });
      toast.success("Notes saved"); reload();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };
  return (
    <div className="space-y-4" data-testid="tab-notes">
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="ws-notes-input" rows={14} placeholder="Jot down meeting notes, ideas, decisions…" className="w-full resize-none rounded-xl border border-white/10 bg-zinc-950 p-5 text-sm leading-relaxed text-zinc-200 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
      <div className="flex justify-end">
        <button onClick={save} disabled={saving} data-testid="ws-notes-save-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50">{saving && <Loader2 className="h-4 w-4 animate-spin" />}Save Notes</button>
      </div>
    </div>
  );
}

/* ---------------- Activity ---------------- */
const activityMeta = {
  project_created: { icon: Rocket, color: "bg-violet-600/20 text-violet-400" },
  task_created: { icon: Plus, color: "bg-blue-600/20 text-blue-400" },
  task_completed: { icon: CheckCircle2, color: "bg-emerald-600/20 text-emerald-400" },
  proposal_generated: { icon: FileText, color: "bg-amber-600/20 text-amber-400" },
  document_uploaded: { icon: FileUp, color: "bg-cyan-600/20 text-cyan-400" },
  plan_generated: { icon: Sparkles, color: "bg-violet-600/20 text-violet-400" },
  proposal_saved: { icon: FilePlus2, color: "bg-violet-600/20 text-violet-400" },
  proposal_exported: { icon: FileUp, color: "bg-blue-600/20 text-blue-400" },
  contract_generated: { icon: ScrollText, color: "bg-violet-600/20 text-violet-400" },
  contract_saved: { icon: FilePlus2, color: "bg-violet-600/20 text-violet-400" },
  contract_exported: { icon: FileUp, color: "bg-blue-600/20 text-blue-400" },
  contract_restored: { icon: RotateCcw, color: "bg-emerald-600/20 text-emerald-400" },
  invoice_generated: { icon: Receipt, color: "bg-violet-600/20 text-violet-400" },
  invoice_saved: { icon: FilePlus2, color: "bg-violet-600/20 text-violet-400" },
  invoice_exported: { icon: FileUp, color: "bg-blue-600/20 text-blue-400" },
  invoice_restored: { icon: RotateCcw, color: "bg-emerald-600/20 text-emerald-400" },
};
function ActivityTab({ activities }) {
  const fmt = (d) => new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  return (
    <div data-testid="tab-activity">
      {activities.length === 0 ? <EmptyState icon={Clock} title="No activity yet" description="Actions on this project will be logged here automatically." testid="ws-activity-empty" /> : (
        <div className="relative space-y-1 pl-2">
          {activities.map((a, i) => {
            const m = activityMeta[a.type] || { icon: CircleDot, color: "bg-zinc-700 text-zinc-300" };
            const Icon = m.icon;
            return (
              <div key={a.id} className="relative flex gap-4 pb-6" data-testid={`activity-${a.type}`}>
                {i < activities.length - 1 && <span className="absolute left-[19px] top-10 h-full w-px bg-white/10" />}
                <div className={`z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${m.color}`}><Icon className="h-5 w-5" /></div>
                <div className="pt-1.5"><p className="text-sm text-zinc-200">{a.message}</p><p className="text-xs text-zinc-500">{fmt(a.created_at)}</p></div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ---------------- Workspace shell ---------------- */
export default function ProjectWorkspace() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(searchParams.get("tab") || "overview");

  const loadProject = () => projectsApi.get(id).then(setProject).catch(() => navigate("/projects"));
  const loadTasks = () => tasksApi.list(id).then(setTasks).catch(() => {});
  const loadDocs = () => documentsApi.list(id).then(setDocuments).catch(() => {});
  const loadProposals = () => proposalsApi.list(id).then(setProposals).catch(() => {});
  const loadActivities = () => activitiesApi.list(id).then(setActivities).catch(() => {});

  useEffect(() => {
    setLoading(true);
    Promise.all([loadProject(), loadTasks(), loadDocs(), loadProposals(), loadActivities()]).finally(() => setLoading(false));
    // eslint-disable-next-line
  }, [id]);

  const afterTaskChange = () => { loadTasks(); loadActivities(); loadProject(); };
  const afterDocChange = () => { loadDocs(); loadActivities(); };
  const afterProposalChange = () => { loadProposals(); loadActivities(); };

  if (loading || !project) {
    return <div className="flex items-center justify-center py-32 text-zinc-500" data-testid="workspace-loading"><Loader2 className="h-7 w-7 animate-spin" /></div>;
  }

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "planner", label: "AI Planner" },
    { id: "proposal", label: "Proposal" },
    { id: "contract", label: "Contract" },
    { id: "invoice", label: "Invoice" },
    { id: "chat", label: "AI Chat" },
    { id: "tasks", label: "Tasks" },
    { id: "documents", label: "Documents" },
    { id: "proposals", label: "Proposals" },
    { id: "notes", label: "Notes" },
    { id: "activity", label: "Activity" },
  ];

  return (
    <div className="space-y-6" data-testid="project-workspace">
      <div>
        <button onClick={() => navigate("/projects")} data-testid="back-to-projects" className="mb-4 flex items-center gap-1.5 text-sm text-zinc-400 transition-colors hover:text-zinc-100"><ArrowLeft className="h-4 w-4" /> Projects</button>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-zinc-50" data-testid="workspace-title">{project.name}</h1>
            <p className="mt-1 text-sm text-zinc-500">{project.client_name || "No client"} · Due {fmtDate(project.due)}</p>
          </div>
          <span className={`inline-flex w-fit items-center rounded-full border px-3 py-1 text-xs font-medium ${statusStyle[project.status]}`}>{project.status}</span>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1 border border-white/10 bg-zinc-950 p-1" data-testid="workspace-tabs">
          {tabs.map((t) => (
            <TabsTrigger key={t.id} value={t.id} data-testid={`tab-trigger-${t.id}`}
              className="rounded-md px-3 py-1.5 text-sm text-zinc-400 data-[state=active]:bg-violet-600 data-[state=active]:text-white">{t.label}</TabsTrigger>
          ))}
        </TabsList>

        <div className="mt-5">
          <TabsContent value="overview"><Overview project={project} tasks={tasks} documents={documents} goTab={setTab} /></TabsContent>
          <TabsContent value="planner"><AIPlanner projectId={project.id} projectName={project.name} onSaved={loadActivities} /></TabsContent>
          <TabsContent value="proposal"><ProposalWriter projectId={project.id} projectName={project.name} onSaved={loadActivities} /></TabsContent>
          <TabsContent value="contract"><ContractWriter projectId={project.id} projectName={project.name} onSaved={loadActivities} /></TabsContent>
          <TabsContent value="invoice"><InvoiceWriter projectId={project.id} projectName={project.name} onSaved={loadActivities} /></TabsContent>
          <TabsContent value="chat"><ProjectChat projectId={project.id} projectName={project.name} /></TabsContent>
          <TabsContent value="tasks"><TasksTab projectId={project.id} tasks={tasks} reload={afterTaskChange} /></TabsContent>
          <TabsContent value="documents"><DocumentsTab projectId={project.id} documents={documents} reload={afterDocChange} /></TabsContent>
          <TabsContent value="proposals"><ProposalsTab projectId={project.id} proposals={proposals} reload={afterProposalChange} /></TabsContent>
          <TabsContent value="notes"><NotesTab project={project} reload={loadProject} /></TabsContent>
          <TabsContent value="activity"><ActivityTab activities={activities} /></TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
