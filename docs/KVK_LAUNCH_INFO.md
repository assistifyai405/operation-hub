# KVK launch information (Sprint 28)

**Not legal advice.** This document lists business information the owner should collect
after KVK registration so Assistify placeholders can be replaced with real company data.

Do **not** invent KVK numbers, VAT numbers, legal entities, or addresses in the product.

## Fill after KVK registration

| Field | Env / config key | Notes |
|-------|------------------|--------|
| Legal / business name | `LEGAL_COMPANY_NAME` | Exact registered name |
| Trade name | `LEGAL_TRADE_NAME` | If different from legal name (e.g. Assistify) |
| KVK number | `LEGAL_KVK_NUMBER` | Only after official registration |
| VAT number | `LEGAL_VAT_NUMBER` | When received (BTW) |
| Business contact email | `LEGAL_CONTACT_EMAIL` | Public contact |
| Privacy contact | `LEGAL_PRIVACY_EMAIL` | May match contact email initially |
| Business address | `LEGAL_ADDRESS` | Registered / correspondence address |
| Invoice company information | Settings / branding + legal fields | For proposals/contracts/invoices later |
| Domain decision | DNS / `FRONTEND_URL` / `CORS_ORIGINS` | Production hostnames |
| Privacy / Terms content | `/privacy`, `/terms` pages | Replace placeholders with counsel-reviewed text |

## Where placeholders appear today

- Public routes: `/privacy`, `/terms`, `/beta-notice`
- `GET /api/config/public` → `legal` object (`placeholders: true` until company name + contact email are set)
- Product copy must not claim a legal entity that does not exist yet

## Suggested activity description (owner review)

> Assistify develops and operates software that helps small businesses and freelancers
> manage clients, projects, tasks, AI-assisted work, proposals, contracts, invoices,
> and day-to-day business workflow in one AI-powered business operating system.

Do **not** claim a specific SBI code unless verified externally with the owner’s accountant or KVK guidance.

## Related

- [`KVK_READINESS_CHECKLIST.md`](./KVK_READINESS_CHECKLIST.md)
- [`CLOSED_BETA_RUNBOOK.md`](./CLOSED_BETA_RUNBOOK.md)
