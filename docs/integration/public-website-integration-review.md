# Public Website Integration Review

Status: Phase 7A audit
Repository: `byeonhosa/mushroom-app`
Reviewed from branch: `codex/production-app-integration-review`
Review date: 2026-04-26

## Executive Summary

The production tracking app is a useful internal farm-operations system, especially for bag-level traceability from liquid culture or spawn source through substrate bags, harvest events, disposal, contamination review, and biological-efficiency reporting.

It is not ready for automated integration with the public website yet.

The most important blockers are:

- no authentication or authorization on the FastAPI API;
- no public-safe read-only integration API;
- no customer-facing availability model;
- no inventory ledger for sellable harvest lots, reservations, channel commitments, spoilage, or value-added conversion;
- no sales/channel/customer model;
- no profitability model beyond yield and biological-efficiency reporting;
- deployment documentation indicates password-based server access and direct public API/DB-style defaults that need hardening before any bridge.

Recommended integration posture:

- Manual export/import can start after a small security and data-contract cleanup.
- Read-only website availability sync should wait for an explicit inventory/availability model and API-token or HMAC-authenticated endpoints.
- Website orders should not reserve or decrement production inventory until the production app has reservation, allocation, idempotency, audit-log, and rollback semantics.

Overall integration readiness rating: **partially ready for internal production reference, not ready for automated website sync**.

## 1. High-Level Architecture

| Area | Finding |
|---|---|
| Technology stack | Next.js frontend, FastAPI backend, SQLAlchemy ORM, PostgreSQL for production, SQLite for local/test paths. |
| Languages | TypeScript/React frontend, Python 3.12 backend. |
| Frontend/backend structure | `frontend/` and `backend/` directories in one repo. Frontend consumes generated OpenAPI TypeScript types. |
| Database | PostgreSQL in Docker/prod; tests default to SQLite unless PostgreSQL is explicitly configured. |
| ORM | SQLAlchemy declarative models in `backend/app/models.py`. |
| API style | REST via FastAPI router under `/api`. No GraphQL found. |
| Migrations | Raw SQL migrations in `backend/app/migrations`; applied by `python -m app.migrate`. Not Alembic. |
| Seeds | Migration SQL seeds baseline reference data such as zones, fill profiles, recipes, grain type, species, and initial mix lot. No separate rich seed workflow. |
| Tests | Pytest backend tests, migration smoke tests, API contract generation/checks, frontend typecheck/build, Playwright E2E in CI. |
| CI | `.github/workflows/ci.yml` runs backend tests, PostgreSQL migration smoke, API contract checks, frontend typecheck/build, and Playwright E2E. |
| Docker | Root `docker-compose.yml` runs Postgres, API, and frontend. |
| Environment variables | `.env.example`, `backend/.env.example`, and `frontend/.env.local.example` provide local/dev defaults. |
| Deployment | `docs/OPERATIONS.md` has release, health, backup, and restore notes. `CLAUDE.md` references a droplet and password-based access. |

### Major Services

- `db`: PostgreSQL 16.
- `api`: FastAPI backend exposing `/api/*`.
- `frontend`: Next.js operator UI.

### Local Development Process

Documented paths:

- Full stack: `docker compose up --build`.
- Backend: create Python venv, install `backend/requirements.txt`, run `python -m app.migrate`, run Uvicorn.
- Frontend: `npm ci`, then `npm run dev`.

### Production Deployment Process

Production operations documentation exists but remains lightweight. It covers health checks, backups, restores, and release checks. There is not yet a hardened staging/production separation plan suitable for a public website integration.

## 2. Data Model Review

