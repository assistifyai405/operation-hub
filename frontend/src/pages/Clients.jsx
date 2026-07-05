import { Search, Plus, MoreHorizontal, Mail } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { clients } from "@/data/mock";

const statusStyle = {
  Active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Lead: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  Churned: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
};

export default function Clients() {
  return (
    <div className="space-y-5" data-testid="clients-page">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-zinc-400">Manage your {clients.length} clients and relationships.</p>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input placeholder="Search clients" data-testid="clients-search" className="rounded-lg border border-white/10 bg-zinc-950 py-2 pl-9 pr-3 text-sm text-zinc-200 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
          </div>
          <button data-testid="add-client-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">
            <Plus className="h-4 w-4" /> Add Client
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-white/10 bg-zinc-950">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-white/10 bg-zinc-900/40 text-zinc-400">
            <tr>
              <th className="px-5 py-3 font-medium">Client</th>
              <th className="px-5 py-3 font-medium">Contact</th>
              <th className="hidden px-5 py-3 font-medium md:table-cell">Value</th>
              <th className="hidden px-5 py-3 font-medium sm:table-cell">Projects</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody>
            {clients.map((c) => (
              <tr key={c.id} className="border-b border-white/5 transition-colors hover:bg-zinc-900/40" data-testid={`client-row-${c.id}`}>
                <td className="px-5 py-3">
                  <div className="flex items-center gap-3">
                    <Avatar className="h-9 w-9 border border-white/10"><AvatarImage src={c.avatar} /><AvatarFallback>{c.name[0]}</AvatarFallback></Avatar>
                    <span className="font-medium text-zinc-100">{c.name}</span>
                  </div>
                </td>
                <td className="px-5 py-3">
                  <p className="text-zinc-200">{c.contact}</p>
                  <p className="flex items-center gap-1 text-xs text-zinc-500"><Mail className="h-3 w-3" />{c.email}</p>
                </td>
                <td className="hidden px-5 py-3 font-semibold text-violet-400 md:table-cell">{c.value}</td>
                <td className="hidden px-5 py-3 text-zinc-300 sm:table-cell">{c.projects}</td>
                <td className="px-5 py-3">
                  <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusStyle[c.status]}`}>{c.status}</span>
                </td>
                <td className="px-5 py-3 text-right">
                  <button className="text-zinc-500 hover:text-zinc-200"><MoreHorizontal className="h-4 w-4" /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
