import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { MessageSquarePlus, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { feedbackApi } from "@/lib/api";

const CATEGORIES = [
  { value: "Bug", label: "Bug" },
  { value: "Idea", label: "Idea" },
  { value: "Confusing", label: "Confusing" },
  { value: "Other", label: "Other" },
];

/**
 * Subtle beta feedback entry — modal form, no external SaaS.
 */
export default function BetaFeedbackButton() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState("Idea");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!open) {
      setMessage("");
      setCategory("Idea");
    }
  }, [open]);

  const submit = async (e) => {
    e.preventDefault();
    if (!message.trim()) {
      toast.error("Please write a short message.");
      return;
    }
    setSending(true);
    try {
      await feedbackApi.submit({
        category,
        message: message.trim(),
        page: location.pathname,
        context: typeof document !== "undefined" ? document.title : undefined,
      });
      toast.success("Thanks — your feedback was sent.");
      setOpen(false);
    } catch (err) {
      toast.error(err.message || "Could not send feedback. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <button
        type="button"
        data-testid="beta-feedback-open"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-950 px-2.5 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:border-violet-500/40 hover:text-zinc-100"
      >
        <MessageSquarePlus className="h-3.5 w-3.5" aria-hidden="true" />
        Send feedback
      </button>

      {open && (
        <div className="fixed inset-0 z-[80] flex items-end justify-center bg-black/60 p-4 sm:items-center" data-testid="beta-feedback-modal">
          <button type="button" className="absolute inset-0 cursor-default" aria-label="Close feedback" onClick={() => setOpen(false)} />
          <form
            onSubmit={submit}
            className="relative z-10 w-full max-w-md rounded-2xl border border-white/10 bg-zinc-950 p-5 shadow-2xl"
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-zinc-50">Send feedback</h2>
                <p className="mt-1 text-xs text-zinc-500">Bugs, ideas, or anything confusing — we read every note.</p>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="rounded-md p-1 text-zinc-500 hover:text-zinc-200" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>

            <label className="mb-1 block text-xs font-medium text-zinc-400">Category</label>
            <div className="mb-4 flex flex-wrap gap-2" data-testid="beta-feedback-categories">
              {CATEGORIES.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  data-testid={`beta-feedback-cat-${c.value.toLowerCase()}`}
                  onClick={() => setCategory(c.value)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                    category === c.value
                      ? "border-violet-500/50 bg-violet-600/20 text-violet-200"
                      : "border-white/10 text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>

            <label htmlFor="beta-feedback-message" className="mb-1 block text-xs font-medium text-zinc-400">Message</label>
            <textarea
              id="beta-feedback-message"
              data-testid="beta-feedback-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={5}
              maxLength={4000}
              placeholder="What happened, or what would help?"
              className="mb-2 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/30"
            />
            <p className="mb-4 text-[11px] text-zinc-600" data-testid="beta-feedback-page">
              Current page: {location.pathname}
            </p>

            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setOpen(false)} className="rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-300">
                Cancel
              </button>
              <button
                type="submit"
                disabled={sending}
                data-testid="beta-feedback-submit"
                className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-60"
              >
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Submit
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