| Domain area | Status | Evidence / gap |
|---|---:|---|
| Mushroom species | Partially ready | `mushroom_species` has code, name, Latin name, notes, active flag. Seed currently includes `LM` after the bag-centric rebuild. Needs broader species master catalog and public/ops mapping codes. |
| Strains/cultures/genetics | Partially ready | `liquid_cultures` has culture code, species, source, prepared date, notes, active flag. No explicit strain/genetics lineage, vendor lot fields, generation, isolate, or culture health status. |
| Liquid culture | Partially ready | First-class entity exists and can be an inoculation source. Needs richer genetics and lifecycle tracking before it becomes a true source of truth. |
| Grain spawn | Partially ready | Spawn bags, sterilization runs, grain types, spawn recipes, and spawn-to-spawn lineage exist. Partial-consumption is intentionally not modeled in v1. |
| Substrate blocks/bags | Ready for v1 bag tracking | Current implementation is bag-centric with `bags` records. Legacy block-centric migrations/pages remain in history, but active model uses bags. |
| Substrate recipes/formulas | Partially ready | `substrate_recipe_versions`, `mix_lots`, `ingredients`, `ingredient_lots`, and `mix_lot_addins` exist. Recipe formulas are not yet a robust costing/formula system. |
| Sterilization batches | Partially ready | `sterilization_runs` exists with run code, recipe, grain type, cycle times, bag count, temp/psi/hold notes. |
| Pasteurization batches | Partially ready | `pasteurization_runs` exists with run code, mix lot, recipe, times, bag count, notes. |
| Incubation | Partially ready | Status events and timestamps track incubation start and ready state. No environmental telemetry or tent-level capacity model. |
| Fruiting | Partially ready | Fruiting start and status are tracked on substrate bags. No detailed room/tent allocation, environmental readings, or forecast model. |
| Harvests | Partially ready | `harvest_events` records bag, flush 1 or 2, fresh weight, harvested date, notes. It does not create sellable inventory lots or channel allocations. |
| Flushes | Partially ready | Flush numbers are limited to 1 and 2 in schema and app logic. |
| Fresh inventory | Missing | Harvest weight is recorded, but no inventory ledger, on-hand quantity, available quantity, commitments, spoilage, packaging, or lot release workflow exists. |
| Value-added products | Missing | No model for dried mushrooms, salts, powders, capsules, or conversion from fresh lots. |
| Dried products | Missing | No drying batches, shrink ratio, packaged inventory, lot traceability, or shelf-stable inventory model. |
| Supplements/powders/capsules | Missing | No supplement/product manufacturing, lot, label, or compliance model. |
| Spent substrate | Partially ready | Spent/final-harvest disposal is represented as bag disposal, but spent substrate reuse or inventory is not modeled. |
| Sales | Missing | No sales order, order line, transaction, invoice, or payment model. |
| Customers/channels | Missing | No customer, restaurant, farmers market, wholesale, online channel, or subscription model. |
| Farmers market sales | Missing | No market-event, cash/POS sale, or market allocation model. |
| Restaurant/wholesale sales | Missing | No restaurant account, standing order, allocation, or wholesale commitment model. |
| Online sales | Missing | Not modeled; public website/Medusa should own ecommerce orders initially. |
| Costs | Partially ready | Ingredient lots have `unit_cost_per_kg`, and dry-weight/yield reporting exists. There is no full COGS rollup. |
| Labor | Missing | No labor entries, time allocation, or labor costing. |
| Overhead | Missing | No utilities/rent/equipment overhead allocation. |
| Profitability | Missing | Biological efficiency is present; revenue, margin, batch profitability, channel profitability, and waste economics are absent. |
| Users/admin | Risky | No authentication or role model; docs explicitly assume a trusted internal team for v1. |

## 3. Inventory and Availability Capabilities

| Question | Can the app answer today? | Notes |
|---|---:|---|
| What fresh mushrooms are available today? | Partially | It can show fruiting and harvested substrate bags, but not sellable on-hand availability. |
| What quantities are available? | No | Harvest weights are not converted into inventory on hand minus commitments/spoilage. |
| Which harvest lot or batch produced them? | Partially | Harvest events link to substrate bags and upstream runs, but there is no harvest-lot identity suitable for commerce. |
| Which species/products are coming soon? | Partially | Incubating/ready/fruiting bags can imply production pipeline, but no public coming-soon state exists. |
| Which species are seasonal or intermittent? | No | Species has only active/inactive, not seasonal schedule or public state. |
| Which inventory is committed to restaurants? | No | No reservation or channel commitment model. |
| Which inventory is committed to subscriptions? | No | No subscription or allocation model. |
| Which inventory is committed to farmers markets? | No | No market inventory allocation model. |
| Which inventory is committed to online sales? | No | No order/reservation bridge to website. |
| Which inventory should be visible on the public website? | No | No public visibility or availability-publish flag. |
| Which inventory should not be visible publicly? | No | No public/private inventory field. |
| Which products are sold out? | No | No public product availability model. |
| Which products are expected soon? | Partially | Operational stage can be used for forecasts, but there are no expected availability dates. |
| Which products are wholesale-only? | No | No channel/product state model. |
| Which products should become value-added rather than fresh sale? | No | No conversion-planning model. |

