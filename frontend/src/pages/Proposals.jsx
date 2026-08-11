import { FileText } from "lucide-react";
import { useTranslation } from "react-i18next";
import { libraryApi } from "@/lib/api";
import LibraryDocsPage from "@/components/LibraryDocsPage";
import PageIntro from "@/components/PageIntro";

const STATUSES = ["Draft", "Generated", "Sent", "Accepted", "Rejected"];

export default function Proposals() {
  const { t } = useTranslation();
  return (
    <div data-testid="proposals-page-wrap">
      <PageIntro title={t("pages.proposals.title")} description={t("pages.proposals.description")} />
      <LibraryDocsPage
        icon={FileText}
        kind="proposal"
        tabId="proposal"
        statuses={STATUSES}
        apiFn={libraryApi.proposals}
        help={t("pages.proposals.description")}
        testid="proposals"
      />
    </div>
  );
}
