# ERP-Lite

A multi-company ERP dashboard for small logistics and distribution operations,
inspired by Dynamics NAV / Business Central. FastAPI + SQLAlchemy on the back
end, Nuxt 3 on the front, SQLite by default so the whole thing runs with no
external services. It covers the sales, purchasing, warehouse, demand planning
and transport routes of a distribution business, with role-based access and an
append-only audit trail behind every state change.

> **Documentation language:** English only. The user interface is translated
> into Catalan, Spanish and English; this file, the changelog and every code
> comment stay in English.

---

## Status

This is an early-stage project. Be precise about what that means.

**Working today:**

- JWT authentication, four roles, per-company grants
- Multi-tenant scoping across every business table
- Sales orders: `OPEN → PICKING → SHIPPED → INVOICED`
- Purchase orders: `OPEN → RECEIVED → QC_PENDING → QC_APPROVED → CLOSED`, with a
  real quality gate
- Warehouse items, stock adjustments, locations
- Demand worksheet generation
- Transport routes and an activity feed
- Four computed dashboard KPIs
- Three-language interface

**Not built yet — do not assume any of these exist:**

| Not built | Note |
| --- | --- |
| Business Central / Dynamics NAV integration | There is no connector. The `GET /routes` endpoint is **shipment routes for transport planning**, not an ERP connector. The name collision is unfortunate and worth stating explicitly. |
| PDF / Excel export | No export of any kind |
| Single sign-on | Local username and password only, no OAuth, OIDC or SAML |
| Alembic migrations | The schema is bootstrapped with `create_all`. Introduce Alembic once the schema starts changing between deployments. |
| Email, notifications, background jobs | None |
| Front-end test suite | The pytest suite covers the API only |

---

## Quick start

Requires Python 3.13, `uv` and Node.js 20+.

```bash
make setup   # venv + backend deps + npm install, copies backend/.env.example
make seed    # demo companies, users, orders and a synthetic activity history
make dev     # runs both servers; Ctrl-C stops both
```

Then open:

| URL | What |
| --- | --- |
| <http://localhost:3000> | The dashboard |
| <http://localhost:8000/docs> | Interactive OpenAPI documentation |
| <http://localhost:8000/health> | Liveness and database connectivity probe |

### Without the Makefile

```bash
# Backend
cd backend
uv venv --python 3.13 .venv
uv pip install -e ".[dev]"
cp .env.example .env          # then set SECRET_KEY
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend, in a second terminal
cd frontend
npm install
npm run dev
```

### Other Make targets

```
make backend    # API only, with reload
make frontend   # Nuxt dev server only
make test       # pytest suite
make lint       # ruff check
make format     # ruff format
make clean      # remove build artefacts and the local database
```

---

## Demo accounts

All four roles are seeded so every permission path can be exercised. The
password is `demo1234` for every one of them.

| Username | Role | Companies | Can do |
| --- | --- | --- | --- |
| `admin` | admin | `DEMO_SL`, `ACME_SA` | Everything, in every company |
| `buyer` | buyer | `DEMO_SL` | Raise purchase orders, run the demand worksheet |
| `logistics` | logistics | `DEMO_SL` | Receive goods, pick and ship, manage items and routes |
| `quality` | quality | `DEMO_SL` | Approve or reject received goods |

---

## Architecture

