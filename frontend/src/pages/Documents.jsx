import { Plus, Upload, FileText, FileImage, FileSpreadsheet, FileArchive, File } from "lucide-react";
import { documents } from "@/data/mock";

const typeIcon = {
  PDF: { icon: FileText, color: "text-red-400 bg-red-500/10" },
  Figma: { icon: FileImage, color: "text-pink-400 bg-pink-500/10" },
  Doc: { icon: FileText, color: "text-blue-400 bg-blue-500/10" },
  Sheet: { icon: FileSpreadsheet, color: "text-emerald-400 bg-emerald-500/10" },
  Archive: { icon: FileArchive, color: "text-amber-400 bg-amber-500/10" },
};

export default function Documents() {
  return (
    <div className="space-y-5" data-testid="documents-page">
      <div className="flex items-center justify-between">
        <p className="text-sm text-zinc-400">{documents.length} files in your library.</p>
        <button data-testid="upload-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">
          <Upload className="h-4 w-4" /> Upload
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {documents.map((d) => {
          const t = typeIcon[d.type] || { icon: File, color: "text-zinc-400 bg-zinc-500/10" };
          const Icon = t.icon;
          return (
            <div key={d.id} className="group rounded-xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-violet-500/40" data-testid={`doc-${d.id}`}>
              <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${t.color}`}>
                <Icon className="h-6 w-6" />
              </div>
              <p className="mt-3 truncate text-sm font-medium text-zinc-100" title={d.name}>{d.name}</p>
              <p className="mt-0.5 truncate text-xs text-zinc-500">{d.client}</p>
              <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
                <span>{d.size}</span><span>{d.date}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
