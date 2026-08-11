import { useCallback, useEffect, useState } from "react";
import { Loader2, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { feedbackApi } from "@/lib/api";
import { SectionCard } from "@/components/settings/fields";

export function BetaFeedbackSection() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await feedbackApi.list({ limit: 100 });
      setItems(res.feedback || []);
      setTotal(res.total ?? (res.feedback || []).length);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <SectionCard
      title="Beta feedback"
      description="Feedback submitted by users in this workspace."
      testid="settings-beta-feedback"
    >
      <p className="text-xs text-zinc-500" data-testid="beta-feedback-total">{total} submission{total === 1 ? "" : "s"}</p>
      {loading ? (
        <div className="flex justify-center py-10"><Loader2 className="h-5 w-5 animate-spin text-zinc-500" /></div>
      ) : items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-white/10 py-10 text-center text-sm text-zinc-500" data-testid="beta-feedback-empty">
          No feedback yet.
        </p>
      ) : (
        <ul className="space-y-3" data-testid="beta-feedback-list">
          {items.map((f) => (
            <li key={f.id} className="rounded-xl border border-white/10 bg-zinc-950/60 p-4" data-testid={`beta-feedback-item-${f.id}`}>
              <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                <MessageSquare className="h-3.5 w-3.5" />
                <span className="rounded bg-brand-600/20 px-1.5 py-0.5 font-medium text-brand-300">{f.category}</span>
                <span>{f.userName || f.userEmail}</span>
                <span>·</span>
                <span>{f.createdAt ? new Date(f.createdAt).toLocaleString() : "—"}</span>
                {f.page && <span className="text-zinc-600">· {f.page}</span>}
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-200">{f.message}</p>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
