import { Sparkles } from "lucide-react";

export function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="grid min-h-screen grid-cols-1 bg-black lg:grid-cols-2">
      <div className="relative hidden overflow-hidden border-r border-white/10 lg:flex lg:flex-col lg:justify-between grid-bg p-12">
        <div className="absolute -left-32 top-1/3 h-96 w-96 rounded-full bg-violet-600/20 blur-[120px]" />
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 glow-violet">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <p className="text-lg font-bold tracking-tight">Assistify <span className="text-violet-400">OS</span></p>
        </div>
        <div className="relative z-10 max-w-md">
          <h2 className="text-4xl font-bold leading-tight tracking-tight text-zinc-50">
            Run your entire business from one intelligent workspace.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-zinc-400">
            Clients, projects, proposals, documents and a fleet of AI agents — unified in a single premium operating system.
          </p>
          <div className="mt-8 flex flex-col gap-2 text-sm font-medium text-zinc-300">
            <div>Clients, projects, and tasks in one workspace</div>
            <div>AI Agents and Copilot for daily operations</div>
            <div>Team settings, integrations, and document workflows</div>
          </div>
        </div>
        <p className="relative z-10 text-xs text-zinc-600">© 2026 Assistify OS. Crafted for entrepreneurs.</p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="mb-8 lg:hidden flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 glow-violet">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <p className="text-lg font-bold tracking-tight">Assistify <span className="text-violet-400">OS</span></p>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-50">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-zinc-400">{subtitle}</p>}
          {children}
          {footer}
        </div>
      </div>
    </div>
  );
}

export const inputClass =
  "w-full rounded-lg border border-white/10 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-100 outline-none transition-all placeholder:text-zinc-600 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40";
