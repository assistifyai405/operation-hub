import { useTranslation } from "react-i18next";
import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import { SectionCard } from "@/components/settings/fields";

const OPTIONS = [
  { id: "light", icon: Sun, labelKey: "light" },
  { id: "dark", icon: Moon, labelKey: "dark" },
  { id: "system", icon: Monitor, labelKey: "system" },
];

export function AppearanceSection() {
  const { t } = useTranslation();
  const { theme, setTheme, resolved } = useTheme();

  return (
    <SectionCard
      title={t("settings.appearance.title")}
      description={t("settings.appearance.description")}
      testid="settings-appearance"
    >
      <p className="mb-2 text-xs font-medium text-zinc-400">{t("settings.appearance.label")}</p>
      <div className="flex flex-wrap gap-2" data-testid="theme-options" role="radiogroup" aria-label={t("settings.appearance.label")}>
        {OPTIONS.map(({ id, icon: Icon, labelKey }) => (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={theme === id}
            data-testid={`theme-option-${id}`}
            onClick={() => setTheme(id)}
            className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
              theme === id
                ? "border-brand-500/50 bg-brand-600/20 text-brand-200"
                : "border-white/10 text-zinc-300 hover:border-brand-500/30 hover:text-zinc-100"
            }`}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {t(`settings.appearance.${labelKey}`)}
          </button>
        ))}
      </div>
      <p className="mt-3 text-xs text-zinc-500" data-testid="theme-resolved-hint">
        {t("settings.appearance.hint", { resolved: t(`settings.appearance.${resolved}`) })}
      </p>
    </SectionCard>
  );
}
