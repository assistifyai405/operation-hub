import { useState } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { ArrowRight, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { AuthShell, inputClass } from "@/components/AuthShell";
import { events } from "@/lib/analytics";
import { toast } from "sonner";

export default function Register() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const inviteToken = params.get("invite") || sessionStorage.getItem("pending_invite_token") || "";
  const { register } = useAuth();
  const [form, setForm] = useState({
    firstName: "",
    lastName: "",
    email: params.get("email") || "",
    company: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.password.length < 8) { setError("Password must be at least 8 characters"); return; }
    setLoading(true);
    try {
      const payload = { ...form };
      if (inviteToken) payload.invitationToken = inviteToken;
      const data = await register(payload);
      events.userRegistered({ via_invite: Boolean(inviteToken) });
      if (data.verificationLink) toast.success("Account created! Verify your email from Settings anytime.");
      sessionStorage.removeItem("pending_invite_token");
      if (data.joinedViaInvitation) {
        toast.success("Welcome to the team");
        navigate("/dashboard");
      } else {
        navigate("/onboarding");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title={inviteToken ? "Join your team" : "Create your account"}
      subtitle={inviteToken ? "Create an account to accept your invitation." : "Set up your workspace to manage clients, projects, and AI in one place."}
      footer={
        <p className="mt-6 text-center text-xs text-zinc-500">
          Already have an account?{" "}
          <Link
            to={inviteToken ? `/login?invite=${encodeURIComponent(inviteToken)}&email=${encodeURIComponent(form.email)}` : "/login"}
            className="text-violet-400 hover:text-violet-300"
            data-testid="go-login-link"
          >
            Sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="mt-8 space-y-4" data-testid="register-form">
        {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300" data-testid="register-error">{error}</div>}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">First name</label>
            <input value={form.firstName} onChange={set("firstName")} required data-testid="register-firstname" className={inputClass} placeholder="Jordan" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Last name</label>
            <input value={form.lastName} onChange={set("lastName")} data-testid="register-lastname" className={inputClass} placeholder="Reyes" />
          </div>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Work email</label>
          <input type="email" value={form.email} onChange={set("email")} required data-testid="register-email" className={inputClass} placeholder="you@company.com" readOnly={!!inviteToken && !!params.get("email")} />
        </div>
        {!inviteToken && (
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Company <span className="text-zinc-600">(optional)</span></label>
            <input value={form.company} onChange={set("company")} data-testid="register-company" className={inputClass} placeholder="Acme Studio" />
          </div>
        )}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Password</label>
          <input type="password" value={form.password} onChange={set("password")} required data-testid="register-password" className={inputClass} placeholder="At least 8 characters" />
        </div>
        <button type="submit" disabled={loading} data-testid="register-submit" className="group flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 py-2.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-60 glow-violet">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <>{inviteToken ? "Join organization" : "Create account"} <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" /></>}
        </button>
      </form>
    </AuthShell>
  );
}
