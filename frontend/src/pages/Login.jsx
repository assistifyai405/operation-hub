import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowRight, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { AuthShell, inputClass } from "@/components/AuthShell";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("jordan@assistify.io");
  const [password, setPassword] = useState("Assistify2026!");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password, remember);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to your operating system."
      footer={
        <p className="mt-6 text-center text-xs text-zinc-500">
          Don't have an account?{" "}
          <Link to="/register" className="text-violet-400 hover:text-violet-300" data-testid="go-register-link">Start free trial</Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="mt-8 space-y-4" data-testid="login-form">
        {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300" data-testid="login-error">{error}</div>}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email" className={inputClass} placeholder="you@company.com" />
        </div>
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <label className="block text-xs font-medium text-zinc-400">Password</label>
            <Link to="/forgot-password" className="text-xs text-violet-400 hover:text-violet-300" data-testid="forgot-link">Forgot?</Link>
          </div>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password" className={inputClass} placeholder="••••••••" />
        </div>
        <label className="flex items-center gap-2 text-xs text-zinc-400">
          <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} data-testid="remember-me" className="h-4 w-4 rounded border-white/10 bg-zinc-950 accent-violet-600" />
          Remember me for 7 days
        </label>
        <button type="submit" disabled={loading} data-testid="login-submit" className="group flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 py-2.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-60 glow-violet">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Sign in <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" /></>}
        </button>
      </form>
    </AuthShell>
  );
}
