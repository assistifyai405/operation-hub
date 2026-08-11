import { useCallback, useEffect, useState } from "react";
import {
  Loader2, UserPlus, Trash2, Crown, Shield, User, Mail, X, ArrowRightLeft,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { teamApi } from "@/lib/api";
import { SectionCard, TextField, SelectField } from "@/components/settings/fields";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const ROLE_OPTIONS = [
  { value: "member", label: "Member" },
  { value: "admin", label: "Admin" },
];

const roleIcon = (role) => {
  if (role === "owner") return <Crown className="h-3.5 w-3.5 text-amber-400" />;
  if (role === "admin") return <Shield className="h-3.5 w-3.5 text-violet-400" />;
  return <User className="h-3.5 w-3.5 text-zinc-500" />;
};

const fmtDate = (d) => {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "—";
  }
};

export function TeamSection() {
  const { user, setUser, refreshUser } = useAuth();
  const [data, setData] = useState(null);
  const [invites, setInvites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [inviteForm, setInviteForm] = useState({ email: "", role: "member" });
  const [inviting, setInviting] = useState(false);
  const [confirm, setConfirm] = useState(null); // { type, member?, invitation? }

  const canManage = user?.role === "owner" || user?.role === "admin";
  const isOwner = user?.role === "owner";

  const load = useCallback(async () => {
    setError("");
    try {
      const membersRes = await teamApi.members();
      setData(membersRes);
      if (canManage) {
        const inv = await teamApi.invitations().catch(() => ({ invitations: [] }));
        setInvites(inv.invitations || []);
      } else {
        setInvites([]);
      }
    } catch (e) {
      setError(e.message || "Failed to load team");
    } finally {
      setLoading(false);
    }
  }, [canManage]);

  useEffect(() => { load(); }, [load]);

  const sendInvite = async () => {
    if (!inviteForm.email.trim()) { toast.error("Email is required"); return; }
    setInviting(true);
    try {
      const res = await teamApi.invite({ email: inviteForm.email.trim(), role: inviteForm.role });
      if (res.emailDelivery === "manual" || res.invitationLink) {
        toast.message("Invitation created — email sending is disabled", {
          description: res.invitationLink
            ? "Share this invite link manually (shown once in development)."
            : (res.emailDeliveryNote || "Share the invite link manually with the recipient."),
        });
        if (res.invitationLink) {
          toast.message("Dev invitation link", { description: res.invitationLink });
        }
      } else {
        toast.success(`Invitation sent to ${res.email}`);
      }
      setInviteForm({ email: "", role: "member" });
      await load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setInviting(false);
    }
  };

  const changeRole = async (member, role) => {
    try {
      await teamApi.changeRole(member.id, role);
      toast.success(`Updated ${member.firstName || member.email} to ${role}`);
      await load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const runConfirm = async () => {
    if (!confirm) return;
    try {
      if (confirm.type === "remove") {
        await teamApi.removeMember(confirm.member.id);
        toast.success("Member removed");
        if (confirm.member.id === user.id) {
          const me = await refreshUser();
          setUser(me);
        }
      } else if (confirm.type === "cancel-invite") {
        await teamApi.cancelInvitation(confirm.invitation.id);
        toast.success("Invitation cancelled");
      } else if (confirm.type === "transfer") {
        await teamApi.transferOwnership(confirm.member.id);
        toast.success("Ownership transferred");
        const me = await refreshUser();
        setUser(me);
      }
      setConfirm(null);
      await load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-zinc-500" data-testid="team-loading">
        <Loader2 className="h-6 w-6 animate-spin" aria-label="Loading team" />
      </div>
    );
  }

  if (error) {
    return (
      <SectionCard title="Team" description="People in your organization." testid="settings-team">
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300" data-testid="team-error">
          {error}
          <button type="button" onClick={() => { setLoading(true); load(); }} className="ml-3 text-violet-300 underline">Retry</button>
        </div>
      </SectionCard>
    );
  }

  const members = data?.members || [];
  const pending = invites.filter((i) => i.status === "pending");
  const seats = data?.seats;

  return (
    <div className="space-y-6" data-testid="settings-team">
      <SectionCard
        title="Team"
        description={`${data?.organization?.name || "Organization"} · ${members.length} member${members.length === 1 ? "" : "s"}`}
        testid="team-members-card"
      >
        {seats && (
          <p className="text-xs text-zinc-500" data-testid="team-seat-count">
            Seats in use: {seats.active_members} active
            {seats.pending_invitations ? ` · ${seats.pending_invitations} pending invite${seats.pending_invitations === 1 ? "" : "s"}` : ""}
            {seats.seat_limit == null ? " · unlimited (billing not enforced)" : ` · limit ${seats.seat_limit}`}
          </p>
        )}

        {members.length === 0 ? (
          <div className="rounded-xl border border-dashed border-white/10 py-12 text-center text-sm text-zinc-500" data-testid="team-empty">
            No members yet.
          </div>
        ) : (
          <div className="overflow-x-auto" data-testid="team-members-list">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-zinc-500">
                  <th className="pb-2 pr-3 font-medium">Member</th>
                  <th className="pb-2 pr-3 font-medium">Role</th>
                  <th className="pb-2 pr-3 font-medium">Status</th>
                  <th className="pb-2 pr-3 font-medium">Joined</th>
                  <th className="pb-2 font-medium"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id} className="border-b border-white/5" data-testid={`team-member-${m.id}`}>
                    <td className="py-3 pr-3">
                      <div className="flex flex-col">
                        <span className="font-medium text-zinc-100">
                          {[m.firstName, m.lastName].filter(Boolean).join(" ") || m.email}
                          {m.isCurrentUser && <span className="ml-2 rounded bg-violet-600/20 px-1.5 py-0.5 text-[10px] text-violet-300">You</span>}
                        </span>
                        <span className="text-xs text-zinc-500">{m.email}</span>
                      </div>
                    </td>
                    <td className="py-3 pr-3">
                      <span className="inline-flex items-center gap-1.5 capitalize text-zinc-300">
                        {roleIcon(m.role)} {m.role}
                      </span>
                    </td>
                    <td className="py-3 pr-3">
                      <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-400">{m.status}</span>
                    </td>
                    <td className="py-3 pr-3 text-zinc-400">{fmtDate(m.joinedAt)}</td>
                    <td className="py-3">
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        {canManage && !m.isOwner && !m.isCurrentUser && (
                          <select
                            aria-label={`Change role for ${m.email}`}
                            value={m.role}
                            onChange={(e) => changeRole(m, e.target.value)}
                            data-testid={`team-role-${m.id}`}
                            className="rounded-md border border-white/10 bg-zinc-900 px-2 py-1 text-xs text-zinc-200"
                          >
                            {ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                          </select>
                        )}
                        {isOwner && !m.isCurrentUser && !m.isOwner && (
                          <button
                            type="button"
                            aria-label={`Transfer ownership to ${m.email}`}
                            data-testid={`team-transfer-${m.id}`}
                            onClick={() => setConfirm({ type: "transfer", member: m })}
                            className="inline-flex items-center gap-1 rounded-md border border-amber-500/30 px-2 py-1 text-xs text-amber-300 hover:bg-amber-500/10"
                          >
                            <ArrowRightLeft className="h-3 w-3" /> Transfer
                          </button>
                        )}
                        {((canManage && !m.isOwner && !m.isCurrentUser) || (m.isCurrentUser && !m.isOwner)) && (
                          <button
                            type="button"
                            aria-label={m.isCurrentUser ? "Leave organization" : `Remove ${m.email}`}
                            data-testid={`team-remove-${m.id}`}
                            onClick={() => setConfirm({ type: "remove", member: m })}
                            className="inline-flex items-center gap-1 rounded-md border border-red-500/30 px-2 py-1 text-xs text-red-300 hover:bg-red-500/10"
                          >
                            <Trash2 className="h-3 w-3" /> {m.isCurrentUser ? "Leave" : "Remove"}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {canManage && (
        <SectionCard title="Invite member" description="Invite a teammate to this organization." testid="team-invite-card">
          <p className="mb-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/90" data-testid="team-invite-email-note">
            When email sending is disabled, invitations are created but not emailed — you must share the invite link manually (development shows the link once).
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_160px_auto]">
            <TextField
              label="Email"
              value={inviteForm.email}
              onChange={(v) => setInviteForm((f) => ({ ...f, email: v }))}
              placeholder="colleague@company.com"
              testid="team-invite-email"
            />
            <SelectField
              label="Role"
              value={inviteForm.role}
              onChange={(v) => setInviteForm((f) => ({ ...f, role: v }))}
              options={ROLE_OPTIONS}
              testid="team-invite-role"
            />
            <div className="flex items-end">
              <button
                type="button"
                disabled={inviting}
                onClick={sendInvite}
                data-testid="team-invite-submit"
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-60"
              >
                {inviting ? <Loader2 className="h-4 w-4 animate-spin" /> : <><UserPlus className="h-4 w-4" /> Invite</>}
              </button>
            </div>
          </div>

          {pending.length > 0 && (
            <div className="mt-6 space-y-2" data-testid="team-pending-invites">
              <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Pending invitations</p>
              {pending.map((inv) => (
                <div key={inv.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-zinc-900/50 px-3 py-2" data-testid={`team-invite-${inv.id}`}>
                  <div className="flex items-center gap-2 text-sm text-zinc-300">
                    <Mail className="h-4 w-4 text-zinc-500" />
                    <span>{inv.email}</span>
                    <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] uppercase text-zinc-400">{inv.role}</span>
                    <span className="text-xs text-zinc-600">expires {fmtDate(inv.expiresAt)}</span>
                  </div>
                  <button
                    type="button"
                    aria-label={`Cancel invitation to ${inv.email}`}
                    data-testid={`team-cancel-invite-${inv.id}`}
                    onClick={() => setConfirm({ type: "cancel-invite", invitation: inv })}
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                  >
                    <X className="h-3.5 w-3.5" /> Cancel
                  </button>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}

      <AlertDialog open={!!confirm} onOpenChange={(o) => !o && setConfirm(null)}>
        <AlertDialogContent className="border-white/10 bg-zinc-950 text-zinc-100">
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirm?.type === "transfer" && "Transfer ownership?"}
              {confirm?.type === "remove" && (confirm.member?.isCurrentUser ? "Leave organization?" : "Remove member?")}
              {confirm?.type === "cancel-invite" && "Cancel invitation?"}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">
              {confirm?.type === "transfer" && (
                <>You will become an admin. <strong className="text-zinc-200">{confirm.member?.email}</strong> will become the owner.</>
              )}
              {confirm?.type === "remove" && !confirm.member?.isCurrentUser && (
                <>Remove <strong className="text-zinc-200">{confirm.member?.email}</strong> from this organization?</>
              )}
              {confirm?.type === "remove" && confirm.member?.isCurrentUser && (
                <>You will leave this organization and get a new personal workspace.</>
              )}
              {confirm?.type === "cancel-invite" && (
                <>Cancel the pending invite to <strong className="text-zinc-200">{confirm.invitation?.email}</strong>?</>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 bg-zinc-900 text-zinc-200">Cancel</AlertDialogCancel>
            <AlertDialogAction
              data-testid="team-confirm-action"
              onClick={(e) => { e.preventDefault(); runConfirm(); }}
              className="bg-violet-600 text-white hover:bg-violet-500"
            >
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
