import { useCallback, useEffect, useState } from "react";
import {
  Loader2, UserPlus, Trash2, Crown, Shield, User, Mail, X, ArrowRightLeft,
} from "lucide-react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/context/AuthContext";
import { teamApi } from "@/lib/api";
import { localizeApiError } from "@/i18n/errors";
import { SectionCard, TextField, SelectField } from "@/components/settings/fields";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const roleIcon = (role) => {
  if (role === "owner") return <Crown className="h-3.5 w-3.5 text-amber-400" />;
  if (role === "admin") return <Shield className="h-3.5 w-3.5 text-brand-400" />;
  return <User className="h-3.5 w-3.5 text-zinc-500" />;
};

const fmtDate = (d, locale) => {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString(locale, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "—";
  }
};

export function TeamSection() {
  const { t, i18n } = useTranslation();
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
  const roleOptions = [
    { value: "member", label: t("settings.team.roles.member") },
    { value: "admin", label: t("settings.team.roles.admin") },
  ];
  const roleLabel = (role) => role ? t(`settings.team.roles.${role}`, { defaultValue: role }) : "—";
  const statusLabel = (status) => status ? t(`settings.team.statuses.${status}`, { defaultValue: status }) : "—";
  const locale = i18n.resolvedLanguage || i18n.language;

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
      setError(localizeApiError(t, e, "settings.team.loadError"));
    } finally {
      setLoading(false);
    }
  }, [canManage, t]);

  useEffect(() => { load(); }, [load]);

  const sendInvite = async () => {
    if (!inviteForm.email.trim()) { toast.error(t("settings.team.emailRequired")); return; }
    setInviting(true);
    try {
      const res = await teamApi.invite({ email: inviteForm.email.trim(), role: inviteForm.role });
      if (res.emailDelivery === "manual" || res.invitationLink) {
        toast.message(t("settings.team.invitationCreatedManual"), {
          description: res.invitationLink
            ? t("settings.team.shareDevInviteLink")
            : t("settings.team.shareInviteLink"),
        });
        if (res.invitationLink) {
          toast.message(t("settings.team.devInvitationLink"), { description: res.invitationLink });
        }
      } else {
        toast.success(t("settings.team.invitationSent", { email: res.email }));
      }
      setInviteForm({ email: "", role: "member" });
      await load();
    } catch (e) {
      toast.error(localizeApiError(t, e));
    } finally {
      setInviting(false);
    }
  };

  const changeRole = async (member, role) => {
    try {
      await teamApi.changeRole(member.id, role);
      toast.success(t("settings.team.roleUpdated", {
        name: member.firstName || member.email,
        role: roleLabel(role),
      }));
      await load();
    } catch (e) {
      toast.error(localizeApiError(t, e));
    }
  };

  const runConfirm = async () => {
    if (!confirm) return;
    try {
      if (confirm.type === "remove") {
        await teamApi.removeMember(confirm.member.id);
        toast.success(t("settings.team.memberRemoved"));
        if (confirm.member.id === user.id) {
          const me = await refreshUser();
          setUser(me);
        }
      } else if (confirm.type === "cancel-invite") {
        await teamApi.cancelInvitation(confirm.invitation.id);
        toast.success(t("settings.team.invitationCancelled"));
      } else if (confirm.type === "transfer") {
        await teamApi.transferOwnership(confirm.member.id);
        toast.success(t("settings.team.ownershipTransferred"));
        const me = await refreshUser();
        setUser(me);
      }
      setConfirm(null);
      await load();
    } catch (e) {
      toast.error(localizeApiError(t, e));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-zinc-500" data-testid="team-loading">
        <Loader2 className="h-6 w-6 animate-spin" aria-label={t("settings.team.loading")} />
      </div>
    );
  }

  if (error) {
    return (
      <SectionCard title={t("settings.team.title")} description={t("settings.team.description")} testid="settings-team">
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300" data-testid="team-error">
          {error}
          <button type="button" onClick={() => { setLoading(true); load(); }} className="ml-3 text-brand-300 underline">{t("common.retry")}</button>
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
        title={t("settings.team.title")}
        description={`${data?.organization?.name || t("settings.team.organizationFallback")} · ${t("settings.team.memberCount", { count: members.length })}`}
        testid="team-members-card"
      >
        {seats && (
          <p className="text-xs text-zinc-500" data-testid="team-seat-count">
            {t("settings.team.seatsActive", { count: seats.active_members })}
            {seats.pending_invitations ? ` · ${t("settings.team.seatsPending", { count: seats.pending_invitations })}` : ""}
            {seats.seat_limit == null ? ` · ${t("settings.team.seatsUnlimited")}` : ` · ${t("settings.team.seatsLimit", { count: seats.seat_limit })}`}
          </p>
        )}

        {members.length === 0 ? (
          <div className="rounded-xl border border-dashed border-white/10 py-12 text-center text-sm text-zinc-500" data-testid="team-empty">
            {t("settings.team.noMembers")}
          </div>
        ) : (
          <div className="overflow-x-auto" data-testid="team-members-list">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-zinc-500">
                  <th className="pb-2 pr-3 font-medium">{t("settings.team.member")}</th>
                  <th className="pb-2 pr-3 font-medium">{t("settings.team.role")}</th>
                  <th className="pb-2 pr-3 font-medium">{t("settings.team.status")}</th>
                  <th className="pb-2 pr-3 font-medium">{t("settings.team.joined")}</th>
                  <th className="pb-2 font-medium"><span className="sr-only">{t("common.actions")}</span></th>
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id} className="border-b border-white/5" data-testid={`team-member-${m.id}`}>
                    <td className="py-3 pr-3">
                      <div className="flex flex-col">
                        <span className="font-medium text-zinc-100">
                          {[m.firstName, m.lastName].filter(Boolean).join(" ") || m.email}
                          {m.isCurrentUser && <span className="ml-2 rounded bg-brand-600/20 px-1.5 py-0.5 text-[10px] text-brand-300">{t("common.you")}</span>}
                        </span>
                        <span className="text-xs text-zinc-500">{m.email}</span>
                      </div>
                    </td>
                    <td className="py-3 pr-3">
                      <span className="inline-flex items-center gap-1.5 capitalize text-zinc-300">
                        {roleIcon(m.role)} {roleLabel(m.role)}
                      </span>
                    </td>
                    <td className="py-3 pr-3">
                      <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-400">{statusLabel(m.status)}</span>
                    </td>
                    <td className="py-3 pr-3 text-zinc-400">{fmtDate(m.joinedAt, locale)}</td>
                    <td className="py-3">
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        {canManage && !m.isOwner && !m.isCurrentUser && (
                          <select
                            aria-label={t("settings.team.changeRoleFor", { email: m.email })}
                            value={m.role}
                            onChange={(e) => changeRole(m, e.target.value)}
                            data-testid={`team-role-${m.id}`}
                            className="rounded-md border border-white/10 bg-zinc-900 px-2 py-1 text-xs text-zinc-200"
                          >
                            {roleOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                          </select>
                        )}
                        {isOwner && !m.isCurrentUser && !m.isOwner && (
                          <button
                            type="button"
                            aria-label={t("settings.team.transferTo", { email: m.email })}
                            data-testid={`team-transfer-${m.id}`}
                            onClick={() => setConfirm({ type: "transfer", member: m })}
                            className="inline-flex items-center gap-1 rounded-md border border-amber-500/30 px-2 py-1 text-xs text-amber-300 hover:bg-amber-500/10"
                          >
                            <ArrowRightLeft className="h-3 w-3" /> {t("settings.team.transfer")}
                          </button>
                        )}
                        {((canManage && !m.isOwner && !m.isCurrentUser) || (m.isCurrentUser && !m.isOwner)) && (
                          <button
                            type="button"
                            aria-label={m.isCurrentUser ? t("settings.team.leaveOrganization") : t("settings.team.removePerson", { email: m.email })}
                            data-testid={`team-remove-${m.id}`}
                            onClick={() => setConfirm({ type: "remove", member: m })}
                            className="inline-flex items-center gap-1 rounded-md border border-red-500/30 px-2 py-1 text-xs text-red-300 hover:bg-red-500/10"
                          >
                            <Trash2 className="h-3 w-3" /> {m.isCurrentUser ? t("settings.team.leave") : t("settings.team.remove")}
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
        <SectionCard title={t("settings.team.inviteMember")} description={t("settings.team.inviteDescription")} testid="team-invite-card">
          <p className="mb-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/90" data-testid="team-invite-email-note">
            {t("settings.team.inviteEmailNote")}
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_160px_auto]">
            <TextField
              label={t("settings.team.email")}
              value={inviteForm.email}
              onChange={(v) => setInviteForm((f) => ({ ...f, email: v }))}
              placeholder={t("settings.team.emailPlaceholder")}
              testid="team-invite-email"
            />
            <SelectField
              label={t("settings.team.role")}
              value={inviteForm.role}
              onChange={(v) => setInviteForm((f) => ({ ...f, role: v }))}
              options={roleOptions}
              testid="team-invite-role"
            />
            <div className="flex items-end">
              <button
                type="button"
                disabled={inviting}
                onClick={sendInvite}
                data-testid="team-invite-submit"
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-60"
              >
                {inviting ? <Loader2 className="h-4 w-4 animate-spin" /> : <><UserPlus className="h-4 w-4" /> {t("settings.team.invite")}</>}
              </button>
            </div>
          </div>

          {pending.length > 0 && (
            <div className="mt-6 space-y-2" data-testid="team-pending-invites">
              <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{t("settings.team.pendingInvitations")}</p>
              {pending.map((inv) => (
                <div key={inv.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-zinc-900/50 px-3 py-2" data-testid={`team-invite-${inv.id}`}>
                  <div className="flex items-center gap-2 text-sm text-zinc-300">
                    <Mail className="h-4 w-4 text-zinc-500" />
                    <span>{inv.email}</span>
                    <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] uppercase text-zinc-400">{roleLabel(inv.role)}</span>
                    <span className="text-xs text-zinc-600">{t("settings.team.expires", { date: fmtDate(inv.expiresAt, locale) })}</span>
                  </div>
                  <button
                    type="button"
                    aria-label={t("settings.team.cancelInvitationTo", { email: inv.email })}
                    data-testid={`team-cancel-invite-${inv.id}`}
                    onClick={() => setConfirm({ type: "cancel-invite", invitation: inv })}
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                  >
                    <X className="h-3.5 w-3.5" /> {t("common.cancel")}
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
              {confirm?.type === "transfer" && t("settings.team.confirmTransferTitle")}
              {confirm?.type === "remove" && (confirm.member?.isCurrentUser ? t("settings.team.confirmLeaveTitle") : t("settings.team.confirmRemoveTitle"))}
              {confirm?.type === "cancel-invite" && t("settings.team.confirmCancelInviteTitle")}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">
              {confirm?.type === "transfer" && (
                <>{t("settings.team.confirmTransferPrefix")} <strong className="text-zinc-200">{confirm.member?.email}</strong> {t("settings.team.confirmTransferSuffix")}</>
              )}
              {confirm?.type === "remove" && !confirm.member?.isCurrentUser && (
                <>{t("settings.team.confirmRemovePrefix")} <strong className="text-zinc-200">{confirm.member?.email}</strong> {t("settings.team.confirmRemoveSuffix")}</>
              )}
              {confirm?.type === "remove" && confirm.member?.isCurrentUser && (
                <>{t("settings.team.confirmLeaveDescription")}</>
              )}
              {confirm?.type === "cancel-invite" && (
                <>{t("settings.team.confirmCancelInvitePrefix")} <strong className="text-zinc-200">{confirm.invitation?.email}</strong>?</>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 bg-zinc-900 text-zinc-200">{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction
              data-testid="team-confirm-action"
              onClick={(e) => { e.preventDefault(); runConfirm(); }}
              className="bg-brand-600 text-white hover:bg-brand-500"
            >
              {t("settings.team.confirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
