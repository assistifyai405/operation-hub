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
        <section className="border-b border-white/10">
          <div className="mx-auto max-w-4xl px-5 py-20 text-center sm:px-8 lg:py-28">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-brand-300">{t("marketing.faq.eyebrow")}</p>
            <h1 className="mt-4 text-4xl font-black tracking-tight text-white sm:text-6xl">{t("marketing.faq.title")}</h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-zinc-300">{t("marketing.faq.intro")}</p>
          </div>
        </section>

        <section className="mx-auto max-w-3xl px-5 py-16 sm:px-8 lg:py-24">
          <Accordion type="single" collapsible className="rounded-2xl border border-white/10 bg-zinc-950 px-5 sm:px-7">
            {items.map((item, index) => (
              <AccordionItem key={item.question} value={`faq-${index}`} className="border-white/10 last:border-b-0">
                <AccordionTrigger className="py-6 text-base font-semibold text-zinc-100 hover:text-brand-200 hover:no-underline">
                  {item.question}
                </AccordionTrigger>
                <AccordionContent className="pb-6 text-sm leading-7 text-zinc-400">
                  {item.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
          <div className="mt-10 rounded-2xl border border-brand-400/20 bg-brand-500/10 p-6 text-center">
            <h2 className="text-lg font-semibold text-white">{t("marketing.faq.more.title")}</h2>
            <p className="mt-2 text-sm leading-6 text-zinc-300">{t("marketing.faq.more.body")}</p>
          </div>
        </section>
      </div>
    </MarketingShell>
  );
}
