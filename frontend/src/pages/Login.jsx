import { useNavigate } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";

export default function Login() {
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    navigate("/dashboard");
  };

  return (
    <div className="grid min-h-screen grid-cols-1 bg-black lg:grid-cols-2">
      {/* Left brand panel */}
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
          <div className="mt-8 flex items-center gap-6">
            {["37 projects", "128 clients", "9.4k AI runs"].map((s) => (
              <div key={s} className="text-sm font-medium text-zinc-300">{s}</div>
            ))}
          </div>
        </div>
        <p className="relative z-10 text-xs text-zinc-600">© 2026 Assistify OS. Crafted for entrepreneurs.</p>
      </div>

      {/* Right form */}
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="mb-8 lg:hidden flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 glow-violet">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <p className="text-lg font-bold tracking-tight">Assistify <span className="text-violet-400">OS</span></p>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-50">Welcome back</h1>
          <p className="mt-2 text-sm text-zinc-400">Sign in to your operating system.</p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4" data-testid="login-form">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">Email</label>
              <input
                type="email"
                defaultValue="jordan@assistify.io"
                data-testid="login-email"
                className="w-full rounded-lg border border-white/10 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-100 outline-none transition-all placeholder:text-zinc-600 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40"
                placeholder="you@company.com"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">Password</label>
              <input
                type="password"
                defaultValue="password"
                data-testid="login-password"
                className="w-full rounded-lg border border-white/10 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-100 outline-none transition-all placeholder:text-zinc-600 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              data-testid="login-submit"
              className="group flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 py-2.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet"
            >
              Sign in
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </button>
          </form>
          <p className="mt-6 text-center text-xs text-zinc-500">
            Don't have an account? <span className="cursor-pointer text-violet-400 hover:text-violet-300">Start free trial</span>
          </p>
        </div>
      </div>
    </div>
  );
}