```
erp-lite-dashboard/
├── Makefile                  # setup / seed / dev / test entry points
├── docker-compose.yml        # optional PostgreSQL service
├── backend/                  # FastAPI service, package name `app`
│   ├── pyproject.toml        # hatchling, uv, ruff, pytest
│   └── app/
│       ├── main.py           # app, lifespan, /health, ValueError -> 422
│       ├── seed.py           # demo dataset + synthetic activity history
│       ├── core/             # config, engine/session, Argon2 + JWT
│       ├── models/           # SQLAlchemy ORM models
│       ├── schemas/          # Pydantic v2 request/response models
│       ├── services/         # business rules, workflow graphs, KPIs
│       └── api/
│           ├── deps.py       # THE TENANT BOUNDARY: get_current_company
│           └── v1/endpoints/ # HTTP layer, thin by design
│   └── tests/                # pytest, in-memory SQLite
└── frontend/                 # Nuxt 3 application
    ├── nuxt.config.ts        # modules, i18n, runtime config
    ├── app.vue
    ├── layouts/              # default (app shell), auth (login)
    ├── pages/                # index, sales, purchases, warehouse, demand,
    │                         # routes, activity, login
    ├── components/           # KpiCard, StatCard, StatusBadge, switchers…
    ├── stores/auth.ts        # session, role, navigation visibility
    ├── composables/          # useApi (fetch wrapper), useFormat
    ├── middleware/           # auth.global.ts route guard
    └── i18n/locales/         # ca.json, es.json, en.json
```

Three rules govern where code goes:

1. **Endpoints stay thin.** They resolve the actor and the tenant, delegate to a
   service, and map domain errors to HTTP status codes.
2. **Authorisation is server-side.** Every mutating endpoint re-checks the role.
3. **Business state changes are recorded.** A mutation without an
   `ActivityEvent` is a bug.

---

## Design decisions

These are the seven decisions that shaped the code. Everything else follows
from them.

### 1. One database, a `company_code` discriminator

Multi-tenancy is **not** one database file per company, as the original
prototype did it. There is one database and every business table carries a
`company_code` foreign key.

**Why.** A user can hold grants to several companies. With one file per
company, granting a second company means duplicating the user table, the
password hash and the role into a second file, and keeping them consistent.
With a discriminator, a grant is one row in `user_company_access`.

`get_current_company` in `app/api/deps.py` is the tenant boundary. Every
endpoint that touches business data depends on it, so a query that forgot to
filter by company cannot reach the data layer. It returns:

| Situation | Status |
| --- | --- |
| Unknown company code | `404` |
| Known company, caller has no grant | `403` |
| Grant present | `200`, company bound to the request |

The frontend sends the active company as a `?company=` query parameter on
every request, so no request can silently run against "whatever the last
request used". Administrators reach every registered company implicitly.

### 2. Authorisation is enforced on the server

The frontend hides menu entries the caller's role cannot use. That is
presentation, not security. A user who forces an entry into the DOM gains
nothing, because the endpoint checks again.

Enforcement happens at two levels:

- **Endpoint level** — the handler checks `user.role` and returns `403`. For
  example `POST /warehouse/items/{id}/adjust` accepts only `admin` and
  `logistics`. The `require_roles(*roles)` dependency factory exists in
  `app/api/deps.py` for new endpoints, but the current handlers use explicit
  checks because each one needs a role-specific error message.
- **Workflow level** — the transition graph itself carries a role permission
  map, so even the right endpoint refuses the wrong action with `409`.

### 3. The activity event log is the foundation

Every business state change is appended to `activity_events`
(`app/services/activity.py`). The table is append-only by design: there is no
`updated_at` column because a recorded event is never edited.

**Why.** A counter such as `qty_picked` tells you *how much* was picked but
never *when*. "Picks per hour" is unanswerable without a record of the event
itself. The same log is the audit trail: who changed what, and when.

This replaced the prototype's hardcoded dashboard numbers. The writer flushes
but never commits — the caller owns the transaction, so a failure to log
cannot leave a committed change unrecorded.

### 4. KPIs are computed, never hardcoded

