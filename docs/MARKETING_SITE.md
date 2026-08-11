# Assistify marketing site

Public sales website for Assistify (Sprint 30). Lives in the same CRA app as the
authenticated product so branding tokens and i18n stay shared.

## Public routes

| Path | Purpose |
|------|---------|
| `/` | Homepage |
| `/product` | Module overview |
| `/product/copilot` | AI Copilot |
| `/product/crm` | CRM / Clients |
| `/product/projects` | Projects & Tasks |
| `/product/automations` | Automations (conservative copy) |
| `/product/documents` | Proposals, contracts, invoices, documents |
| `/product/agents` | AI Agents |
| `/product/knowledge` | Knowledge Brain |
| `/product/opportunities` | Opportunities |
| `/product/proposals` etc. | Redirect → `/product/documents` |
| `/solutions` | Freelancer / agency / small business |
| `/pricing` | Pre-billing plans (no checkout) |
| `/faq` | FAQ |
| `/security` | Security posture (implemented only) |
| `/privacy` `/terms` `/beta-notice` | Legal placeholders |
| `/login` `/register` | Auth entry |

Authenticated app routes remain under `ProtectedRoute` + `Layout`.

## Copy structure

Marketing strings live in:

- `frontend/src/i18n/locales/marketing-en.json`
- `frontend/src/i18n/locales/marketing-nl.json`

They are deep-merged into the main `en` / `nl` translation resources in
`frontend/src/i18n/index.js`.

Prefer natural Dutch (`je/jouw`) over literal translation.

## CTA system

- **Primary:** Get started / Aan de slag → `/register` (or Open Assistify → `/dashboard` when logged in)
- **Secondary:** See how it works / Bekijk hoe het werkt → on-page `#how-it-works` or product overview
- **Tertiary:** Learn more → product detail pages

Avoid multiple competing primary buttons in one viewport.

## Pricing config

Checkout is **disabled** while Stripe is not integrated (`BILLING_ENABLED` /
runtime `billingEnabled` remain false).

Pricing page shows plan structure (Starter / Pro / Business) with beta messaging
and register CTAs — never payment forms or invented discounts.

## Product visuals

`ProductFrame` / `DashboardMock` render CSS UI previews using Assistify brand
tokens. They are visual-only and must not invent revenue, ratings, or social proof.

## SEO conventions

Use `SeoHead` on every public page:

- unique `title` + `meta description`
- Open Graph title/description
- canonical path

Optional truthful JSON-LD via `JsonLd` (`SoftwareApplication`, `FAQPage`). Do not
include fake ratings, review counts, or prices.

## Localization

Same priority as the authenticated app:

1. Manual preference (`assistify_locale` / saved user language)
2. Browser language
3. English fallback

Public nav/footer language switcher updates immediately and persists.

## Analytics events

Via `frontend/src/pages/marketing/marketingAnalytics.js` → `track()`:

- `marketing_page_view`
- `hero_cta_clicked`
- `product_page_opened`
- `pricing_viewed`
- `faq_opened`
- `register_cta_clicked`

No fingerprinting. No sensitive payloads.

## Adding a product page

1. Add route in `App.js`
2. Add page under `frontend/src/pages/marketing/`
3. Add `marketing.product.details.<slug>` copy in both marketing locale files
4. Link from homepage modules + footer
5. Add SeoHead + `data-testid="marketing-product-<slug>"`
6. Extend Playwright marketing journey if it is a primary CTA path
