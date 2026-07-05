import { FileText } from "lucide-react";
import { libraryApi } from "@/lib/api";
import LibraryDocsPage from "@/components/LibraryDocsPage";

const STATUSES = ["Draft", "Generated", "Sent", "Accepted", "Rejected"];

export default function Proposals() {
  return (
    <LibraryDocsPage
      icon={FileText}
      kind="proposal"
      tabId="proposal"
      statuses={STATUSES}
      apiFn={libraryApi.proposals}
      help="Every AI-generated proposal across your projects. Open one to edit, change status, or export to PDF/DOCX in the Project Workspace."
      testid="proposals"
    />
  );
}