`app/services/kpi_service.py` derives every dashboard figure from the activity
log and the operational tables. See the [KPI methodology](#kpi-methodology)
table below for the exact formulas.

The important behaviour: **a KPI that cannot be measured returns `null`**, and
the frontend renders "No data yet". A KPI shown as `0` asserts that work did
not happen. That is a worse lie than showing nothing, because a reader cannot
tell it apart from a real zero.

`picks_per_hour` deserves a specific note. It measures the rate across the span
in which picking actually happened — first event to last event, floored at one
hour — not across the whole calendar window. Six orders spread over a month
divided by 240 working hours reports "0.0 picks per hour", which reads as
"nobody picked anything" when the warehouse was simply idle at the weekend.

### 5. Seeded activity is synthetic, and labelled as such

A fresh database has no events, so every KPI would read "no data" — the honest
state of an empty installation. `app/seed.py` backfills a generated event
history so the dashboard is demonstrable immediately.

**Those rows are generated, not measured.** Every one of them carries:

- `actor_username = "seed"`
- `"synthetic": true` in the payload

Once real activity accumulates, strip the generated rows:

```bash
cd backend
.venv/bin/python -m app.seed --reset-synthetic
```

### 6. A goods receipt does not increase stock

The inventory rules, and the reason each one exists:

| Rule | Reason |
| --- | --- |
| A goods receipt does **not** increase stock | Goods sit in `QC_PENDING`, invisible to inventory, until Quality accepts them |
| Stock increases only on a Quality approval | Approval is the gate, so the receipt cannot silently create inventory |
| Each line posts its quantity **exactly once**, guarded by the `stock_posted` column | The prototype added stock on every click, so approving twice inflated inventory. Regression test: `test_repeat_approval_does_not_inflate_stock` |
| A rejection returns the order to `OPEN` and leaves stock untouched | The vendor needs an order they can rework or resupply |
| Manual corrections go through `POST /warehouse/items/{id}/adjust`, require a reason, and are logged | A stock discrepancy must always trace back to a person and a justification |

An approval only sticks when every line passed. A partial pass posts the
passed lines and returns the order to `OPEN` with the rejected line ids in the
activity payload.

### 7. Money is `Numeric(14, 2)`, never `float`

The prototype stored money as `Float`. `0.1 + 0.2` is not `0.3` in binary
floating point, and an ERP that reports totals a cent off on every invoice is an
ERP nobody trusts.

Quantities use `Numeric(14, 3)` — warehouse stock legitimately needs three
decimal places (pallets, kilograms, litres). Every arithmetic path in the
services goes through `Decimal`, never through a float round-trip.

### Bonus: workflow graphs are validated server-side

A bare status string is never accepted. Two tables decide every transition:

| Table | Where | Purpose |
| --- | --- | --- |
| `ALLOWED_TRANSITIONS` | `sales_service.py` | Which states may follow which |
| `ROLE_PERMISSIONS` | `sales_service.py`, `purchasing_service.py` | Which roles may drive each transition |

An `OPEN → SHIPPED` transition that skips `PICKING` is rejected with `409`, and
so is a role attempting a transition it may not perform. `can_transition()`
returns `(allowed, reason)` instead of raising, so the endpoint can produce a
specific, actionable HTTP error rather than a generic failure.

---

## Roles and permissions

| Role | Purchase orders | Goods receipt | Quality decision | Picking & shipping | Items & routes |
| --- | --- | --- | --- | --- | --- |
| `admin` | yes | yes | yes | yes | yes |
| `buyer` | yes | no | no | no | no |
| `logistics` | no | yes | no | yes | yes |
| `quality` | no | no | yes | no | no |

**Receiving and inspecting are deliberately separate duties.** The role that
books a delivery (`logistics`) cannot also approve it (`quality`). Without that
separation, the same person who signs for goods decides whether they are
acceptable, and the quality gate is theatre.

The matrix governs **changes**. Reads are open to any authenticated user
holding a grant on the company: an operator who cannot edit the item master can
still look up an item code to answer a question, and that is not a privilege
worth withholding.

The frontend mirrors this matrix in `stores/auth.ts` for navigation visibility
only. The backend enforces the real thing, in `app/api/deps.py`
(`require_roles`) and in the service-level `ROLE_PERMISSIONS` maps.

---

## KPI methodology

Computed per company, always scoped to the active tenant.

| KPI | Formula | Default window | Returns `null` when |
| --- | --- | --- | --- |
| **Order accuracy** | `sum(qty_shipped) / sum(quantity) × 100` across orders in `SHIPPED` or `INVOICED` | 30 days | Nothing ordered in the window — there is no denominator |
| **Picks per hour** | count of sales orders entering `PICKING`, divided by the hours between the first and last such event (floored at 1 h) | 30 days | No pick was recorded |
| **Dock to stock** | mean hours between a `received` event and the matching `qc_approved` event on the same order | 90 days | No completed QC cycle, or an approval with no matching receipt |
| **Inventory turnover** | COGS (`sum(quantity × unit_price)` on shipped/invoiced lines) ÷ inventory value (`sum(stock × unit_cost)`) | 90 days | Inventory value is zero |

Under 100% order accuracy means the warehouse shipped short. Turnover is a
snapshot measure: with no historical inventory readings the current value is
used for both the opening and the closing balance, so the figure is indicative
until snapshots exist.

`null` renders as "No data yet" in the UI, never as `0`.

---

## Configuration

### Backend (`backend/.env`)

Copy `backend/.env.example` to `backend/.env`. Every value below is read from
the environment through Pydantic Settings.

| Variable | Default | Notes |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | Free-form label, surfaced by `/health` |
| `DEBUG` | `true` | |
| `SQL_ECHO` | `false` | Logs every statement. Separate from `DEBUG` because statement logging drowns CLI tools like the seeder |
| `DATABASE_URL` | `sqlite:///backend/erp_lite.db` | A bare path is accepted and normalised to a SQLite URL |
| `SECRET_KEY` | dev placeholder | **Override everywhere.** HS256 needs at least 32 bytes. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `720` | 12 hours |
| `ALGORITHM` | `HS256` | |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | JSON list |
| `DEFAULT_COMPANY` | `DEMO_SL` | Preferred landing company when the caller holds a grant to it |

### Frontend (`frontend/.env`)

| Variable | Default |
| --- | --- |
| `NUXT_PUBLIC_API_BASE` | `http://localhost:8000/api/v1` |

### SQLite or PostgreSQL

SQLite is the default so the project runs with zero external services.

```bash
# SQLite: nothing to do
# PostgreSQL: install the driver and point the URL somewhere
cd backend && uv pip install -e ".[postgres]"

DATABASE_URL=postgresql+psycopg://erp:erp@localhost:5432/erp_lite
```

The schema is created by `create_all` inside the application lifespan, so it
boots empty and logs loudly on failure. Introduce Alembic when the schema starts
changing between deployments.

SQLite specifics worth knowing: foreign key enforcement is switched on per
connection (`PRAGMA foreign_keys=ON`), because SQLite ships with it off and
would otherwise accept orphaned order lines.

### Containers

Both services have Dockerfiles, so the whole stack runs without a local Python
or Node install:

```bash
docker compose up --build      # API on :8000, web app on :3000
```

To bring up only PostgreSQL and run the apps on the host:

```bash
docker compose --profile postgres up -d db
```

Both images declare a health check. The API probe hits `/health`, which also
verifies the process can reach its database rather than reporting healthy while
being useless.

---

## API surface

Base prefix `/api/v1`. Interactive documentation at <http://localhost:8000/docs>
is the authoritative reference; this is a map, not a dump.

| Module | Prefix | What it covers |
| --- | --- | --- |
| meta | *(none)* | `GET /health` — liveness plus a real database round-trip. Unauthenticated |
| auth | `/auth` | Login, `/me`, change own password. User administration (`GET`/`POST /users`, `PATCH /users/{id}`) is admin-only and blocks an admin from removing their own access |
| companies | `/companies` | List accessible companies, read and update the current one |
| dashboard | `/dashboard` | `/summary` (KPIs + headline counts), `/alerts`, `/stock-levels`, `/routes`, `/activity` |
| sales | `/sales/orders` | List, read, create, `PATCH /{id}/status`, `DELETE /{id}` |
| purchases | `/purchases/orders` | List, `/awaiting-quality`, read, create, `POST /{id}/receive`, `POST /{id}/quality` |
| warehouse | `/warehouse` | Items CRUD, `/locations`, `POST /items/{id}/adjust` |
| partners | `/customers`, `/vendors` | Business partner CRUD |
| planning | `/demand`, `/routes` | Demand worksheet list, `POST /demand/generate`, `PATCH /demand/{id}`; transport route CRUD |
| activity | `/activity` | Paginated audit feed |

Status codes that matter:

| Code | Meaning |
| --- | --- |
| `401` | Missing, invalid or expired token — or a token issued before the account was deactivated |
| `403` | Authenticated, but no grant for this company or the role may not do this |
| `404` | Unknown record **within the caller's company**. A record in another tenant is a `404`, not a `403`, so an outsider cannot probe for its existence |
| `409` | Workflow violation: an illegal transition, a role attempting one, or receiving against an order already past the gate |
| `422` | Domain validation error. Services raise `ValueError` subclasses and a global handler maps them to `422` instead of `500` |

List endpoints accept `limit` (1–500, default 50) and `offset`, and return
`{ "items": [...], "meta": { "total", "limit", "offset" } }`.

---

## Testing

```bash
make test
# or
cd backend && .venv/bin/python -m pytest -q
```

The suite runs against an in-memory SQLite database, so it is hermetic and can
never touch a developer's working data. Coverage:

| File | What it protects |
| --- | --- |
| `test_auth.py` | Login, indistinguishable failures for unknown user and wrong password, deactivated accounts cannot use a still-valid token, tenant isolation, admin reaching an ungranted company, unknown company is a `404` |
| `test_sales_workflow.py` | The full `OPEN → INVOICED` path, skipping a step is rejected, a buyer cannot start picking, logistics cannot invoice, line counters update, the status change is logged, cross-tenant reads fail |
| `test_purchasing_workflow.py` | Receipt does not increase stock, approval posts stock, **repeat approval does not inflate stock**, logistics cannot approve quality, rejection leaves stock untouched, adjustments are logged and cannot go negative |
| `test_kpi_service.py` | KPIs are `null` on an empty installation, `picks_per_hour` uses the activity span, dock-to-stock measures receipt to approval and ignores orphan approvals, turnover is `null` on empty inventory, alerts fire |
| `test_endpoints_smoke.py` | Every collection endpoint returns 200 without a server error, tenant scoping on the read endpoints, pagination metadata, the OpenAPI schema builds, the seeder runs end to end |

The smoke file exists for a reason worth remembering: a schema module once
referenced a type it never imported. The endpoint existed, routed correctly,
imported cleanly, and still returned `500` on every call, because unit tests on
the service layer never called it. **When you add an endpoint, add it to
`COLLECTION_ENDPOINTS`.**

---

## Not yet built

- Business Central / Dynamics NAV integration of any kind
- PDF and Excel export
- Single sign-on (OAuth, OIDC, SAML)
- Alembic migrations — `create_all` only
- Email, notifications, scheduled jobs
- Inventory movement ledger (stock is a single mutable column plus an activity
  event; a per-movement stock ledger is the correct next step)
- Unit and value variance, multi-warehouse, serial or batch tracking
- Front-end test suite

---

## Contributing

- **Code identifiers in English.** Function, class, variable and file names.
- **Documentation and comments in English.** Both READMEs, the changelog and
  every code comment.
- **Translations are the only non-English content.** `frontend/i18n/locales/`
  holds `ca.json`, `es.json` and `en.json`. When you add a UI string, add the
  key to all three catalogues.
- **Every mutation logs an activity event.** If you write a code path that
  changes business data, add an `activity.record(...)` call or the KPIs will
  silently under-report.
- **Business rules live in services, not endpoints.** Endpoints resolve actor,
  tenant and status codes.
- **Domain errors are `ValueError` subclasses.** The application-level handler
  turns them into `422`.
- Backend formatting and lint: `ruff`, 100 columns, configured in
  `backend/pyproject.toml`.
