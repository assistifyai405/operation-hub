# Assistify light design direction

Sprint 31 introduces a **premium light-first** visual identity for the public marketing site, plus reusable theme tokens for gradual authenticated-app adoption.

## Marketing (light-first)

| Token role | Value |
|------------|-------|
| Page background | `#F7F8F7` (`--theme-background`) |
| Cards / surfaces | `#FFFFFF` (`--theme-surface`) |
| Muted surface | `#EEF2EF` (`--theme-surface-muted`) |
| Primary text | `#111827` (`--theme-text-primary`) |
| Secondary text | `#6B7280` (`--theme-text-secondary`) |
| Brand green | `#16A34A` on light (`--theme-brand`) |
| Soft green | `rgba(22, 163, 74, 0.08)` |
| Borders | subtle neutral / brand tint |

Feel: modern B2B SaaS — warm off-white, rounded cards, soft shadows, Assistify green. Avoid clinical pure-white sheets, neon green, heavy glassmorphism, crypto aesthetics, and huge empty sections.

`MarketingShell` sets `data-theme="light"` on the document and uses theme CSS variables for chrome, CTAs, and footer.

## Authenticated app

The authenticated product **remains dark by default** in Sprint 31 to avoid a risky full rewrite.

- `Layout` and `AuthShell` re-apply `data-theme="dark"`.
- Light tokens are defined and ready.
- Shared marketing components and theme utilities are centralized.
- Full authenticated light conversion can continue in Sprint 31.5.

## Theme architecture

Source: `frontend/src/styles/theme.css` (imported from `index.css`).

Central variables:

- `background`, `surface`, `surface-muted`
- `border`, `text-primary`, `text-secondary`
- `brand`, `brand-hover`, `brand-soft`
- `focus`, `shadow`

Helpers: `frontend/src/lib/theme.js` (`light` | `dark` | `system` preference storage).

Tailwind exposes `theme.*` colors and `shadow-soft` / `shadow-brand-soft`.

Do **not** scatter hardcoded light hex values through JSX — use CSS variables / theme utilities.

## Semantic colors

Preserved across themes:

- Red → error / destructive
- Amber → warning
- Green → success (and brand where appropriate)

## Typography & atmosphere

Outfit remains the product typeface. Marketing uses a subtle grid + soft green radial wash (`marketing-grid-bg`, `marketing-soft-green`) without neon glow.

`prefers-reduced-motion` disables decorative animations globally.
