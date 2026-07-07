import { useRef, useState } from "react";
import { Loader2, Upload, ImageIcon } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { settingsApi } from "@/lib/api";
import { toast } from "sonner";

export const inputCls =
  "w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none transition-all placeholder:text-zinc-600 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40 disabled:opacity-60";

export function SectionCard({ title, description, children, footer, testid }) {
  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950 p-6" data-testid={testid}>
      <div className="mb-5">
        <h2 className="text-base font-semibold text-zinc-100">{title}</h2>
        {description && <p className="mt-1 text-sm text-zinc-500">{description}</p>}
      </div>
      <div className="space-y-4">{children}</div>
      {footer}
    </div>
  );
}

export function Field({ label, children, hint }) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-zinc-400">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-zinc-600">{hint}</p>}
    </div>
  );
}

export function TextField({ label, value, onChange, placeholder, type = "text", disabled, testid, hint }) {
  return (
    <Field label={label} hint={hint}>
      <input type={type} value={value ?? ""} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        disabled={disabled} data-testid={testid} className={inputCls} />
    </Field>
  );
}

export function TextArea({ label, value, onChange, placeholder, rows = 3, testid, hint }) {
  return (
    <Field label={label} hint={hint}>
      <textarea value={value ?? ""} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} rows={rows}
        data-testid={testid} className={`${inputCls} resize-none`} />
    </Field>
  );
}

export function SelectField({ label, value, onChange, options, testid, hint }) {
  return (
    <Field label={label} hint={hint}>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger data-testid={testid} className="border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
        <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
          {options.map((o) => (typeof o === "string"
            ? <SelectItem key={o} value={o}>{o}</SelectItem>
            : <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>))}
        </SelectContent>
      </Select>
    </Field>
  );
}

export function ColorField({ label, value, onChange, testid }) {
  return (
    <Field label={label}>
      <div className="flex items-center gap-3">
        <input type="color" value={value || "#8b5cf6"} onChange={(e) => onChange(e.target.value)} data-testid={testid}
          className="h-9 w-12 cursor-pointer rounded-lg border border-white/10 bg-zinc-900" />
        <input value={value ?? ""} onChange={(e) => onChange(e.target.value)} className={`${inputCls} font-mono`} placeholder="#8b5cf6" />
      </div>
    </Field>
  );
}

export function ToggleRow({ label, description, checked, onChange, testid }) {
  return (
    <div className="flex items-center justify-between border-b border-white/5 py-3 last:border-0">
      <div className="pr-4">
        <p className="text-sm font-medium text-zinc-100">{label}</p>
        {description && <p className="text-xs text-zinc-500">{description}</p>}
      </div>
      <Switch checked={checked} onCheckedChange={onChange} data-testid={testid} className="data-[state=checked]:bg-violet-600" />
    </div>
  );
}

export function ImageUpload({ label, value, onChange, testid, hint }) {
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);
  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      const res = await settingsApi.uploadImage(file);
      onChange(res.url);
      toast.success("Image uploaded");
    } catch (err) { toast.error(err.message); }
    finally { setBusy(false); if (ref.current) ref.current.value = ""; }
  };
  return (
    <Field label={label} hint={hint}>
      <div className="flex items-center gap-4">
        <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-zinc-900">
          {value ? <img src={settingsApi.imageUrl(value)} alt="Logo preview" className="h-full w-full object-contain" /> : <ImageIcon className="h-6 w-6 text-zinc-600" />}
        </div>
        <input ref={ref} type="file" accept="image/*" onChange={upload} className="hidden" data-testid={`${testid}-input`} />
        <button type="button" onClick={() => ref.current?.click()} disabled={busy} data-testid={testid}
          className="flex items-center gap-2 rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 transition-all hover:border-violet-500/40 disabled:opacity-60">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />} Upload
        </button>
        {value && <button type="button" onClick={() => onChange("")} className="text-xs text-zinc-500 hover:text-red-400">Remove</button>}
      </div>
    </Field>
  );
}

export function SaveButton({ onClick, saving, testid, label = "Save changes" }) {
  return (
    <button onClick={onClick} disabled={saving} data-testid={testid}
      className="mt-2 flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-60 glow-violet">
      {saving && <Loader2 className="h-4 w-4 animate-spin" />} {label}
    </button>
  );
}
