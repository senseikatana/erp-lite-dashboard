# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.1] - 2026-10-25

Highlights: fix: theme: update theme-related styles and components to FlyonUI (#1), plus 1 more change.

- 🔹 added 7 packages, and audited 8 packages in 929ms `020e16e`
  - `.husky/pre-commit`
  - `Makefile`
  - `README.md`
  - `backend/.env.example`
  - `backend/app/api/v1/endpoints/admin.py`
  - `backend/app/api/v1/endpoints/companies.py`
  - `backend/app/api/v1/router.py`
  - `backend/app/core/config.py`
  - `backend/tests/test_admin_purge.py`
  - `backend/tests/test_companies.py`
  - `frontend/components/ThemeToggle.vue`
  - `frontend/components/UserMenu.vue`
  - `frontend/composables/useApi.ts`
  - `frontend/i18n/locales/ca.json`
  - `frontend/i18n/locales/en.json`
  - `frontend/i18n/locales/es.json`
  - `frontend/layouts/default.vue`
  - `package-lock.json`
  - `package.json`
- 🐛 fix: theme: update theme-related styles and components to FlyonUI (#1) `22f2257`
  - `frontend/app.vue`
  - `frontend/assets/css/main.css`
  - `frontend/components/AppNotice.vue`
  - `frontend/components/CompanySwitcher.vue`
  - `frontend/components/EmptyState.vue`
  - `frontend/components/KpiCard.vue`
  - `frontend/components/LanguageSwitcher.vue`
  - `frontend/components/StatCard.vue`
  - `frontend/components/StatusBadge.vue`
  - `frontend/components/ThemeSwitcher.vue`
  - `frontend/composables/useTheme.ts`
  - `frontend/error.vue`
  - `frontend/i18n/locales/ca.json`
  - `frontend/i18n/locales/en.json`
  - `frontend/i18n/locales/es.json`
  - `frontend/layouts/auth.vue`
  - `frontend/layouts/default.vue`
  - `frontend/nuxt.config.ts`
  - `frontend/package-lock.json`
  - `frontend/package.json`
  - `frontend/pages/activity.vue`
  - `frontend/pages/demand.vue`
  - `frontend/pages/index.vue`
  - `frontend/pages/login.vue`
  - `frontend/pages/purchases.vue`
  - `frontend/pages/routes.vue`
  - `frontend/pages/sales.vue`
  - `frontend/pages/warehouse.vue`
- 🐛 fix: update .gitignore and CHANGELOG.md files `cc62e93`
- 📝 docs(modules): add CompanyConfig, Customer and DemandLine `6974c1b`

## [0.2.0]

Complete rewrite of the application: the Streamlit prototype is gone, replaced
by a FastAPI API and a Nuxt 3 front end.

### Added

- **Append-only activity event log.** Every business state change is recorded
  in `activity_events` with actor, entity, action and a JSON payload. There is
  no `updated_at` column on purpose — a recorded event is never edited. This is
  what makes the dashboard measurable and the audit trail complete.
- **Computed KPIs.** Order accuracy, picks per hour, dock-to-stock and
  inventory turnover, all derived from the activity log. A KPI that cannot be
  measured returns `null` and the UI renders "No data yet"; it is never shown
  as `0`, because a zero asserts that work did not happen.
- **JWT authentication.** HS256 bearer tokens with Argon2 password hashing,
  self-describing payloads (active company and role embedded in the token),
  `GET /auth/me`, and a change-password endpoint that requires the current
  password even when the caller already holds a valid token.
- **Four roles**: `admin`, `buyer`, `logistics`, `quality`. Coarse by design —
  they map onto the departments that actually operate a warehouse.
- **Tenant scoping.** One database with a `company_code` discriminator, and a
  `get_current_company` dependency that is the single tenant boundary.
- **Company grants.** A user may hold access to several companies through
  `user_company_access`. Administrators reach every registered company
  implicitly.
- **Three-language interface** — Catalan, Spanish and English — via
  `@nuxtjs/i18n`. Spanish is the default. The user picks the language
  deliberately; there is no auto-detect on first visit.
- **Test suite.** A pytest suite covering authentication, tenant isolation,
  role enforcement, workflow transitions, the double-approval stock regression,
  KPI behaviour and endpoint smoke coverage. It runs against an in-memory
  SQLite database and can never touch working data.
- **`GET /health` probe** that performs a real database round-trip. A server
  that cannot reach its database cannot serve requests, and a deployment probe
  that ignores that reports healthy while the application is useless.
- **Demand worksheet regeneration.** `POST /demand/generate` rebuilds the
  pending worksheet from stock levels and committed sales orders. Lines already
  marked `ORDERED` or `IGNORED` survive regeneration, so manual decisions are
  not lost on every run.
- **Stock adjustment endpoint.** `POST /warehouse/items/{id}/adjust` requires a
  reason, refuses adjustments that would drive stock negative, and records
  previous value, new value, delta and reason in the activity log.
- **Operational alerts** on the dashboard: low stock, Quality backlog, and
  purchase orders past their expected delivery date.
- **Makefile** with `setup`, `seed`, `dev`, `test`, `lint`, `format` and
  `clean`.
- **Docker Compose PostgreSQL service** for exercising the non-SQLite path.

### Changed

- **Multi-tenancy model.** The prototype gave each company its own database
  file. There is now one database and a `company_code` discriminator on every
  business table, because a user can hold grants to several companies and
  per-company files would mean duplicating the user table into each one.
- **Money is `Numeric(14, 2)`**, quantities are `Numeric(14, 3)`. All
  arithmetic goes through `Decimal`.
- **Default company resolution is deterministic.** The landing company
  prefers `DEFAULT_COMPANY` when the caller holds a grant to it, instead of
  relying on unordered relationship iteration.
- **Status values are stored as strings**, not integers, so the database stays
  readable and an ordering mistake cannot silently corrupt a workflow.
- **Domain errors map to `422`.** Services raise `ValueError` subclasses and an
  application-level handler converts them, instead of letting a business-rule
  violation surface as a `500`.
- **Workflow transitions are validated server-side** against
  `ALLOWED_TRANSITIONS` and `ROLE_PERMISSIONS`, not accepted as a bare status
  string.

### Removed

- **The entire Streamlit application**: `app.py`, `database.py`, `config.py`,
  `i18n.py`, `seed_data.py` and the whole `modules/` tree, plus the `streamlit`,
  `pandas` and `plotly` dependencies.
- **`requeriments.txt`** — the misspelled requirements file, which nothing read.
- **The previous changelog content.** The `v0.1.0` entry it carried was
  machine-generated before the code worked, and it documented a broken nested
  directory layout
  (`modules/modules/modules/modules/modules/modules/app.py`) as though it were
  the official project structure. It is replaced below by an accurate
  description of what the prototype actually was. That file listing is not
  carried forward, because repeating it would be documenting a defect.
- **Hardcoded dashboard figures.** The prototype showed fixed numbers
  regardless of what happened in the system.

### Fixed

- **Double Quality approval inflated inventory.** The prototype added stock on
  every click of the approve button. Each purchase order line now posts exactly
  once, guarded by a `stock_posted` column. Regression test:
  `test_repeat_approval_does_not_inflate_stock`.
- **Naive/aware datetime crash in dock-to-stock.** SQLite has no native
  datetime type and drops the offset on read, so a value written as
  timezone-aware came back naive and the subtraction raised. Timestamps are now
  normalised to UTC before arithmetic.
- **Default company resolution was non-deterministic.** Landing company came
  from unordered relationship iteration and could differ between requests.
- **Money was stored as float.** `0.1 + 0.2` is not `0.3` in binary floating
  point, and an ERP that reports totals a cent off on every invoice is an ERP
  nobody trusts.
- **A goods receipt increased stock.** Receiving now books the receipt and
  leaves inventory untouched; only a Quality approval posts the quantities.

### Security

- **Argon2 password hashing.** Argon2 rather than bcrypt because bcrypt
  truncates silently at 72 bytes.
- **JWT signed with HS256.** `SECRET_KEY` is read from the environment with a
  development-only placeholder; the docs say plainly that it must be overridden.
- **Server-side role enforcement.** Hiding a menu entry is presentation. Every
  mutating endpoint re-checks the role, and the workflow graphs themselves
  carry a role permission map, so the right endpoint still refuses the wrong
  action.
- **Tenant isolation tests.** A non-admin without a grant gets `403`; a record
  belonging to another tenant is a `404`, so an outsider cannot probe for its
  existence. Endpoint-level smoke tests assert tenant scoping on the read paths.
- **Deactivation takes effect immediately on existing tokens.** The auth
  dependency re-reads the user and rejects a deactivated account even if its
  token has not expired.
- **Login does not leak whether a username exists.** An unknown user and a wrong
  password produce the same `401` with the same message.
- **Administrators cannot lock themselves out.** Removing or demoting your own
  administrator access is rejected.

---

## [0.1.1] - 2026-10-14

Highlights: fix: update .gitignore and CHANGELOG.md files.

- [x] 🐛 fix: update .gitignore and CHANGELOG.md files
  - `.gitignore`
  - `Makefile`
  - `README.md`
  - `backend/.env.example`
  - `backend/Dockerfile`
  - `backend/README.md`
  - `backend/app/__init__.py`
  - `backend/app/api/__init__.py`
  - `backend/app/api/deps.py`
  - `backend/app/api/v1/__init__.py`
  - `backend/app/api/v1/endpoints/__init__.py`
  - `backend/app/api/v1/endpoints/auth.py`
  - `backend/app/api/v1/endpoints/companies.py`
  - `backend/app/api/v1/endpoints/dashboard.py`
  - `backend/app/api/v1/endpoints/partners.py`
  - `backend/app/api/v1/endpoints/planning.py`
  - `backend/app/api/v1/endpoints/purchases.py`
  - `backend/app/api/v1/endpoints/sales.py`
  - `backend/app/api/v1/endpoints/warehouse.py`
  - `backend/app/api/v1/router.py`
  - `backend/app/core/__init__.py`
  - `backend/app/core/config.py`
  - `backend/app/core/database.py`
  - `backend/app/core/security.py`
  - `backend/app/main.py`
  - `backend/app/models/__init__.py`
  - `backend/app/models/activity.py`
  - `backend/app/models/base.py`
  - `backend/app/models/company.py`
  - `backend/app/models/demand.py`
  - `backend/app/models/item.py`
  - `backend/app/models/partner.py`
  - `backend/app/models/purchasing.py`
  - `backend/app/models/routing.py`
  - `backend/app/models/sales.py`
  - `backend/app/models/user.py`
  - `backend/app/schemas/__init__.py`
  - `backend/app/schemas/auth.py`
  - `backend/app/schemas/common.py`
  - `backend/app/schemas/company.py`
  - `backend/app/schemas/dashboard.py`
  - `backend/app/schemas/item.py`
  - `backend/app/schemas/ops.py`
  - `backend/app/schemas/partner.py`
  - `backend/app/schemas/purchasing.py`
  - `backend/app/schemas/sales.py`
  - `backend/app/seed.py`
  - `backend/app/services/__init__.py`
  - `backend/app/services/activity.py`
  - `backend/app/services/demand_service.py`
  - `backend/app/services/kpi_service.py`
  - `backend/app/services/purchasing_service.py`
  - `backend/app/services/sales_service.py`
  - `backend/pyproject.toml`
  - `backend/tests/__init__.py`
  - `backend/tests/conftest.py`
  - `backend/tests/test_auth.py`
  - `backend/tests/test_endpoints_smoke.py`
  - `backend/tests/test_kpi_service.py`
  - `backend/tests/test_purchasing_workflow.py`
  - `backend/tests/test_sales_workflow.py`
  - `config.py`
  - `database.py`
  - `docker-compose.yml`
  - `frontend/.env.example`
  - `frontend/Dockerfile`
  - `frontend/README.md`
  - `frontend/app.vue`
  - `frontend/assets/css/main.css`
  - `frontend/components/CompanySwitcher.vue`
  - `frontend/components/EmptyState.vue`
  - `frontend/components/KpiCard.vue`
  - `frontend/components/LanguageSwitcher.vue`
  - `frontend/components/StatCard.vue`
  - `frontend/components/StatusBadge.vue`
  - `frontend/composables/useApi.ts`
  - `frontend/composables/useFormat.ts`
  - `frontend/error.vue`
  - `frontend/i18n/locales/ca.json`
  - `frontend/i18n/locales/en.json`
  - `frontend/i18n/locales/es.json`
  - `frontend/layouts/auth.vue`
  - `frontend/layouts/default.vue`
  - `frontend/middleware/auth.global.ts`
  - `frontend/nuxt.config.ts`
  - `frontend/package-lock.json`
  - `frontend/package.json`
  - `frontend/pages/activity.vue`
  - `frontend/pages/demand.vue`
  - `frontend/pages/index.vue`
  - `frontend/pages/login.vue`
  - `frontend/pages/purchases.vue`
  - `frontend/pages/routes.vue`
  - `frontend/pages/sales.vue`
  - `frontend/pages/warehouse.vue`
  - `frontend/stores/auth.ts`
  - `frontend/tsconfig.json`
  - `frontend/types/api.ts`
  - `i18n.py`
  - `modules/dashboard.py`
  - `modules/modules/modules/compras.py`
  - `modules/modules/modules/modules/modules/demanda.py`
  - `modules/modules/modules/modules/modules/modules/app.py`
  - `modules/modules/modules/modules/modules/modules/routes.py`
  - `modules/modules/modules/modules/warehouse.py`
  - `modules/modules/ventas.py`
  - `requeriments.txt`
  - `seed_data.py`
- [x] 📝 docs(modules): add CompanyConfig, Customer and DemandLine

## [0.1.0]

An early Streamlit prototype. Discarded and superseded by 0.2.0; it is
summarised here for history only and should not be used as a reference.

A single-file-ish Python application built with Streamlit, pandas and plotly
over SQLite, organised into `app.py`, `database.py`, `config.py`, `i18n.py`,
`seed_data.py` and a `modules/` package covering dashboard, sales, purchasing,
warehouse, demand and routes. It demonstrated the module boundaries and the
Catalan/Spanish/English interface that 0.2.0 kept, but it had no API, no
authentication, no role enforcement, no tenant isolation, no audit trail and
hardcoded dashboard numbers. Its requirements file was misspelled
`requeriments.txt`.

**Its changelog entry was machine-generated and inaccurate.** It recorded a
"release" of a file tree containing
`modules/modules/modules/modules/modules/modules/app.py` — a repeated
`modules/` nesting that was a bug in how the tool walked the directory, not a
real structure. The entry has been removed rather than corrected, because a
changelog is a record of what happened, not a place to retroactively publish a
file listing that never described working code.
