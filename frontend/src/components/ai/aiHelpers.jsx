import {
  FileText, ScrollText, Receipt, Mail, ListChecks, Users, FolderKanban,
  CheckSquare, BadgeDollarSign, BarChart3, Sparkles, AlertTriangle, Clock, Folder,
  Calendar, Copy,
} from "lucide-react";

const ICONS = {
  "file-text": FileText, "scroll-text": ScrollText, "receipt": Receipt, "mail": Mail,
  "list-checks": ListChecks, "users": Users, "folder-kanban": FolderKanban,
  "check-square": CheckSquare, "badge-dollar-sign": BadgeDollarSign, "bar-chart-3": BarChart3,
  "sparkles": Sparkles, "alert": AlertTriangle, "clock": Clock, "folder": Folder,
  "calendar": Calendar, "copy": Copy,
};

export function AiIcon({ name, className }) {
  const Cmp = ICONS[name] || Sparkles;
  return <Cmp className={className} />;
}

export function fmtDuration(mins) {
  const m = Math.max(0, Math.round(mins || 0));
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r ? `${h}h ${r}m` : `${h}h`;
}

export function relTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
