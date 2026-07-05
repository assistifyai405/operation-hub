import { useEffect, useState, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import { authApi } from "@/lib/api";
import { AuthShell } from "@/components/AuthShell";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [status, setStatus] = useState("verifying"); // verifying | ok | error
  const [message, setMessage] = useState("");
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    if (!token) { setStatus("error"); setMessage("Missing verification token."); return; }
    authApi.verifyEmail(token)
      .then(() => { setStatus("ok"); setMessage("Your email has been verified."); })
      .catch((e) => { setStatus("error"); setMessage(e.message); });
  }, [token]);

  return (
    <AuthShell
      title="Email verification"
      footer={<p className="mt-6 text-center text-xs text-zinc-500"><Link to="/dashboard" className="text-violet-400 hover:text-violet-300">Go to dashboard</Link></p>}
    >
      <div className="mt-8" data-testid="verify-email-status">
        {status === "verifying" && (
          <div className="flex items-center gap-3 text-sm text-zinc-300"><Loader2 className="h-5 w-5 animate-spin text-violet-400" /> Verifying your email…</div>
        )}
        {status === "ok" && (
          <div className="flex items-center gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300"><CheckCircle2 className="h-5 w-5" /> {message}</div>
        )}
        {status === "error" && (
          <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300"><XCircle className="h-5 w-5" /> {message}</div>
        )}
      </div>
    </AuthShell>
  );
}
