# ERP-Lite Frontend

Nuxt 3 single-page application for the ERP-Lite dashboard. Talks to the
FastAPI backend over a plain REST API.

## Quick start

```bash
npm install
cp .env.example .env      # then check NUXT_PUBLIC_API_BASE
npm run dev
```

The app is served on <http://localhost:3000> and expects the API on
<http://localhost:8000>.

```bash
npm run build             # production build into .output/
node .output/server/index.mjs
```

## Internationalisation

Three locales, switched at runtime from the sidebar: **Catalan**, **Spanish**
(default) and **English**.

| File | Contents |
| --- | --- |
| `i18n/locales/es.json` | Spanish (default) |
| `i18n/locales/ca.json` | Catalan |
| `i18n/locales/en.json` | English |

`@nuxtjs/i18n` resolves `langDir` relative to `i18n/`, which is why the
catalogues live in `i18n/locales/` rather than `locales/`.

The active locale is stored in the `erp_locale` cookie and is deliberately
**not** auto-detected from the browser on first visit: warehouse terminals are
shared, and a surprise language switch mid-task is worse than one deliberate
click.

Adding a string means adding the key to all three catalogues. English is the
source of truth for key names; the other two translate them.

## Roles and navigation

`stores/auth.ts` derives the navigation from the caller's role. Buyers do not
fulfil orders, logistics do not raise them, and Quality only inspects what
logistics has received.

**This is presentation, not security.** The sidebar hides what a role cannot
use so the interface stays clean, but the API is the real boundary: every
mutating endpoint re-checks the role server-side. Forcing a hidden route into
the DOM gains nothing.

## Structure

```
├── app.vue                     root component
├── error.vue                   error boundary
├── layouts/
│   ├── default.vue             sidebar + topbar, for signed-in pages
│   └── auth.vue                centred shell for the login page
├── middleware/
│   └── auth.global.ts          route guard
├── pages/
│   ├── login.vue
│   ├── index.vue               dashboard
│   ├── sales.vue               sales orders and fulfilment
│   ├── purchases.vue           purchase orders, receipts, quality gate
│   ├── warehouse.vue           item master and stock adjustments
│   ├── demand.vue              demand worksheet and replenishment simulator
│   ├── routes.vue              shipment routes
│   └── activity.vue            audit trail
├── components/                 KpiCard, StatCard, StatusBadge, switchers…
├── composables/
│   ├── useApi.ts               authenticated fetch wrapper
│   └── useFormat.ts            locale-aware number, date and currency
├── stores/auth.ts              session state
├── types/api.ts                types mirroring the backend schemas
└── assets/css/main.css         design tokens and base styles
```

## Notes

* `types/api.ts` is hand-maintained. If the API surface grows, regenerate it
  from `http://localhost:8000/openapi.json` with `openapi-typescript`.
* The token is held in a cookie so it survives a reload and is readable during
  SSR. That is acceptable while the API is same-site; a cross-site deployment
  should move to an httpOnly cookie issued by the backend.
* The replenishment simulator on the demand page uses the same formula as the
  backend worksheet, so the two cannot disagree about what a reorder quantity
  is.