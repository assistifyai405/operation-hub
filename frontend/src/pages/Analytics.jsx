import { useEffect, useState } from "react";
import { Users, FolderKanban, DollarSign, FileText, Loader2, TrendingUp, CheckSquare } from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import { analyticsApi } from "@/lib/api";
import { analyticsNl } from "@/lib/nlCopy";
import { toast } from "sonner";
import HelpTip from "@/components/HelpTip";

const money = (n) => `$${(n || 0).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;

const Card = ({ children, className = "" }) => (
  <div className={`rounded-xl border border-white/10 bg-zinc-950 p-5 ${className}`}>{children}</div>
);

export default function Analytics() {
  const [data, setData] = useState(null);

  useEffect(() => { analyticsApi.get().then(setData).catch((e) => toast.error(e.message)); }, []);

  if (!data) return <div className="flex items-center justify-center py-32 text-zinc-500" data-testid="analytics-loading"><Loader2 className="h-7 w-7 animate-spin" /></div>;

  const k = data.kpis;
  const kpis = [
    { label: analyticsNl.kpiPaid, value: money(k.total_paid), icon: DollarSign, color: "text-emerald-400", testid: "analytics-kpi-paid" },
    { label: analyticsNl.kpiInvoiced, value: money(k.total_invoiced), icon: TrendingUp, color: "text-violet-400", testid: "analytics-kpi-invoiced" },
    { label: analyticsNl.kpiClients, value: k.total_clients, icon: Users, color: "text-blue-400", testid: "analytics-kpi-clients" },
    { label: analyticsNl.kpiProjects, value: k.total_projects, icon: FolderKanban, color: "text-cyan-400", testid: "analytics-kpi-projects" },
  ];
  const docCounts = [
    { label: analyticsNl.proposals, value: k.proposals },
    { label: analyticsNl.contracts, value: k.contracts },
    { label: analyticsNl.invoices, value: k.invoices },
    { label: analyticsNl.documents, value: k.documents },
  ];
  const projectStatus = (data.project_status || []).map((row) => ({
    ...row,
    name: analyticsNl.projectStatus[row.name] || row.name,
  }));

  const emptyWorkspace = (k.total_clients || 0) === 0 && (k.total_projects || 0) === 0;
  const docsEmpty = docCounts.every((d) => (d.value || 0) === 0);
  const tasksTotal = (k.completed_tasks || 0) + (k.open_tasks || 0);

  return (
    <div className="space-y-6" data-testid="analytics-page">
      {emptyWorkspace && (
        <div className="rounded-2xl border border-dashed border-white/10 bg-zinc-950 px-4 py-8 text-center" data-testid="analytics-empty">
          <p className="text-sm font-semibold text-zinc-200">{analyticsNl.emptyTitle}</p>
          <p className="mx-auto mt-1 max-w-md text-xs text-zinc-500">
            {analyticsNl.emptyBody}
          </p>
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kp) => (
          <Card key={kp.label}>
            <div className="flex items-center justify-between">
              <p className="text-xs text-zinc-500">{kp.label}</p>
              <kp.icon className={`h-4 w-4 ${kp.color}`} />
            </div>
            <p className="mt-2 text-2xl font-bold text-zinc-50" data-testid={kp.testid}>{kp.value}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="mb-4 flex items-center gap-2">
            <h3 className="text-sm font-semibold text-zinc-100">{analyticsNl.revenueTitle}</h3>
            <HelpTip testid="analytics-revenue-help" text={analyticsNl.revenueHelp} />
          </div>
          {data.revenue_series.length === 0 ? (
            <p className="py-16 text-center text-sm text-zinc-500">{analyticsNl.revenueEmpty}</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={data.revenue_series}>
                <defs>
                  <linearGradient id="gInv" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4} /><stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} /></linearGradient>
                  <linearGradient id="gPaid" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#34d399" stopOpacity={0.4} /><stop offset="95%" stopColor="#34d399" stopOpacity={0} /></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="month" stroke="#71717a" fontSize={12} />
                <YAxis stroke="#71717a" fontSize={12} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8, color: "#e4e4e7" }} />
                <Legend />
                <Area type="monotone" dataKey="invoiced" name={analyticsNl.kpiInvoiced} stroke="#8b5cf6" fill="url(#gInv)" strokeWidth={2} />
                <Area type="monotone" dataKey="paid" name={analyticsNl.kpiPaid} stroke="#34d399" fill="url(#gPaid)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card>
          <h3 className="mb-4 text-sm font-semibold text-zinc-100">{analyticsNl.projectsTitle}</h3>
          {projectStatus.length === 0 ? (
            <p className="py-16 text-center text-sm text-zinc-500">{analyticsNl.projectsEmpty}</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={projectStatus} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3}>
                  {projectStatus.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8, color: "#e4e4e7" }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <h3 className="mb-4 text-sm font-semibold text-zinc-100">{analyticsNl.docsTitle}</h3>
          {docsEmpty ? (
            <p className="py-24 text-center text-sm text-zinc-500">{analyticsNl.docsEmpty}</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={docCounts}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="label" stroke="#71717a" fontSize={12} />
                <YAxis stroke="#71717a" fontSize={12} allowDecimals={false} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8, color: "#e4e4e7" }} cursor={{ fill: "#27272a55" }} />
                <Bar dataKey="value" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card>
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-zinc-100"><CheckSquare className="h-4 w-4 text-violet-400" /> {analyticsNl.tasksTitle}</h3>
          {tasksTotal === 0 ? (
            <p className="py-24 text-center text-sm text-zinc-500">{analyticsNl.tasksEmpty}</p>
          ) : (
            <div className="flex h-[240px] flex-col justify-center gap-6">
              <div>
                <div className="mb-2 flex items-center justify-between text-sm"><span className="text-zinc-400">{analyticsNl.completed}</span><span className="font-semibold text-emerald-400">{k.completed_tasks}</span></div>
                <div className="h-3 overflow-hidden rounded-full bg-zinc-800"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${(k.completed_tasks / tasksTotal) * 100}%` }} /></div>
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between text-sm"><span className="text-zinc-400">{analyticsNl.open}</span><span className="font-semibold text-violet-400">{k.open_tasks}</span></div>
                <div className="h-3 overflow-hidden rounded-full bg-zinc-800"><div className="h-full rounded-full bg-violet-500" style={{ width: `${(k.open_tasks / tasksTotal) * 100}%` }} /></div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
