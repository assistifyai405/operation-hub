import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { Loader2, CheckCircle2 } from "lucide-react";
import { authApi } from "@/lib/api";
import { AuthShell, inputClass } from "@/components/AuthShell";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }
    if (password !== confirm) { setError("Passwords do not match"); return; }
    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
      setTimeout(() => navigate("/login"), 1800);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <AuthShell title="Invalid link" subtitle="This reset link is missing or malformed.">
        <p className="mt-6 text-sm text-zinc-400"><Link to="/forgot-password" className="text-violet-400 hover:text-violet-300">Request a new link</Link></p>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Set a new password" subtitle="Choose a strong password you'll remember.">
      {done ? (
        <div className="mt-8 flex items-center gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300" data-testid="reset-success">
          <CheckCircle2 className="h-5 w-5" /> Password updated. Redirecting to sign in…
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-8 space-y-4" data-testid="reset-form">
          {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300" data-testid="reset-error">{error}</div>}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">New password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required data-testid="reset-password" className={inputClass} placeholder="At least 8 characters" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Confirm password</label>
            <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required data-testid="reset-confirm" className={inputClass} placeholder="Re-enter password" />
          </div>
          <button type="submit" disabled={loading} data-testid="reset-submit" className="flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 py-2.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-60 glow-violet">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Update password"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
