import { useEffect, useState } from "react";
import { Plus, Trash2, ArrowRight } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { MODE_META } from "./automationShared";
import { AiIcon } from "@/components/ai/aiHelpers";

const emptyCond = () => ({ field: "status", op: "eq", value: "" });

export function AutomationBuilder({ open, onOpenChange, options, initial, onSave }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState("");
  const [days, setDays] = useState(0);
  const [conditions, setConditions] = useState([]);
  const [actions, setActions] = useState([]);
  const [mode, setMode] = useState("prepare");

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setName(initial.name || "");
      setDescription(initial.description || "");
      setTriggerType(initial.trigger?.type || "");
      setDays(initial.trigger?.days ?? 0);
      setConditions(initial.conditions || []);
      setActions((initial.actions || []).map((a) => a.type));
      setMode(initial.mode || "prepare");
    } else {
      setName(""); setDescription(""); setTriggerType(options?.triggers?.[0]?.type || "");
      setDays(options?.triggers?.[0]?.days ?? 0); setConditions([]); setActions([]); setMode("prepare");
    }
  }, [open, initial, options]);

  const triggerMeta = options?.triggers?.find((t) => t.type === triggerType);

  const toggleAction = (type) => {
    setActions((prev) => (prev.includes(type) ? prev.filter((a) => a !== type) : [...prev, type]));
  };

  const submit = () => {
    onSave({
      name: name.trim() || (triggerMeta?.label || "New automation"),
      description,
      trigger: { type: triggerType, days: Number(days) || 0 },
      conditions: conditions.filter((c) => c.field && c.op),
      actions: actions.map((type) => ({ type, config: {} })),
      mode,
      enabled: true,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto border-white/10 bg-zinc-950 text-zinc-100 sm:max-w-2xl" data-testid="automation-builder">
        <DialogHeader>
          <DialogTitle>{initial ? "Edit automation" : "Create automation"}</DialogTitle>
          <DialogDescription className="text-zinc-500">Build a rule: when something happens, optionally check conditions, then prepare or run actions.</DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <div>
            <Label className="text-xs text-zinc-400">Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Chase overdue enterprise invoices" data-testid="builder-name" className="mt-1 border-white/10 bg-zinc-900" />
          </div>

          {/* WHEN */}
          <div className="rounded-xl border border-violet-500/20 bg-violet-500/[0.04] p-4">
            <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-violet-300">When</p>
            <div className="flex flex-wrap items-center gap-2">
              <Select value={triggerType} onValueChange={(v) => { setTriggerType(v); const t = options?.triggers?.find((x) => x.type === v); setDays(t?.days ?? 0); }}>
                <SelectTrigger data-testid="builder-trigger" className="h-9 flex-1 border-white/10 bg-zinc-900 text-sm"><SelectValue placeholder="Choose a trigger" /></SelectTrigger>
                <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
                  {(options?.triggers || []).map((t) => (
                    <SelectItem key={t.type} value={t.type}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {triggerMeta?.days > 0 && (
                <div className="flex items-center gap-1.5">
                  <Input type="number" value={days} onChange={(e) => setDays(e.target.value)} data-testid="builder-days" className="h-9 w-20 border-white/10 bg-zinc-900 text-sm" />
                  <span className="text-xs text-zinc-500">days</span>
                </div>
              )}
            </div>
            {triggerMeta && <p className="mt-2 text-xs text-zinc-500">{triggerMeta.desc}</p>}
          </div>

          {/* IF */}
          <div className="rounded-xl border border-white/10 bg-zinc-900/40 p-4">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">If <span className="font-normal normal-case text-zinc-600">(optional)</span></p>
              <button onClick={() => setConditions((c) => [...c, emptyCond()])} data-testid="add-condition" className="inline-flex items-center gap-1 text-xs font-medium text-violet-300 hover:text-violet-200"><Plus className="h-3.5 w-3.5" /> Add condition</button>
            </div>
            {conditions.length === 0 ? (
              <p className="text-xs text-zinc-600">No conditions — the automation runs for every match.</p>
            ) : (
              <div className="space-y-2">
                {conditions.map((c, i) => (
                  <div key={i} className="flex flex-wrap items-center gap-2">
                    <Select value={c.field} onValueChange={(v) => setConditions((arr) => arr.map((x, idx) => idx === i ? { ...x, field: v } : x))}>
                      <SelectTrigger className="h-8 w-[140px] border-white/10 bg-zinc-900 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
                        {(options?.conditions?.fields || []).map((f) => <SelectItem key={f.field} value={f.field} className="text-xs">{f.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <Select value={c.op} onValueChange={(v) => setConditions((arr) => arr.map((x, idx) => idx === i ? { ...x, op: v } : x))}>
                      <SelectTrigger className="h-8 w-[120px] border-white/10 bg-zinc-900 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
                        {(options?.conditions?.ops || []).map((o) => <SelectItem key={o.op} value={o.op} className="text-xs">{o.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <Input value={c.value} onChange={(e) => setConditions((arr) => arr.map((x, idx) => idx === i ? { ...x, value: e.target.value } : x))} placeholder="value" className="h-8 w-28 border-white/10 bg-zinc-900 text-xs" />
                    <button onClick={() => setConditions((arr) => arr.filter((_, idx) => idx !== i))} aria-label="Remove condition" className="rounded-md p-1.5 text-zinc-500 hover:text-red-300"><Trash2 className="h-3.5 w-3.5" /></button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* THEN */}
          <div className="rounded-xl border border-white/10 bg-zinc-900/40 p-4">
            <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-zinc-400">Then</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {(options?.actions || []).map((act) => {
                const on = actions.includes(act.type);
                return (
                  <button key={act.type} onClick={() => toggleAction(act.type)} data-testid={`builder-action-${act.type}`}
                    className={`flex items-center gap-2 rounded-lg border px-2.5 py-2 text-left text-xs transition-all ${on ? "border-violet-500 bg-violet-600/15 text-violet-100" : "border-white/10 bg-zinc-900 text-zinc-400 hover:text-zinc-200"}`}>
                    <AiIcon name={act.icon} className="h-3.5 w-3.5 shrink-0" />
                    <span className="min-w-0 truncate">{act.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* MODE */}
          <div>
            <Label className="text-xs text-zinc-400">Execution mode</Label>
            <Select value={mode} onValueChange={setMode}>
              <SelectTrigger data-testid="builder-mode" className="mt-1 h-9 border-white/10 bg-zinc-900 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
                {Object.entries(MODE_META).map(([v, m]) => <SelectItem key={v} value={v}>{m.label}</SelectItem>)}
              </SelectContent>
            </Select>
            <p className="mt-1 text-xs text-zinc-500">{MODE_META[mode]?.desc}</p>
          </div>
        </div>

        <DialogFooter>
          <button onClick={() => onOpenChange(false)} className="rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-200">Cancel</button>
          <button onClick={submit} disabled={!triggerType || actions.length === 0} data-testid="builder-save" className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-50">
            {initial ? "Save" : "Create automation"} <ArrowRight className="h-4 w-4" />
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
