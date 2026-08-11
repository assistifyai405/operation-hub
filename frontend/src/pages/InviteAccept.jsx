import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowRight, Loader2, ShieldAlert, CheckCircle2, Clock } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { teamApi } from "@/lib/api";
import { AuthShell } from "@/components/AuthShell";

export default function InviteAccept() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { user, setUser, logout } = useAuth();
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const data = await teamApi.previewInvitation(token);
        if (!cancelled) setPreview(data);
      } catch (e) {
        if (!cancelled) {
          setPreview(null);
          setError(e.message || "Invalid invitation");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [token]);

  // Persist token so login/register can continue the flow
  useEffect(() => {
    if (token) sessionStorage.setItem("pending_invite_token", token);
  }, [token]);

  const accept = async () => {
    setAccepting(true);
    try {
      const res = await teamApi.acceptInvitation(token);
      if (res.user) setUser(res.user);
      sessionStorage.removeItem("pending_invite_token");
      toast.success(`Joined ${preview?.organization?.name || "the team"}`);
      navigate("/dashboard");
    } catch (e) {
      toast.error(e.message);
      setError(e.message);
    } finally {
      setAccepting(false);
    }
  };

  if (loading || user === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-zinc-500" data-testid="invite-loading">
        <Loader2 className="h-7 w-7 animate-spin" aria-label="Loading invitation" />
      </div>
    );
  }

  const status = preview?.status;
  const emailMatch = user && user !== false && preview && user.email?.toLowerCase() === preview.email?.toLowerCase();

  let body;
  if (!preview || status === "invalid" || error && !preview) {
    body = (
      <div className="mt-8 rounded-xl border border-red-500/30 bg-red-500/10 p-5 text-center" data-testid="invite-invalid">
        <ShieldAlert className="mx-auto h-8 w-8 text-red-400" />
        <p className="mt-3 text-sm font-semibold text-red-200">Invitation not found</p>
        <p className="mt-1 text-xs text-red-300/80">{error || "This link is invalid."}</p>
        <Link to="/login" className="mt-4 inline-block text-sm text-brand-400 hover:text-brand-300">Go to sign in</Link>
      </div>
    );
  } else if (status === "expired") {
    body = (
      <div className="mt-8 rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 text-center" data-testid="invite-expired">
        <Clock className="mx-auto h-8 w-8 text-amber-400" />
        <p className="mt-3 text-sm font-semibold text-amber-100">Invitation expired</p>
        <p className="mt-1 text-xs text-amber-200/80">Ask your admin to send a new invite to {preview.email}.</p>
      </div>
    );
  } else if (status === "cancelled") {
    body = (
      <div className="mt-8 rounded-xl border border-zinc-700 bg-zinc-900 p-5 text-center" data-testid="invite-cancelled">
        <p className="text-sm font-semibold text-zinc-200">Invitation cancelled</p>
        <p className="mt-1 text-xs text-zinc-500">This invitation is no longer valid.</p>
      </div>
    );
  } else if (status === "accepted") {
    body = (
      <div className="mt-8 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-5 text-center" data-testid="invite-used">
        <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-400" />
        <p className="mt-3 text-sm font-semibold text-emerald-100">Already used</p>
        <p className="mt-1 text-xs text-emerald-200/80">This invitation was already accepted.</p>
        <Link to="/login" className="mt-4 inline-block text-sm text-brand-400">Sign in</Link>
      </div>
    );
  } else {
    // pending
    body = (
      <div className="mt-8 space-y-4" data-testid="invite-pending">
        <div className="rounded-xl border border-white/10 bg-zinc-950/80 p-5">
          <p className="text-xs uppercase tracking-wide text-zinc-500">You're invited to</p>
          <p className="mt-1 text-xl font-semibold text-zinc-50" data-testid="invite-org-name">{preview.organization?.name}</p>
          <p className="mt-3 text-sm text-zinc-400">
            Role: <span className="font-medium capitalize text-brand-300" data-testid="invite-role">{preview.role}</span>
          </p>
          <p className="mt-1 text-sm text-zinc-400">
            Invited email: <span className="text-zinc-200" data-testid="invite-email">{preview.email}</span>
          </p>
          {preview.invitedByName && (
            <p className="mt-1 text-xs text-zinc-500">From {preview.invitedByName}</p>
          )}
        </div>

        {user && user !== false ? (
          emailMatch ? (
            <button
              type="button"
              disabled={accepting}
              onClick={accept}
              data-testid="invite-accept-btn"
              className="group flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-60 glow-brand"
            >
              {accepting ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Accept invitation <ArrowRight className="h-4 w-4" /></>}
            </button>
          ) : (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100" data-testid="invite-email-mismatch">
              <p>You're signed in as <strong>{user.email}</strong>, but this invite is for <strong>{preview.email}</strong>.</p>
              <button
                type="button"
                className="mt-3 text-brand-300 underline"
                data-testid="invite-switch-account"
                onClick={async () => { await logout(); navigate(`/login?invite=${encodeURIComponent(token)}&email=${encodeURIComponent(preview.email)}`); }}
              >
                Sign out and continue
              </button>
            </div>
          )
        ) : (
          <div className="space-y-3" data-testid="invite-auth-actions">
            {preview.accountExists ? (
              <Link
                to={`/login?invite=${encodeURIComponent(token)}&email=${encodeURIComponent(preview.email)}`}
                data-testid="invite-go-login"
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-500"
              >
                Sign in to accept <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <Link
                to={`/register?invite=${encodeURIComponent(token)}&email=${encodeURIComponent(preview.email)}`}
                data-testid="invite-go-register"
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-500"
              >
                Create account to join <ArrowRight className="h-4 w-4" />
              </Link>
            )}
            <p className="text-center text-xs text-zinc-500">
              {preview.accountExists ? (
                <>New here? <Link className="text-brand-400" to={`/register?invite=${encodeURIComponent(token)}&email=${encodeURIComponent(preview.email)}`}>Register</Link></>
              ) : (
                <>Already have an account? <Link className="text-brand-400" to={`/login?invite=${encodeURIComponent(token)}&email=${encodeURIComponent(preview.email)}`}>Sign in</Link></>
              )}
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <AuthShell
      title="Team invitation"
      subtitle="Join your teammates on Assistify OS."
      footer={null}
    >
      {body}
    </AuthShell>
  );
}
