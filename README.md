# ProcureSight: AI-Based Procurement Spend Analytics

ProcureSight is a Phase 1 procurement decision-intelligence system built over 47,128 purchase-order records. PostgreSQL and deterministic Python services remain the source of truth; the AI layer only explains verified opportunities and never calculates prices, performance, or savings.

For a complete new-laptop walkthrough, including database-password setup and troubleshooting, see [`INSTRUCTIONS_TO_RUN.md`](./INSTRUCTIONS_TO_RUN.md).

## 1. Project overview

The system provides:

- validated, rerunnable CSV ingestion into a normalized PostgreSQL schema;
- spend, supplier, category, business-unit, contract, quality, and delivery analytics;
- explainable price benchmarks and four deterministic opportunity types;
- a guarded AI procurement advisor with validated structured output and a safe fallback;
- a responsive React dashboard using only live FastAPI data.

An opportunity is a review candidate, not a guaranteed saving. Findings from different opportunity types can overlap and must not be blindly added together.

## 2. Architecture

```text
purchase_orders.csv
        │ Pydantic validation + idempotent upsert
        ▼
PostgreSQL 16 ── SQLAlchemy/Alembic
        │
        ├── deterministic analytics services
        ├── benchmark + opportunity engine
        └── verified recommendation context
                        │
                        ▼
             OpenAI Responses API
             (narrative only; optional)
                        │
                        ▼
FastAPI /api + OpenAPI ────────── React/Vite dashboard
```

The API uses dependency-managed sessions, commits successful write requests, rolls back failures, returns Pydantic response models, and never serializes ORM objects directly.

## 3. Technology stack

- Backend: Python 3.11+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, HTTPX
- Database: PostgreSQL 16 with fixed-precision `NUMERIC` money fields
- Frontend: React 19, TypeScript, Vite 7, Tailwind CSS 4, Recharts
- Testing and quality: Pytest, Vitest, Testing Library, Ruff, TypeScript
- Local infrastructure: Docker Compose

## 4. Database schema

| Table | Purpose | Key relationships and constraints |
| --- | --- | --- |
| `suppliers` | Supplier dimension | Source `supplier_id` PK; unique supplier name; country index |
| `categories` | Procurement category dimension | Integer PK; unique category name |
| `items` | Item dimension | Integer PK; FK to category; unique item name within category |
| `business_units` | Organizational dimension | Integer PK; unique business-unit name |
| `purchase_orders` | Transaction fact table | Original `po_id` PK; FKs to supplier, item, and business unit; date and composite query indexes |
| `item_benchmarks` | Current item price distribution | One row per item; FK to item; p25/median/p75/min/max and coverage values |
| `cost_opportunities` | Deterministic findings | FKs to item/supplier; unique type-item-supplier scope; priority/status indexes |
| `ai_recommendations` | Stored advisory narratives | FK to opportunity; unique opportunity-model-prompt version |

The schema enforces positive quantity, nonnegative money, valid delivery-date ordering, valid opportunity enums, score ranges, and referential integrity. The clean PostgreSQL verification found 26 indexes, 8 foreign keys, and 7 unique constraints.

## 5. Setup instructions

Prerequisites: Python 3.11+, Node.js 20+, npm, Docker, and Docker Compose.

```bash
cp .env.example .env
# Replace local database password placeholders. OPENAI_API_KEY is optional.

docker compose up -d database

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './backend[dev]'

cd frontend
npm install
cd ..
```

The root `.env`, Python environment, frontend dependencies, production output, caches, and rejection reports are ignored. Never put an OpenAI key in a `VITE_` variable.

## 6. Environment variables

Copy [`.env.example`](./.env.example). Important settings are:

- `DATABASE_URL`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`
- `LOG_LEVEL`, `APP_CURRENCY`
- `CORS_ORIGINS`: comma-separated allowed frontend origins
- `OPENAI_API_KEY`: optional, server-side only
- `OPENAI_MODEL`, `OPENAI_TIMEOUT_SECONDS`
- price, materiality, consolidation, supplier-score, and priority thresholds listed in the example file

The four supplier-performance weights and three priority weights must each sum to 1. The frontend accepts only `VITE_API_BASE_URL`; its example is in [`frontend/.env.example`](./frontend/.env.example).

## 7. Database migration

From `backend`:

```bash
../.venv/bin/alembic upgrade head
../.venv/bin/alembic current
../.venv/bin/alembic check
```

The migration chain is:

1. `20260826_0001` — normalized Phase 1 schema;
2. `20260826_0002` — null-safe opportunity uniqueness;
3. `20260827_0003` — opportunity explainability and recommendation detail fields.

All migrations were verified from an empty PostgreSQL database and the schema matches the ORM metadata.

## 8. CSV ingestion

From `backend`:

```bash
../.venv/bin/python -m app.scripts.import_data --csv ../purchase_orders.csv
../.venv/bin/python -m app.scripts.verify_data
../.venv/bin/python -m app.scripts.calculate_opportunities
```

The importer checks headers, dates, booleans, positive quantities, nonnegative money, delivery-date ordering, duplicate PO IDs, consistent supplier identities, and `line_total == quantity * unit_price` within 0.01. Invalid rows are written with row numbers, source values, and errors to `data/import_rejections.json`; strict mode performs no database writes when any row is invalid.

Dimensions are normalized before facts. Existing source PO IDs are updated and new ones inserted, making the import safely rerunnable. `--allow-partial` is available only for an explicitly reviewed partial import.

Verified source result:

| Measure | Value |
| --- | ---: |
| Source / valid / rejected rows | 47,128 / 47,128 / 0 |
| Total spend | $411,183,335.24 |
| Suppliers / categories / items / business units | 106 / 10 / 50 / 5 |
| Duplicate PO IDs | 0 |
| Orphan relationships | 0 |

The second import produced 0 inserts and 47,128 safe updates with unchanged counts and spend.

## 9. Running the backend

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## 10. Running the frontend

```bash
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. The application contains Executive Dashboard, Spend Analysis, Cost Optimization, and AI Advisor workspaces. It includes loading, error, empty, pagination, filtering, opportunity detail, and responsive navigation states.

