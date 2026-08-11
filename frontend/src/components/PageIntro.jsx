import PageHelp from "@/help/PageHelp";
import HelpTip from "@/components/HelpTip";

/**
 * Concise page heading + explanation. Keep descriptions short — no giant cards.
 * Optional `helpModule` wires the Sprint 31 PageHelp entry (registry-based).
 * Legacy `help` string still supports HelpTip tooltips.
 */
export default function PageIntro({
  title,
  description,
  help,
  helpModule,
  action,
  testid = "page-intro",
  className = "",
}) {
  return (
    <div className={`mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between ${className}`} data-testid={testid}>
      <div className="min-w-0 max-w-2xl">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xl font-semibold tracking-tight text-zinc-50 sm:text-2xl" data-testid={`${testid}-title`}>
            {title}
          </h2>
          {helpModule ? <PageHelp moduleId={helpModule} /> : null}
          {!helpModule && help ? <HelpTip text={help} testid={`${testid}-help`} /> : null}
        </div>
        {description ? (
          <p className="mt-1 text-sm leading-relaxed text-zinc-400" data-testid={`${testid}-description`}>
            {description}
          </p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
