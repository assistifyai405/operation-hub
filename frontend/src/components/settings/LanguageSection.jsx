import { useState } from "react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import { useLocale } from "@/context/LocaleContext";
import { SectionCard } from "@/components/settings/fields";

export function LanguageSection() {
  const { t } = useTranslation();
  const { locale, setLocale } = useLocale();
  const [saving, setSaving] = useState(false);

  const choose = async (next) => {
    if (next === locale) return;
    setSaving(true);
    try {
      await setLocale(next, { persistRemote: true });
      toast.success(t("settings.language.saved"));
    } catch (e) {
      toast.error(e.message || t("common.error"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <SectionCard
      title={t("settings.language.title")}
      description={t("settings.language.description")}
      testid="settings-language"
    >
      <p className="mb-2 text-xs font-medium text-zinc-400">{t("settings.language.label")}</p>
      <div className="flex flex-wrap gap-2" data-testid="language-options">
        {[
          { id: "nl", label: t("settings.language.nl") },
          { id: "en", label: t("settings.language.en") },
        ].map((opt) => (
          <button
            key={opt.id}
            type="button"
            disabled={saving}
            data-testid={`language-option-${opt.id}`}
            onClick={() => choose(opt.id)}
            className={`rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
              locale === opt.id
                ? "border-brand-500/50 bg-brand-600/20 text-brand-200"
                : "border-white/10 text-zinc-300 hover:border-brand-500/30 hover:text-zinc-100"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <p className="mt-3 text-xs text-zinc-500">{t("settings.language.hint")}</p>
    </SectionCard>
  );
}
