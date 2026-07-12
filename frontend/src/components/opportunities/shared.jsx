import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { opportunitiesApi } from "@/lib/api";

export const COLORS = {
  red: { bar: "bg-red-500", text: "text-red-400", ring: "stroke-red-500", chip: "bg-red-500/15 text-red-300 border-red-500/30" },
  orange: { bar: "bg-orange-500", text: "text-orange-400", ring: "stroke-orange-500", chip: "bg-orange-500/15 text-orange-300 border-orange-500/30" },
  yellow: { bar: "bg-yellow-500", text: "text-yellow-400", ring: "stroke-yellow-500", chip: "bg-yellow-500/15 text-yellow-300 border-yellow-500/30" },
  green: { bar: "bg-emerald-500", text: "text-emerald-400", ring: "stroke-emerald-500", chip: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
};

// Returns handlers for running an opportunity's one-click action + dismissing it.
export function useOpportunityActions(onChanged) {
  const navigate = useNavigate();

  const run = async (item) => {
    const a = item.action || {};
    if (a.kind === "archive" && a.project_id) {
      if (!window.confirm(`Archive "${item.entity?.project_name || "this project"}"? You can still find it later.`)) return;
      try {
        await opportunitiesApi.archiveProject(a.project_id);
        toast.success("Project archived");
        onChanged?.();
      } catch (e) { toast.error(e.message); }
      return;
    }
    if (a.kind === "navigate_client") { navigate("/clients"); return; }
    if (a.link) { navigate(a.link); return; }
    navigate("/dashboard");
  };

  const dismiss = async (item) => {
    try {
      await opportunitiesApi.dismiss(item.key);
      toast.success("Snoozed for 7 days");
      onChanged?.();
    } catch (e) { toast.error(e.message); }
  };

  return { run, dismiss };
}
