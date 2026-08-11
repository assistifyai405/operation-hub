import { CircleHelp } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useHelpOptional } from "@/help/HelpContext";

/**
 * Compact help entry near page titles. Does not clutter the UI.
 */
export default function PageHelp({ moduleId, className = "" }) {
  const { t } = useTranslation();
  const help = useHelpOptional();
  if (!help || !moduleId) return null;

  return (
    <button
      type="button"
      onClick={() => help.openHelp(moduleId)}
      data-testid={`page-help-${moduleId}`}
      className={`inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900/80 px-2.5 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:border-brand-500/40 hover:bg-brand-500/10 hover:text-brand-200 ${className}`}
      aria-label={t("help.entryAria", { module: t(`help.modules.${moduleId}.title`, { defaultValue: moduleId }) })}
    >
      <CircleHelp className="h-3.5 w-3.5" aria-hidden="true" />
      <span>{t("help.entry")}</span>
    </button>
  );
}