## 11. Running tests and checks

```bash
cd backend
../.venv/bin/pytest -q
../.venv/bin/ruff check .

cd ../frontend
npm test
npm run typecheck
npm run build
```

Automated tests never make a real model call; they inject a mock provider. The production build route-splits each workspace to reduce initial JavaScript loading.

## 12. API overview

Analytics:

- `GET /api/dashboard/summary`
- `GET /api/analytics/spend/monthly`
- `GET /api/analytics/spend/categories`
- `GET /api/analytics/spend/suppliers`
- `GET /api/analytics/spend/business-units`
- `GET /api/analytics/supplier-concentration`
- `GET /api/analytics/contract-compliance`
- `GET /api/analytics/quality`
- `GET /api/analytics/delivery`

Reference and optimization:

- `GET /api/suppliers`, `/api/suppliers/{supplier_id}`
- `GET /api/categories`, `/api/items`, `/api/business-units`
- `GET /api/benchmarks`, `/api/benchmarks/{item_id}`
- `GET /api/opportunities`, `/api/opportunities/{opportunity_id}`, `/api/opportunities/summary`
- `POST /api/recommendations/generate`
- `GET /api/recommendations`, `/api/recommendations/{recommendation_id}`

Analytics share common inclusive filters: `date_from`, `date_to`, `supplier_id`, `category_id`, `business_unit_id`, and `country`. Large resources use validated `page` and `page_size` parameters. Opportunity filters include type, priority, supplier, category, item, status, creation dates, and sort direction. Validation errors use a consistent `{ "error": { "code", "message", "details" } }` shape.

## 13. Analytics methodology

SQL aggregation calculates spend, counts, averages, shares, ranks, and supplier performance without loading all transaction rows into Python. Money remains fixed precision. Monthly growth is `(current spend - prior spend) / prior spend * 100`; it is null for the first month or a zero prior month. Delivery delay averages positive calendar-day lateness only. Quality and delivery rates use the relevant order counts as denominators.

## 14. Price benchmarking methodology

For every item and supplier:

```text
weighted supplier price = SUM(line_total) / SUM(quantity)
```

The engine then calculates the continuous distribution over supplier-level weighted prices and stores min, p25, median, p75, max, supplier count, quantity, and spend. The p25 supplier price—not the cheapest transaction—is the benchmark. The clean run produced 50 item benchmarks.

## 15. Cost opportunity methodology

- Price optimization: `variance = (actual weighted price - p25 benchmark) / benchmark * 100`; estimated savings are `max(0, actual - benchmark) * quantity` after configurable variance, supplier-coverage, and minimum-savings thresholds.
- Contract leakage: material off-contract supplier-item spend is labeled spend requiring review, never recoverable savings.
- Supplier consolidation: material multi-supplier items with configurable price dispersion are candidates for volume-negotiation review, never automatic supplier elimination.
- Supplier performance: configurable price/quality/delivery/contract score weights default to 40%/25%/20%/15%.

Confidence combines supplier coverage (35%), transaction coverage (25%), logarithmic quantity coverage (20%), and benchmark stability (20%). Priority is `100 × (impact × 50% + confidence × 30% + severity × 20%)`, with Critical/High/Medium/Low bands at 80/60/40.

Verified all-time run: 254 opportunities—107 price optimization, 144 contract leakage, 1 consolidation, and 2 supplier performance. Price-only estimated opportunity is $12,512,042.67. Review spend remains separate and overlapping opportunity types are not presented as additive.

## 16. AI recommendation methodology

The backend constructs a typed context exclusively from stored opportunity, benchmark, supplier, quality, delivery, and contract values. The system prompt prohibits invented suppliers, prices, savings, competitors, contract terms, market claims, and guaranteed savings.

The OpenAI Responses API receives structured context and a strict JSON Schema. Pydantic validates title, summary, reasoning, action, impact, risks, and next steps. A second numerical-preservation check requires exact impact equality and rejects numbers in prose that were absent from the context. The server stores model name, prompt version, timestamp, and context snapshot. Requests use `store: false`, the key never leaves the backend, and provider errors, timeouts, malformed output, or rate limits produce a clearly labeled deterministic fallback.

## 17. Known limitations

- Phase 1 uses one imported currency and does not perform FX conversion.
- Benchmarks are internal supplier-price distributions, not external market prices.
- Recommendations require human procurement and commercial review.
- The current API has no authentication/authorization layer and is intended for a controlled local or internal environment.
- Opportunity refresh is an explicit command, not a scheduled job.
- The live OpenAI smoke request in this environment received HTTP 429; fallback storage and display were verified successfully.
- A dependency-level Starlette TestClient deprecation warning remains; it does not affect runtime behavior or test results.
- Anomaly detection and forecasting are intentionally out of Phase 1 scope.

## 18. Phase 2 roadmap

- organizational authentication and role-based access;
- scheduled ingestion and opportunity refresh jobs;
- audit workflow for accepting, rejecting, assigning, and realizing opportunities;
- multi-currency normalization and externally governed benchmarks;
- production deployment, observability, backups, and rate limiting;
- anomaly detection and forecasting only after data-governance and evaluation criteria are agreed.
