import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation();
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
      name: name.trim() || (triggerMeta
        ? t(`automations.builder.options.triggers.${triggerMeta.type}.label`, { defaultValue: triggerMeta.label })
        : t("automations.builder.newAutomation")),
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
          <DialogTitle>{t(initial ? "automations.builder.editTitle" : "automations.builder.createTitle")}</DialogTitle>
          <DialogDescription className="text-zinc-500">{t("automations.builder.description")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <div>
            <Label className="text-xs text-zinc-400">{t("automations.builder.name")}</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("automations.builder.namePlaceholder")} data-testid="builder-name" className="mt-1 border-white/10 bg-zinc-900" />
          </div>

          {/* WHEN */}
          <div className="rounded-xl border border-brand-500/20 bg-brand-500/[0.04] p-4">
            <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-brand-300">{t("automations.builder.when")}</p>
            <div className="flex flex-wrap items-center gap-2">
              <Select value={triggerType} onValueChange={(v) => { setTriggerType(v); const trigger = options?.triggers?.find((x) => x.type === v); setDays(trigger?.days ?? 0); }}>
                <SelectTrigger data-testid="builder-trigger" className="h-9 flex-1 border-white/10 bg-zinc-900 text-sm"><SelectValue placeholder={t("automations.builder.chooseTrigger")} /></SelectTrigger>
                <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
                  {(options?.triggers || []).map((trigger) => (
                    <SelectItem key={trigger.type} value={trigger.type}>{t(`automations.builder.options.triggers.${trigger.type}.label`, { defaultValue: trigger.label })}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {triggerMeta?.days > 0 && (
                <div className="flex items-center gap-1.5">
                  <Input type="number" value={days} onChange={(e) => setDays(e.target.value)} data-testid="builder-days" className="h-9 w-20 border-white/10 bg-zinc-900 text-sm" />
                  <span className="text-xs text-zinc-500">{t("automations.builder.days")}</span>
                </div>
              )}
            </div>
            {triggerMeta && <p className="mt-2 text-xs text-zinc-500">{t(`automations.builder.options.triggers.${triggerMeta.type}.description`, { defaultValue: triggerMeta.desc })}</p>}
          </div>

          {/* IF */}
          <div className="rounded-xl border border-white/10 bg-zinc-900/40 p-4">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">{t("automations.builder.if")} <span className="font-normal normal-case text-zinc-600">({t("common.optional")})</span></p>
              <button onClick={() => setConditions((c) => [...c, emptyCond()])} data-testid="add-condition" className="inline-flex items-center gap-1 text-xs font-medium text-brand-300 hover:text-brand-200"><Plus className="h-3.5 w-3.5" /> {t("automations.builder.addCondition")}</button>
            </div>
            {conditions.length === 0 ? (
              <p className="text-xs text-zinc-600">{t("automations.builder.noConditions")}</p>
            ) : (
              <div className="space-y-2">
                {conditions.map((c, i) => (
                  <div key={i} className="flex flex-wrap items-center gap-2">
                    <Select value={c.field} onValueChange={(v) => setConditions((arr) => arr.map((x, idx) => idx === i ? { ...x, field: v } : x))}>
                      <SelectTrigger className="h-8 w-[140px] border-white/10 bg-zinc-900 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
                        {(options?.conditions?.fields || []).map((f) => <SelectItem key={f.field} value={f.field} className="text-xs">{t(`automations.builder.options.fields.${f.field}`, { defaultValue: f.label })}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <Select value={c.op} onValueChange={(v) => setConditions((arr) => arr.map((x, idx) => idx === i ? { ...x, op: v } : x))}>
                      <SelectTrigger className="h-8 w-[120px] border-white/10 bg-zinc-900 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
                        {(options?.conditions?.ops || []).map((o) => <SelectItem key={o.op} value={o.op} className="text-xs">{t(`automations.builder.options.operators.${o.op}`, { defaultValue: o.label })}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <Input value={c.value} onChange={(e) => setConditions((arr) => arr.map((x, idx) => idx === i ? { ...x, value: e.target.value } : x))} placeholder={t("automations.builder.valuePlaceholder")} className="h-8 w-28 border-white/10 bg-zinc-900 text-xs" />
                    <button onClick={() => setConditions((arr) => arr.filter((_, idx) => idx !== i))} aria-label={t("automations.builder.removeCondition")} className="rounded-md p-1.5 text-zinc-500 hover:text-red-300"><Trash2 className="h-3.5 w-3.5" /></button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* THEN */}
          <div className="rounded-xl border border-white/10 bg-zinc-900/40 p-4">
            <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-zinc-400">{t("automations.builder.then")}</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {(options?.actions || []).map((act) => {
                const on = actions.includes(act.type);
                return (
                  <button key={act.type} onClick={() => toggleAction(act.type)} data-testid={`builder-action-${act.type}`}
                    className={`flex items-center gap-2 rounded-lg border px-2.5 py-2 text-left text-xs transition-all ${on ? "border-brand-500 bg-brand-600/15 text-brand-100" : "border-white/10 bg-zinc-900 text-zinc-400 hover:text-zinc-200"}`}>
                    <AiIcon name={act.icon} className="h-3.5 w-3.5 shrink-0" />
                    <span className="min-w-0 truncate">{t(`automations.builder.options.actions.${act.type}`, { defaultValue: act.label })}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* MODE */}
          <div>
            <Label className="text-xs text-zinc-400">{t("automations.builder.executionMode")}</Label>
            <Select value={mode} onValueChange={setMode}>
              <SelectTrigger data-testid="builder-mode" className="mt-1 h-9 border-white/10 bg-zinc-900 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
                {Object.entries(MODE_META).map(([v, m]) => <SelectItem key={v} value={v}>{t(m.labelKey)}</SelectItem>)}
              </SelectContent>
            </Select>
            <p className="mt-1 text-xs text-zinc-500">{MODE_META[mode] ? t(MODE_META[mode].descKey) : ""}</p>
          </div>
        </div>

        <DialogFooter>
          <button onClick={() => onOpenChange(false)} className="rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-200">{t("common.cancel")}</button>
          <button onClick={submit} disabled={!triggerType || actions.length === 0} data-testid="builder-save" className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-50">
            {t(initial ? "common.save" : "automations.builder.createAction")} <ArrowRight className="h-4 w-4" />
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
