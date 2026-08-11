import { useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import MarketingShell from "@/components/marketing/MarketingShell";
import JsonLd from "@/components/marketing/JsonLd";
import SeoHead from "@/components/marketing/SeoHead";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { track } from "@/lib/analytics";

export default function FaqPage() {
  const { t } = useTranslation();
  const items = useMemo(() => {
    const questions = t("marketing.faq.questions", { returnObjects: true });
    return Array.isArray(questions) ? questions : [];
  }, [t]);

  useEffect(() => {
    track("faq_opened");
  }, []);

  const jsonLd = useMemo(() => ({
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer,
      },
    })),
  }), [items]);

  return (
    <MarketingShell>
      <SeoHead
        title={t("marketing.faq.seo.title")}
        description={t("marketing.faq.seo.description")}
        canonicalPath="/faq"
      />
      <JsonLd data={jsonLd} />
      <div data-testid="marketing-faq">
        <section className="border-b border-[var(--theme-border)]">
          <div className="mx-auto max-w-4xl px-5 py-20 text-center sm:px-8 lg:py-28">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--theme-brand)]">{t("marketing.faq.eyebrow")}</p>
            <h1 className="mt-4 text-4xl font-black tracking-tight text-[var(--theme-text-primary)] sm:text-6xl">{t("marketing.faq.title")}</h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-[var(--theme-text-secondary)]">{t("marketing.faq.intro")}</p>
          </div>
        </section>

        <section className="mx-auto max-w-3xl px-5 py-16 sm:px-8 lg:py-24">
          <Accordion type="single" collapsible className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-5 sm:px-7">
            {items.map((item, index) => (
              <AccordionItem key={item.question} value={`faq-${index}`} className="border-[var(--theme-border)] last:border-b-0">
                <AccordionTrigger className="py-6 text-base font-semibold text-[var(--theme-text-primary)] hover:text-[var(--theme-brand)] hover:no-underline">
                  {item.question}
                </AccordionTrigger>
                <AccordionContent className="pb-6 text-sm leading-7 text-[var(--theme-text-secondary)]">
                  {item.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
          <div className="mt-10 rounded-2xl border border-[var(--theme-brand-border)] bg-[var(--theme-brand-soft)] p-6 text-center">
            <h2 className="text-lg font-semibold text-[var(--theme-text-primary)]">{t("marketing.faq.more.title")}</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--theme-text-secondary)]">{t("marketing.faq.more.body")}</p>
          </div>
        </section>
      </div>
    </MarketingShell>
  );
}
