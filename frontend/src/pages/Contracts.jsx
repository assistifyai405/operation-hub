import { ScrollText } from "lucide-react";
import { libraryApi } from "@/lib/api";
import LibraryDocsPage from "@/components/LibraryDocsPage";

const STATUSES = ["Draft", "Generated", "Sent", "Signed", "Cancelled"];

export default function Contracts() {
  return (
    <LibraryDocsPage
      icon={ScrollText}
      kind="contract"
      tabId="contract"
      statuses={STATUSES}
      apiFn={libraryApi.contracts}
      help="Every AI-generated service agreement across your projects. Open one to edit, change status, or export to PDF/DOCX in the Project Workspace."
      testid="contracts"
    />
  );
}