Conclusion: the app is a strong upstream production-history source, but it cannot yet serve as the authoritative public availability source.

## 4. Cost and Profitability Capabilities

| Capability | Status | Notes |
|---|---:|---|
| Cost per substrate block/bag | Partially ready | Ingredient lot costs and dry weights exist, but there is no complete cost rollup per bag. |
| Cost per grow batch | Missing | Runs/mix lots exist, but no batch COGS calculation. |
| Input/substrate costs | Partially ready | Ingredient lots include unit cost; formula usage and overhead allocation are incomplete. |
| Packaging costs | Missing | No packaging/material cost model. |
| Labor allocation | Missing | No labor capture. |
| Utilities/rent allocation | Missing | No overhead allocation. |
| Yield by species | Partially ready | Production report can group yield/contamination by species. |
| Yield by strain | Missing | Strain/genetics is not modeled deeply enough. |
| Yield by batch/run | Partially ready | Pasteurization/sterilization run reporting exists. |
| Yield by fruiting tent | Missing | Zones exist but bags are not clearly allocated over time for tent yield reporting. |
| Revenue by product/channel/customer type | Missing | No sales/customer/channel model. |
| Profit margin by species/product/channel | Missing | No revenue and incomplete COGS. |
| Fresh vs dried/value-added profitability | Missing | No value-added conversion/inventory model. |
| Batch-level profitability | Missing | Yield exists; revenue and cost allocation do not. |
| Waste/spoilage | Missing | Contamination and final disposal exist, but sellable waste/spoilage after harvest is not modeled. |

## 5. API and Integration Surface

### Existing REST API

The API is generated into OpenAPI and TypeScript types. Current routes include:

- Health: `GET /api/health`, `/api/health/live`, `/api/health/ready`
- Reference data: `/api/fill-profiles`, `/api/substrate-recipe-versions`, `/api/spawn-recipes`, `/api/mix-lots`, `/api/species`, `/api/liquid-cultures`, `/api/grain-types`, `/api/ingredients`, `/api/ingredient-lots`
- Runs: `/api/pasteurization-runs`, `/api/sterilization-runs`, run detail routes
- Bags and lifecycle: `/api/bags`, `/api/bags/spawn`, `/api/bags/substrate`, `/api/bags/{bag_id}`, status-events, incubation, ready, fruiting, disposal, dry-weight
- Inoculations: `/api/spawn-inoculations/batch`, `/api/inoculations`, `/api/inoculations/batch`, `/api/bags/{bag_id}/inoculation`
- Harvests: `/api/harvest-events`, `/api/bags/{bag_id}/harvest-events`
- Reports/dashboard: `/api/dashboard/overview`, `/api/reports/production`
- Labels: `/api/labels/{bag_id}`, `/api/labels/{bag_id}/qr`

### GraphQL

No GraphQL route or schema was found.

### Auth Suitability

Not suitable for website integration today. The repo documentation states there is no authentication and the API is open.

### Service Layer Reuse

`backend/app/crud.py` contains the domain logic and is reusable conceptually, but it is large and mixed-purpose. A stable integration service layer should be created before exposing website-facing availability endpoints.

### Jobs, Webhooks, Import/Export

No events/webhooks/jobs/import-export sync layer was found. Backup/restore scripts exist for PostgreSQL.

### Recommended Integration Direction

- Start with manual export/import or admin-assisted sync.
- Add read-only availability endpoints first.
- Add push/webhook delivery only after auth, audit logs, idempotency keys, and an inventory ledger exist.
- Treat website-facing endpoints as read-only until order reservation/decrement semantics are designed and tested.

## 6. Security and Operational Review

