# ERP-Lite Backend

FastAPI service backing the ERP-Lite dashboard. Multi-company, role-based,
with a recorded audit trail.

## Quick start

```bash
uv venv --python 3.13 .venv
uv pip install -e ".[dev]"

cp .env.example .env      # then edit SECRET_KEY
python -m app.seed        # demo companies, users and data
uvicorn app.main:app --reload
```

The API is documented at <http://localhost:8000/docs>.

## Seeded accounts

All four roles are seeded so every permission path can be exercised. The
password is `demo1234` for each.

| Username   | Role       | Can do                                        |
| ---------- | ---------- | --------------------------------------------- |
| `admin`    | admin      | Everything, across every company              |
| `buyer`    | buyer      | Raise purchase orders, run the demand worksheet |
| `logistics`| logistics  | Receive goods, pick and ship, manage items and routes |
| `quality`  | quality    | Approve or reject received goods              |

## Architecture

```
app/
├── core/       settings, engine/session, password hashing and JWT
├── models/     SQLAlchemy ORM models
├── schemas/    Pydantic request/response schemas
├── services/   business rules, workflow validation, KPI computation
└── api/v1/     HTTP endpoints
```

Three rules govern where code goes:

1. **Endpoints stay thin.** They resolve the actor and the tenant, delegate to a
   service, and map domain errors to HTTP status codes.
2. **Authorisation is server-side.** Hiding a menu entry in the frontend is
   presentation. Every mutating endpoint checks the caller's role, and every
   query is scoped by company.
3. **State changes are recorded.** Business data never changes without an
   `ActivityEvent`, which is what makes the dashboard KPIs measurable and the
   audit trail complete.

## Multi-tenancy

One database with a `company_code` discriminator on every business table,
rather than one database file per company.

A user may hold grants to several companies. Administrators implicitly reach
all of them. The `get_current_company` dependency in `app/api/deps.py` resolves
the active tenant and rejects the request when the caller has no grant — that
dependency is the tenant boundary, and endpoints that touch business data
depend on it.

## Roles

| Role | Purchase orders | Goods receipt | Quality decision | Picking & shipping | Items & routes |
| --- | --- | --- | --- | --- | --- |
| `admin` | yes | yes | yes | yes | yes |
| `buyer` | yes | no | no | no | no |
| `logistics` | no | yes | no | yes | yes |
| `quality` | no | no | yes | no | no |

Receiving and inspecting are deliberately separate duties: the role that books
the delivery cannot also approve it.

Reads are open to every authenticated user holding a grant on the company; the
matrix governs *changes*. An operator who cannot edit the item master can
still look up an item code to answer a question, which is not a privilege worth
withholding.

## KPI methodology

Dashboard figures are computed from the activity log, never hardcoded.

| KPI | Formula | Returns `null` when |
| --- | --- | --- |
| Order accuracy | shipped units / ordered units on SHIPPED and INVOICED orders | nothing shipped in the window |
| Picks per hour | orders entering PICKING / working hours in the window | no picks recorded |
| Dock to stock | mean hours from receipt to Quality approval | no completed QC cycle |
| Inventory turnover | COGS / inventory value at standard cost | inventory value is zero |

A `null` renders as "no data yet" in the frontend. A KPI shown as zero would
claim that work did not happen, which is a worse lie than showing nothing.

### Seeded activity is synthetic

`app/seed.py` backfills a generated event history so the dashboard is
demonstrable on a fresh install. Those rows carry `actor_username = "seed"` and
`synthetic: true` in the payload. Remove them once real data accumulates:

```bash
python -m app.seed --reset-synthetic
```

## Inventory rules

* A goods receipt does **not** increase stock.
* Stock increases only on a Quality approval.
* Each line posts its received quantity to stock exactly once, guarded by
  `stock_posted`. Re-approving cannot inflate inventory.
* Rejecting returns the order to `OPEN` and leaves stock untouched.
* Manual corrections go through `POST /warehouse/items/{id}/adjust`, which
  requires a reason and records who did it.

## Database

SQLite by default so the project runs with no external services. For
PostgreSQL, set `DATABASE_URL` and install the driver:

```bash
uv pip install -e ".[postgres]"
```

```ini
DATABASE_URL=postgresql+psycopg://erp:erp@localhost:5432/erp_lite
```

`create_all` handles the initial bootstrap. Use Alembic once the schema starts
changing between deployments.

## Tests

```bash
pytest
```

The suite covers tenant isolation, role enforcement, workflow transitions,
the double-approval stock regression and KPI behaviour. It runs against a
temporary SQLite file and never touches working data.