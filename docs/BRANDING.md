# Assistify branding

Assistify's product identity uses a professional green palette on a dark neutral
interface. Green replaces the previous purple brand treatment; purple may still
appear when it carries an intentional semantic meaning, such as one item in a
multi-series chart or a distinct workflow status.

## Green palette

| Token | Hex | Typical use |
|---|---|---|
| `brand-50` | `#F0FDF4` | Very light tinted surfaces |
| `brand-100` | `#DCFCE7` | Light selected surfaces |
| `brand-200` | `#BBF7D0` | Light borders |
| `brand-300` | `#86EFAC` | Soft accents |
| `brand-400` | `#4ADE80` | Bright accent details |
| `brand-500` | `#22C55E` | Primary brand on dark UI |
| `brand-600` | `#16A34A` | Hover, export, and light-surface primary |
| `brand-700` | `#15803D` | Strong contrast |
| `brand-800` | `#166534` | Dark green |
| `brand-900` | `#14532D` | Deep green |

Use `#22C55E` for the main product accent on dark backgrounds. Use `#16A34A`
for backend-generated email and document defaults and where a darker primary is
more appropriate on a light surface. Select a darker token when required to meet
text contrast; never rely on color alone to communicate state.

## Semantic colors

- Brand/primary: the green scale above.
- Success: green is allowed, but pair it with a label or icon so it is not confused
  with a brand-only action.
- Destructive/error: red, using the `destructive` tokens.
- Warning: amber or yellow.
- Information and secondary data: blue or cyan.
- Neutral content and surfaces: the zinc/dark-neutral system.
- Charts and statuses: use colors that keep categories distinguishable. A semantic
  violet is valid here and is not a brand-primary fallback.

## CSS and Tailwind tokens

The source CSS variables are in `frontend/src/index.css`:

```css
--brand-50: #f0fdf4;
/* ... */
--brand-500: #22c55e;
--brand-600: #16a34a;
/* ... */
--brand-soft: rgba(34, 197, 94, 0.08);
--brand-border: rgba(34, 197, 94, 0.20);
--brand-glow: rgba(34, 197, 94, 0.22);
```

The shadcn-style `--primary`, `--accent`, and `--ring` variables map to the green
brand in the dark theme. `frontend/tailwind.config.js` exposes the scale as:

- `brand`, `brand-50` through `brand-900`
- `brand-soft` and `brand-border`
- `shadow-brand`
- semantic aliases such as `bg-primary`, `text-primary`, and `ring-ring`

Prefer these classes and variables over hard-coded hex values:

```jsx
<button className="bg-brand text-white hover:bg-brand-600">Save</button>
<div className="border border-brand-border bg-brand-soft" />
```

Backend HTML and exported PDF/DOCX files cannot consume browser CSS variables.
Their default primary is `#16A34A`, while organization-supplied branding still
overrides that default.

## Correct usage

- Use green for primary calls to action, active navigation, selected controls,
  links that need brand emphasis, focus rings, and restrained highlights.
- Use one dominant green treatment per area and neutral surfaces around it.
- Use palette tokens consistently across hover, border, background, and glow
  states.
- Preserve customer-configured organization colors in branded exports.
- Verify contrast, focus visibility, and non-color state indicators.

## Incorrect usage

- Do not use the old Assistify purple (`#7C3AED` or `#8B5CF6`) as a default brand
  primary.
- Do not replace semantic warning, destructive, informational, chart, or status
  colors with green merely for visual consistency.
- Do not scatter raw green hex values through React components when a CSS or
  Tailwind token exists.
- Do not use bright green for large background areas, body text, or decorative
  glow without restraint.
- Do not override an organization's explicitly configured export branding.


## Light marketing direction (Sprint 31)

Public marketing uses the premium light theme documented in `docs/LIGHT_DESIGN.md`.
Brand green on light surfaces prefers `#16A34A`. Authenticated app remains dark-first until a dedicated light conversion sprint.