| Area | Assessment |
|---|---|
| Auth and authorization | P0 risk. No auth, no roles, no permissions. Acceptable for a trusted LAN/internal v1 only, not for website integration. |
| Public/private route separation | Risky. Same API exposes read and write operational endpoints. No public integration boundary. |
| Environment handling | Example env files are present and useful. Production secret handling is not documented strongly enough. |
| Secrets in repo | Redacted scan found no obvious real committed production secrets. It did find default/dev database passwords and test literals, which are placeholders but must not be used in production. |
| CORS | Configurable by env. With no auth, CORS is not a sufficient protection. |
| Database exposure | `docker-compose.yml` publishes Postgres on `5432:5432`. Fine for local, risky if used directly on a public host. |
| API exposure | Compose publishes FastAPI on `8000:8000`. Public deployment should put it behind TLS/reverse proxy/auth or internal network only. |
| Logging sensitive data | No obvious secret logging was found in the inspected files, but no systematic logging/privacy policy exists. |
| Deployment separation | Local and production flows are not clearly separated. |
| Server access | `CLAUDE.md` references password authentication for deployment; SSH keys and least privilege should replace that. |
| Backups | Backup and restore docs/scripts exist and are tested at command-construction level. |

Security recommendation: do not connect this API to the public website until auth, integration-only routes, production environment guidance, and public network exposure controls are added.

## 7. Test and Reliability Review

### Existing Tests

Backend tests cover:

- bag creation and code assignment;
- spawn and substrate inoculation flows;
- lifecycle transitions;
- harvest and disposal guardrails;
- dashboard summaries;
- production reporting and data-quality issues;
- traceability views;
- health/readiness checks;
- PostgreSQL backup/restore command construction;
- migration smoke against PostgreSQL in CI.

Frontend CI covers:

- generated API contract check;
- TypeScript typecheck;
- production build;
- Playwright end-to-end workflow.

### Local Checks Run During This Review

- `python -m pytest -q` in `backend/`: **29 passed, 1 skipped, 1 warning**.
- `npm run typecheck` in `frontend/`: **not run successfully** because `tsc` was not available locally; frontend dependencies were not installed in this checkout.

### Missing Tests for Integration Readiness

- API authentication and authorization.
- Read-only website integration endpoints.
- Public availability contracts.
- Inventory ledger behavior.
- Channel commitments and reservations.
- Idempotent sync/export/import.
- Order-reservation rollback.
- Cost/profitability calculations.
- Production/staging configuration safety.

## 8. Integration Readiness Assessment

| Area | Readiness | Notes |
|---|---:|---|
| Species master catalog | Usable with minor changes | Needs broader species codes and website mapping fields. |
| Production batch tracking | Partially ready | Strong for runs and bags, but service layer and docs need hardening. |
| Harvest tracking | Partially ready | Good for bag harvest weights; not a sellable inventory lot model. |
| Physical inventory | Missing | Required before automated availability sync. |
| Current availability | Missing | Needs explicit public availability model. |
| Lot/batch traceability | Partially ready | Strong upstream lineage, weak commerce lot identity. |
| Cost/profitability model | Needs refactor / missing | BE reporting exists; profitability requires new models. |
| Sales/channel model | Missing | Website/Medusa should own ecommerce records initially. |
| API layer | Risky | Many routes exist, no auth or public integration boundary. |
| Auth/security | Risky | P0 blocker. |
| Deployment/staging separation | Risky | Needs hardened compose/deployment docs. |
| Tests | Partially ready | Good internal workflow coverage, missing integration/security tests. |
| Backups | Partially ready | Scripts/docs exist; production backup automation not proven. |
| Logging/audit trail | Missing | Lifecycle events exist, but no integration audit log. |
| Export/sync support | Missing | No dedicated sync/export endpoints or jobs. |

## 9. Recommended Source-of-Truth Design

### Production App Should Own

- Mushroom species and operational species codes.
- Strains/genetics/cultures.
- Spawn bags and substrate bags.
- Sterilization and pasteurization runs.
- Inoculation batches and lineage.
- Harvest events and harvest lots.
- Physical inventory and spoilage.
- Production forecasts and expected availability.
- Channel commitments and inventory reservations.
- Production costs, COGS, and profitability.

### Public Website / Medusa Should Own

