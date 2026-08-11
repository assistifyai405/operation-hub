import { ScrollText } from "lucide-react";
import { useTranslation } from "react-i18next";
import { libraryApi } from "@/lib/api";
import LibraryDocsPage from "@/components/LibraryDocsPage";
import PageIntro from "@/components/PageIntro";

const STATUSES = ["Draft", "Generated", "Sent", "Signed", "Cancelled"];

export default function Contracts() {
  const { t } = useTranslation();
  return (
    <div data-testid="contracts-page-wrap">
      <PageIntro title={t("pages.contracts.title")} description={t("pages.contracts.description")} />
      <LibraryDocsPage
        icon={ScrollText}
        kind="contract"
        tabId="contract"
        statuses={STATUSES}
        apiFn={libraryApi.contracts}
        help={t("pages.contracts.description")}
        testid="contracts"
      />
    </div>
  );
}
