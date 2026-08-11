import { track } from "@/lib/analytics";

export const marketingEvents = {
  pageView: (path) => track("marketing_page_view", { path }),
  heroCtaClicked: (props = {}) => track("hero_cta_clicked", props),
  registerCtaClicked: (props = {}) => track("register_cta_clicked", props),
  productPageOpened: (props = {}) => track("product_page_opened", props),
  pricingViewed: (props = {}) => track("pricing_viewed", props),
  faqOpened: (props = {}) => track("faq_opened", props),
};

export function trackMarketingEvent(name, props = {}) {
  track(name, props);
}