- Customer-facing product catalog and product descriptions.
- Public species pages and educational content.
- Recipes and cooking/storage guidance.
- Cart, checkout, payment records, and customer order records.
- Customer notification signups.
- Public availability display derived from production app but editorially controlled in the website.

### Data That Should Be Duplicated

- Stable species code and public species slug.
- Public product SKU/slug mapping.
- Availability state snapshot shown to customers.
- Harvest-lot reference on order/allocation records when needed for traceability.

### Data That Should Be Referenced By ID Only

- Production bag IDs and internal bag codes.
- Sterilization/pasteurization run IDs.
- Inoculation batch IDs.
- Harvest lot IDs.
- Cost records and profitability records.

### Data That Should Never Be Exposed Publicly

- Supplier/vendor cost details.
- Internal contamination investigation details.
- Private production notes.
- Exact profitability/margin information.
- Internal customer/restaurant commitments unless intentionally surfaced.
- Raw operator/admin write endpoints.

## 10. Proposed Integration Architecture

### Phase A - Manual Export/Import or Admin-Assisted Sync

- API endpoints needed: optional CSV/JSON export for species, product mappings, and manual availability snapshots.
- Data contracts: species code, product SKU/slug, availability state, quantity note, expected date, public note.
- Auth method: operator-only UI or local export; no public network exposure.
- Sync direction: production app to website admin/import.
- Failure modes: stale exports, duplicate imports, mismatched SKUs.
- Audit logging: record export timestamp and operator.
- Idempotency: import keyed by species code/product SKU and effective date.
- Rollback: website can revert to previous manual availability snapshot.
- If production app offline: website keeps last manually approved snapshot.
- If website offline: export can be retried later.
- Prerequisites: species/product mapping and explicit public availability fields.

### Phase B - Read-Only Availability Sync

- API endpoints needed: `GET /api/integration/public-availability`, `GET /api/integration/species`, `GET /api/integration/health`.
- Data contracts: versioned JSON with product/species identifiers, quantities, channel commitments, public state, lot references, updated timestamp.
- Auth method: server-to-server API token or HMAC signature; read-only scope.
- Sync direction: website pulls from production app on a schedule or admin action.
- Failure modes: stale cache, auth failure, schema mismatch, partial data.
- Audit logging: request ID, consumer, response version, row count.
- Idempotency: snapshots keyed by `snapshot_id` or `updated_at`.
- Rollback: website keeps last known-good snapshot.
- If production app offline: website displays last known-good availability with stale warning to admin.
- If website offline: production app unaffected.
- Prerequisites: auth, inventory ledger, public visibility fields, tests.

### Phase C - Production App Pushes Availability Updates

- API endpoints needed: production app outbound webhook client, website inbound availability-update endpoint.
- Data contracts: availability-change event with idempotency key and previous/current state.
- Auth method: HMAC-signed webhook with timestamp and replay protection.
- Sync direction: production app pushes to website.
- Failure modes: webhook retries, duplicate delivery, website downtime.
- Audit logging: event delivery attempts and responses.
- Idempotency: event ID required.
- Rollback: compensating availability event or website admin override.
- If production app offline: no updates sent; website keeps last known-good.
- If website offline: production app queues/retries.
- Prerequisites: durable event outbox or retry queue.

### Phase D - Website Orders Reserve/Decrement Production Inventory

- API endpoints needed: reserve inventory, release reservation, confirm fulfillment, cancel reservation.
- Data contracts: website order ID, line IDs, product SKU, quantity, fulfillment channel, lot allocation, idempotency key.
- Auth method: server-to-server scoped token/HMAC with write scope.
- Sync direction: website writes reservations to production app; production app responds with allocation.
- Failure modes: race conditions, oversell, partial reservation, cart abandonment.
- Audit logging: reservation lifecycle and order references.
- Idempotency: required for every reservation/confirm/release call.
- Rollback: release reservation or compensation event.
- If production app offline: website should block fresh local inventory checkout or use a manual fallback.
- If website offline: reservations remain until timeout/cleanup.
- Prerequisites: inventory ledger, reservation model, allocation rules, timeout cleanup, tests.

### Phase E - Profitability Loop From Website Sales To Production Batches

