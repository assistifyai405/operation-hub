# Localization

Assistify supports Dutch (`nl`) and English (`en`). English is the fallback locale.
Locale codes are stored as their two-letter base code.

## Detection and preference priority

The initial interface locale is resolved in this order:

1. Authenticated `user.language`
2. The explicit local preference in `localStorage` under `assistify_locale`
3. The browser's first supported language
4. English (`en`)

`nl`, `nl-NL`, and other `nl-*` browser tags normalize to `nl`. `en`, `en-US`,
and other `en-*` tags normalize to `en`. Unsupported browser locales are skipped
and ultimately fall back to English.

Before authentication finishes, the local or browser preference may render first.
Once the user loads, a valid `user.language` takes priority and is copied to local
storage. Changing the language in Settings updates the interface immediately,
writes `assistify_locale`, and persists `user.language` through
`PATCH /api/auth/profile` for authenticated users.

On registration, the SPA sends the currently resolved locale as `language` in the
payload so a Dutch browser continues in Dutch after account creation. If the client
omits `language`, the API falls back to the `Accept-Language` header, then English.
Invalid values are rejected (`nl` | `en` only).

The backend only persists supported locale preferences. Shared normalization and
AI-language helpers live in `backend/locale_util.py`.

## Frontend translation structure

Localization code is under `frontend/src/i18n/`:

```text
frontend/src/i18n/
├── index.js
├── format.js
└── locales/
    ├── en.json
    └── nl.json
```

- `index.js` registers resources, detects and normalizes locales, and exports the
  supported locale constants.
- `format.js` contains locale-aware date, number, and currency formatting.
- `locales/<locale>.json` contains nested translation keys grouped by product area,
  such as `nav`, `common`, `auth`, `dashboard`, and `settings`.
- React components use `useTranslation()` and `t("namespace.key")`. They obtain
  the active locale from `LocaleProvider` when formatting values or changing the
  preference.

Keep the English and Dutch files structurally aligned. Prefer stable semantic keys
over using English copy as a key, and interpolate values rather than building
translated sentences from fragments.

## Adding a language

1. Add `frontend/src/i18n/locales/<code>.json` with the same key structure as
   `en.json`.
2. Import and register it in `frontend/src/i18n/index.js`, then add its base code
   to `SUPPORTED_LOCALES`.
3. Extend `normalizeLocale`, browser-detection tests, the Settings language picker,
   and locale-aware formatting where the new language needs a different region tag.
4. Add the base code to `ALLOWED_LOCALES` and update normalization/instructions in
   `backend/locale_util.py`. Keep profile validation and persistence tests in sync.
5. Review AI language instructions and generated-document expectations with a
   fluent speaker.
6. Check key parity, layouts with longer copy, dates, numbers, currencies,
   accessibility labels, emails, and empty/error states.
7. Update this document's supported-locale list.

Do not enable a locale with a partial translation file unless product copy has an
explicit, tested fallback policy.

## AI language behavior

Authenticated requests bind the user's normalized locale. `AIService` appends one
system instruction before completion and streaming calls:

- `nl`: `Preferred response language: Dutch (Nederlands).`
- `en`: `Preferred response language: English.`

The instruction applies to assistant replies and generated document content.
An explicit language request in the user's prompt takes precedence. Missing or
unsupported preferences use English. Explicit translation actions also retain
their requested target language.

## Sprint 30 marketing reuse

Marketing pages should reuse the same locale constants, translation resources,
detection rules, storage key, and `format.js` helpers. For a signed-out visitor,
call the shared resolution path without a user preference; after sign-in,
`user.language` remains authoritative. Add marketing copy under a dedicated,
matching namespace in both locale JSON files instead of creating a second detector
or another local-storage key.


## Hardcoded string audit

Run a lightweight heuristic scan for likely customer-facing English left in JSX:

```bash
python scripts/audit_hardcoded_strings.py
python scripts/audit_hardcoded_strings.py --json --limit 500
```

The scanner is intentionally imperfect. Classify hits as technical/internal,
test-only, proper nouns, or follow-up — do not treat every hit as a defect.


## Help system strings (Sprint 31)

Module help copy lives in:

- `frontend/src/i18n/locales/help-en.json`
- `frontend/src/i18n/locales/help-nl.json`

Merged in `frontend/src/i18n/index.js` alongside marketing locales. Help UI must ship NL + EN together — never English-only panels.
