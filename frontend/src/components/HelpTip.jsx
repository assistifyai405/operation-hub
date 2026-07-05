import { HelpCircle } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export default function HelpTip({ text, testid }) {
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button type="button" className="text-zinc-500 transition-colors hover:text-violet-400" data-testid={testid} aria-label="Help">
            <HelpCircle className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs border-white/10 bg-zinc-900 text-xs leading-relaxed text-zinc-200">
          {text}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