- API endpoints needed: import website order lines, map order lines to harvest lots, record revenue and fees.
- Data contracts: order line, channel, price, discount, taxes, fees, quantity, lot/batch IDs.
- Auth method: scoped server-to-server integration auth.
- Sync direction: website to production app, with optional reconciliation exports back.
- Failure modes: refunds, partial fulfillment, lot split, price changes.
- Audit logging: import batch, source order, reconciliation status.
- Idempotency: order line ID and adjustment ID.
- Rollback: reversal/adjustment entries, not destructive deletes.
- If production app offline: website queues exports.
- If website offline: production app profitability reports omit latest website sales until sync resumes.
- Prerequisites: sales/channel model, COGS model, refund/adjustment model.

### Phase F - Accounting/FarmRaise Export Support

- API endpoints needed: accounting export generation and status endpoints.
- Data contracts: sales totals, COGS summaries, category mappings, customer/channel summaries.
- Auth method: admin-only export or scoped integration token.
- Sync direction: production app exports to accounting/FarmRaise workflow.
- Failure modes: mapping errors, duplicate exports, corrected orders.
- Audit logging: export batch ID, operator, period, checksum.
- Idempotency: export period plus version/checksum.
- Rollback: mark export superseded and issue corrected export.
- If production app offline: no export; website commerce remains separate.
- If accounting target offline: export file can be stored and retried.
- Prerequisites: stable cost/sales model and owner/accountant review.

## 11. Specific Recommendations

### Top 10 Integration Risks

1. Open unauthenticated API allows operational writes.
2. No inventory ledger means website availability could oversell or mislead.
3. Harvest events are not sellable inventory lots.
4. No reservation/commitment model for restaurants, markets, subscriptions, or online orders.
5. No public visibility/publish controls.
6. No idempotent sync/event model.
7. No sales/channel/customer model for profitability loops.
8. No production/staging separation suitable for safe public integration.
9. Default Compose publishes Postgres and API ports broadly.
10. Cost/profitability data is not complete enough for FarmRaise/accounting exports.

### Top 10 Recommended Changes Before Integration

1. Add API authentication and a read-only integration scope.
2. Add an integration-only router separate from operator write routes.
3. Add a physical inventory ledger derived from harvest lots.
4. Add public availability state and public visibility fields.
5. Add channel commitment/reservation tables.
6. Add stable species/product/SKU mapping to the public website.
7. Add idempotent export/sync events and audit logging.
8. Harden deployment docs and Compose for production/staging.
9. Add tests for auth, availability snapshots, and idempotent sync.
10. Add cost and sales/channel models before profitability integration.

### Suggested New Endpoints

- `GET /api/integration/health`
- `GET /api/integration/species`
- `GET /api/integration/product-mappings`
- `GET /api/integration/public-availability`
- `GET /api/integration/availability-snapshots/{snapshot_id}`
- `POST /api/integration/reservations` (future, not for first bridge)
- `POST /api/integration/reservations/{reservation_id}/release` (future)
- `POST /api/integration/reservations/{reservation_id}/confirm` (future)

### Suggested Database Changes

- `inventory_lots`
- `inventory_ledger_entries`
- `availability_snapshots`
- `public_product_mappings`
- `channel_commitments`
- `inventory_reservations`
- `integration_events`
- `integration_audit_log`
- `sales_channels`
- `sales_order_imports` and `sales_order_lines` for later profitability work

### Suggested Tests

- Auth required for all integration endpoints.
- Read-only token cannot call operator write endpoints.
- Availability snapshot excludes hidden/private inventory.
- Sold/committed/spoiled quantities reduce available quantity.
- Duplicate sync event does not duplicate records.
- Reservation idempotency prevents double allocation.
- Website-offline and production-app-offline fallbacks.
- Migration from empty DB and from seeded test data.

### Should The Website Integrate Now?

No automated integration yet.

Proceed with:

- documentation;
- manual product/species mapping;
- manual availability export/import prototype;
- internal-only API design.

Wait for API auth, inventory ledger, public availability snapshot, idempotent sync, and deployment hardening before read-only automated sync. Wait for reservations, channel commitments, and audit logging before any website order can decrement production inventory.
