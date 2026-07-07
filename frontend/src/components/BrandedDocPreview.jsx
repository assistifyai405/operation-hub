import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Eye } from "lucide-react";
import { settingsApi } from "@/lib/api";

const FOOTER_KEY = { proposal: "proposalFooter", contract: "contractFooter", invoice: "invoiceFooter" };

export default function BrandedDocPreview({ docType = "proposal" }) {
  const [s, setS] = useState(null);
  const [open, setOpen] = useState(true);

  useEffect(() => { settingsApi.get().then(setS).catch(() => {}); }, []);
  if (!s) return null;

  const b = s.branding, o = s.organization;
  const primary = b.primaryColor || "#8b5cf6";
  const logo = b.pdfLogo || b.logo || o.logo;
  const footer = b[FOOTER_KEY[docType]] || o.name;
  const lines = [o.address, o.businessEmail, o.phone, o.website].filter(Boolean);
  const ids = [o.vatNumber && `VAT: ${o.vatNumber}`, o.kvkNumber && `KVK: ${o.kvkNumber}`].filter(Boolean);

  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-zinc-950" data-testid={`branded-preview-${docType}`}>
      <button onClick={() => setOpen((v) => !v)} className="flex w-full items-center gap-2 border-b border-white/5 px-4 py-2.5 text-left" data-testid="branded-preview-toggle">
        <Eye className="h-4 w-4 text-violet-400" />
        <span className="text-sm font-medium text-zinc-200">Branded preview</span>
        <span className="text-xs text-zinc-500">— how your exported {docType} will look</span>
        {open ? <ChevronUp className="ml-auto h-4 w-4 text-zinc-500" /> : <ChevronDown className="ml-auto h-4 w-4 text-zinc-500" />}
      </button>
      {open && (
        <div className="p-4">
          <div className="mx-auto max-w-2xl rounded-lg bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                {logo ? (
                  <img src={settingsApi.imageUrl(logo)} alt="Company logo" className="mb-2 max-h-12 object-contain" data-testid="branded-preview-logo" />
                ) : (
                  <p className="text-lg font-bold text-zinc-900">{o.name}</p>
                )}
                <div className="space-y-0.5 text-[11px] leading-tight text-zinc-500">
                  {logo && <p className="font-semibold text-zinc-700">{o.name}</p>}
                  {lines.map((l, i) => <p key={i}>{l}</p>)}
                  {ids.length > 0 && <p>{ids.join(" · ")}</p>}
                </div>
              </div>
              <span className="shrink-0 text-2xl font-bold uppercase tracking-tight" style={{ color: primary }}>{docType}</span>
            </div>
            <div className="my-4 h-1 w-full rounded" style={{ backgroundColor: primary }} />
            <div className="space-y-1.5">
              <div className="h-2 w-3/4 rounded bg-zinc-200" />
              <div className="h-2 w-full rounded bg-zinc-100" />
              <div className="h-2 w-5/6 rounded bg-zinc-100" />
            </div>
            <div className="mt-6 flex items-center justify-between border-t pt-2" style={{ borderColor: primary + "40" }}>
              <p className="truncate text-[10px] text-zinc-400" data-testid="branded-preview-footer">{footer}</p>
              <p className="text-[10px] text-zinc-400">Page 1</p>
            </div>
          </div>
          <p className="mt-2 text-center text-xs text-zinc-600">Edit logo, colors and footers in <span className="text-violet-400">Settings → Branding</span>.</p>
        </div>
      )}
    </div>
  );
}
