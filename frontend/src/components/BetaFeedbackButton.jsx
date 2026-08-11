import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { MessageSquarePlus, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { feedbackApi } from "@/lib/api";

const CATEGORIES = ["Bug", "Idea", "Confusing", "Other"];

/**
 * Subtle beta feedback entry — modal form, no external SaaS.
 */
export default function BetaFeedbackButton() {
  const { t } = useTranslation();
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
      toast.error(t("beta.messageRequired"));
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
      toast.success(t("beta.thanks"));
      setOpen(false);
    } catch (err) {
      toast.error(err.message || t("beta.sendError"));
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
        className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-950 px-2.5 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:border-brand-500/40 hover:text-zinc-100"
      >
        <MessageSquarePlus className="h-3.5 w-3.5" aria-hidden="true" />
        {t("beta.sendFeedback")}
      </button>

      {open && (
        <div className="fixed inset-0 z-[100] flex items-end justify-center bg-black/60 p-4 sm:items-center" data-testid="beta-feedback-modal">
          <button type="button" className="absolute inset-0 cursor-default" aria-label={t("beta.closeFeedback")} onClick={() => setOpen(false)} />
          <form
            onSubmit={submit}
            className="relative z-10 w-full max-w-md rounded-2xl border border-white/10 bg-zinc-950 p-5 shadow-2xl"
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-zinc-50">{t("beta.feedbackTitle")}</h2>
                <p className="mt-1 text-xs text-zinc-500">{t("beta.feedbackHint")}</p>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="rounded-md p-1 text-zinc-500 hover:text-zinc-200" aria-label={t("common.close")}>
                <X className="h-4 w-4" />
              </button>
            </div>

            <label className="mb-1 block text-xs font-medium text-zinc-400">{t("beta.category")}</label>
            <div className="mb-4 flex flex-wrap gap-2" data-testid="beta-feedback-categories">
              {CATEGORIES.map((categoryValue) => (
                <button
                  key={categoryValue}
                  type="button"
                  data-testid={`beta-feedback-cat-${categoryValue.toLowerCase()}`}
                  onClick={() => setCategory(categoryValue)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                    category === categoryValue
                      ? "border-brand-500/50 bg-brand-600/20 text-brand-200"
                      : "border-white/10 text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  {t(`beta.categories.${categoryValue}`)}
                </button>
              ))}
            </div>

            <label htmlFor="beta-feedback-message" className="mb-1 block text-xs font-medium text-zinc-400">{t("beta.message")}</label>
            <textarea
              id="beta-feedback-message"
              data-testid="beta-feedback-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={5}
              maxLength={4000}
              placeholder={t("beta.messagePlaceholder")}
              className="mb-2 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30"
            />
            <p className="mb-4 text-[11px] text-zinc-600" data-testid="beta-feedback-page">
              {t("beta.currentPage", { page: location.pathname })}
            </p>

            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setOpen(false)} className="rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-300">
                {t("common.cancel")}
              </button>
              <button
                type="submit"
                disabled={sending}
                data-testid="beta-feedback-submit"
                className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-60"
              >
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {t("common.submit")}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
