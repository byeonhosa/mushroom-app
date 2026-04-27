# Claude Code Production App Fix List

Status: Phase 7A actionable backlog
Audience: Claude Code working in `byeonhosa/mushroom-app`
Purpose: prepare the production tracking app for a safe bridge to The Maury River Mushroom Farm public website.

## 1. Executive Summary

The production app is **not ready for automated public website integration**.

It is useful as an internal source of farm production truth for species, bags, runs, lineage, harvest events, disposal events, and biological-efficiency reporting. The bridge should wait until the app has a secure API boundary and an explicit inventory/availability model.

Main blockers:

- The API has no authentication or authorization.
- There is no public-safe read-only integration API.
- Harvest events do not create sellable inventory lots.
- There is no availability, visibility, commitment, reservation, channel, or sales model.
- Deployment defaults are suitable for local development but risky if copied to production.

Recommended first Claude Code work batch:

**Batch 1 - API auth, integration boundary, and safe public read model skeleton.**

Do not start website order reservation/decrement flows until inventory lots, reservations, idempotency, and audit logs exist.

## 2. Priority Levels

- **P0 - Must fix before any website integration**
- **P1 - Should fix before active sync or public availability display**
- **P2 - Important but can happen after read-only/manual integration**
- **P3 - Future enhancements**

## 3. Prioritized Issues

### P0-001 - Add API Authentication and Integration Scopes

Priority: P0

Problem: The FastAPI API is currently open, and repo documentation explicitly notes that no authentication exists.

Why it matters for website integration: A website bridge would expose operational data and potentially write-capable endpoints without a security boundary.

Affected files/modules:

- `backend/app/main.py`
- `backend/app/api.py`
- new auth/security module
- docs and tests

Recommended fix:

- Add server-to-server API token or HMAC authentication for integration endpoints.
- Add operator/admin auth plan separately; do not assume CORS is enough.
- Ensure read-only integration credentials cannot call operator write endpoints.
- Keep local development ergonomic with explicit development-only bypass if needed.

Acceptance criteria:

- Integration routes require auth by default.
- Invalid or missing credentials return 401/403.
- Read-only token cannot call write endpoints.
- Existing local tests are updated without requiring real secrets.

Suggested tests:

- missing token rejected;
- invalid token rejected;
- valid read-only token accepted for integration GET routes;
- read-only token rejected for POST/PATCH/DELETE operator routes.

Migration/data implications: none required for token-only first pass; database-backed tokens can come later.

Security/privacy implications: critical. Do not log token values.

Dependencies or sequencing notes: Do this before exposing any route to the public website.

### P0-002 - Create a Separate Integration Router

Priority: P0

Problem: Current routes mix operator reads and operational writes under `/api`.

Why it matters for website integration: The website needs a narrow, stable, public-safe contract, not the full farm-floor API.

Affected files/modules:

- `backend/app/api.py`
- new `backend/app/integration_api.py` or equivalent
- OpenAPI generation
- frontend generated contract if shared

Recommended fix:

- Add a new route namespace such as `/api/integration/*`.
- Start with read-only endpoints:
  - `/health`
  - `/species`
  - `/public-availability` skeleton or placeholder
  - `/product-mappings`
- Keep write/reservation endpoints out of scope until later.

Acceptance criteria:

- Integration endpoints are documented and tested.
- Integration endpoints do not expose private notes, costs, contamination investigation details, or operator write commands.
- Integration endpoints require integration auth.

Suggested tests:

- integration route auth tests;
- response contract shape tests;
- private fields excluded tests.

Migration/data implications: may be none for skeleton; product mappings will need schema later.

Security/privacy implications: high; this is the website-facing boundary.

Dependencies or sequencing notes: Pair with P0-001.

### P0-003 - Harden Deployment Defaults Before Any Public Exposure

Priority: P0

Problem: `docker-compose.yml` publishes Postgres on host port 5432 and API on 8000. `CLAUDE.md` references password-based deployment access.

Why it matters for website integration: Public or staging deployments should not expose the database or unauthenticated operator API.

Affected files/modules:

- `docker-compose.yml`
- `docs/OPERATIONS.md`
- deployment docs
- `.env.example` files

Recommended fix:

- Add production/staging Compose guidance that does not publish Postgres publicly.
- Put API behind a reverse proxy or internal network where appropriate.
- Document SSH-key-only server access.
- Replace default production-looking credentials with explicit local-only wording.

Acceptance criteria:

- Docs clearly separate local dev from staging/production.
- Postgres/Redis-style internal services are not publicly exposed in production examples.
- Password-based SSH is documented as not acceptable for production.

Suggested tests:

- docs/review checklist;
- optional Compose config smoke test.

Migration/data implications: none.

Security/privacy implications: critical infrastructure hardening.

Dependencies or sequencing notes: Do before connecting the app to any public network integration.

### P0-004 - Add Public Product/Species Mapping

Priority: P0

Problem: The app has operational species codes but no stable mapping to public website species slugs, product SKUs, or Medusa variant/product identifiers.

Why it matters for website integration: The bridge needs deterministic IDs to avoid syncing Lion's Mane production records into the wrong public product.

Affected files/modules:

- `backend/app/models.py`
- migrations
- schemas/API/service layer
- tests

Recommended fix:

- Add `public_product_mappings` or similar table with:
  - production species ID/code;
  - website species slug;
  - website product slug/SKU;
  - Medusa product/variant ID when known;
  - public visibility default;
  - notes.

Acceptance criteria:

- Mapping is unique and idempotent.
- Missing mapping prevents automatic publish for that product.
- Integration endpoint returns mapping metadata without private fields.

Suggested tests:

- duplicate mapping rejected;
- hidden/unmapped species excluded from public availability;
- mappings serialize correctly for integration endpoint.

Migration/data implications: new table and seed/default rows.

Security/privacy implications: low, but do not expose private notes.

Dependencies or sequencing notes: Needed before manual or automated sync is reliable.

### P1-001 - Add Harvest Lot and Sellable Inventory Ledger

Priority: P1

Problem: `harvest_events` record fresh weight per bag/flush, but no sellable inventory lot or ledger exists.

Why it matters for website integration: Website availability needs on-hand, committed, available, spoiled, converted, and sold quantities.

Affected files/modules:

- `backend/app/models.py`
- migrations
- schemas
- CRUD/service layer
- reports
- tests

Recommended fix:

- Add `harvest_lots` derived from or linked to harvest events.
- Add `inventory_ledger_entries` for additions, reservations, releases, sales, spoilage, value-added conversion, and adjustments.
- Keep ledger append-only where practical.

Acceptance criteria:

- Recording a harvest can create or link to a harvest lot.
- Available quantity = additions - commitments - sales - spoilage - conversions - adjustments.
- Lot links preserve bag/run/species traceability.

Suggested tests:

- harvest creates inventory addition;
- spoilage decreases available inventory;
- duplicate ledger event is idempotent;
- lot traceability includes bag and upstream run.

Migration/data implications: significant new tables; consider backfill for existing harvest events.

Security/privacy implications: do not expose private production notes publicly.

Dependencies or sequencing notes: Required before read-only availability sync can be trusted.

### P1-002 - Add Public Availability States

Priority: P1

Problem: Production statuses like `FRUITING` or `READY` do not map directly to public states like available, low-stock, sold-out, coming-soon, seasonal, preorder, wholesale-only, or hidden.

Why it matters for website integration: Customers need clear availability language; internal production stage should not automatically publish products.

Affected files/modules:

- models/migrations
- integration service
- public availability endpoint
- docs/tests

Recommended fix:

- Add public availability state fields at product/species mapping or availability snapshot level.
- Include:
  - public state;
  - cartability suggestion;
  - visibility;
  - public quantity note;
  - expected availability date;
  - manual override flag;
  - source reason.

Acceptance criteria:

- Default state for new/unmapped catalog items is not publicly cartable.
- Hidden products do not appear in public integration response.
- Coming-soon/sold-out items are visible only when explicitly enabled.

Suggested tests:

- default hidden/not cartable;
- available state appears in public endpoint;
- sold-out and coming-soon serialize with correct flags;
- manual override wins only when explicit.

Migration/data implications: new fields/tables and backfill defaults.

Security/privacy implications: avoid exposing operational notes.

Dependencies or sequencing notes: Build after or alongside inventory ledger.

### P1-003 - Add Channel Commitments and Reservations

Priority: P1

Problem: There is no way to represent inventory already committed to restaurants, markets, subscriptions, or online orders.

Why it matters for website integration: Public availability can oversell if it ignores commitments.

Affected files/modules:

- models/migrations
- inventory services
- reports
- tests

Recommended fix:

- Add `sales_channels` and `inventory_commitments`.
- Include channel type, quantity, lot/species/product, date/window, source, status.
- Keep website reservations separate from farm operator commitments.

Acceptance criteria:

- Available quantity subtracts active commitments.
- Commitments can be released/cancelled.
- Website availability endpoint reports public-safe quantities/notes.

Suggested tests:

- active commitment reduces availability;
- cancelled commitment restores availability;
- restaurant/private commitment details are not exposed publicly.

Migration/data implications: new tables and possible seed channel rows.

Security/privacy implications: do not expose restaurant/customer names in public endpoint.

Dependencies or sequencing notes: Required before website order reservation/decrement.

### P1-004 - Add Idempotent Sync/Audit Log

Priority: P1

Problem: There is no integration event/audit system.

Why it matters for website integration: Syncs and webhooks can retry; duplicate or partial updates must be safe.

Affected files/modules:

- models/migrations
- integration service
- tests

Recommended fix:

- Add `integration_events` and/or `integration_audit_log`.
- Store event ID, source, target, payload hash, status, timestamps, and error summary.
- Require idempotency keys for future write calls.

Acceptance criteria:

- Duplicate event ID does not duplicate effects.
- Failed events can be inspected.
- Audit log avoids storing secrets.

Suggested tests:

- duplicate event no-op;
- failed event recorded;
- payload hash recorded without secrets.

Migration/data implications: new audit table.

Security/privacy implications: sanitize payloads and logs.

Dependencies or sequencing notes: Needed before push sync or write reservation APIs.

### P1-005 - Add Availability Snapshot Endpoint

Priority: P1

Problem: The website needs a compact, versioned snapshot rather than raw bags/harvests.

Why it matters for website integration: The public website should not understand internal production rules or query many operational endpoints.

Affected files/modules:

- integration router/service
- schemas
- tests
- docs

Recommended fix:

- Add `GET /api/integration/public-availability`.
- Include schema version, generated timestamp, snapshot ID, product/species items, public state, available quantity/note, and source freshness.
- Exclude internal costs, notes, and contamination details.

Acceptance criteria:

- Endpoint requires integration auth.
- Response is stable and versioned.
- Tests lock the contract.

Suggested tests:

- snapshot includes only public-safe fields;
- unavailable hidden product omitted;
- stale source status represented.

Migration/data implications: depends on mapping/availability tables.

Security/privacy implications: high public boundary.

Dependencies or sequencing notes: Build after P0 auth/router and P1 availability model.

### P2-001 - Add Cost/COGS Rollups

Priority: P2

Problem: Ingredient lots can store unit cost, but true COGS and profitability are not modeled.

Why it matters for website integration: FarmRaise/accounting and product/channel profitability need COGS by species/product/channel.

Affected files/modules:

- ingredient/mix/run models
- reporting services
- tests

Recommended fix:

- Add cost allocation per mix lot, run, and bag.
- Add packaging/labor/overhead placeholders.
- Separate provisional calculations from accounting-reviewed final numbers.

Acceptance criteria:

- Cost per bag and cost per harvested kg can be calculated for test data.
- Missing cost inputs are surfaced as data-quality issues.

Suggested tests:

- ingredient cost rolls to mix lot;
- mix lot cost allocates to substrate bags;
- missing cost creates warning.

Migration/data implications: new tables/fields for cost assumptions.

Security/privacy implications: cost/margin data should never be public.

Dependencies or sequencing notes: Can follow read-only availability sync.

### P2-002 - Add Sales/Channel Import Model

Priority: P2

Problem: Sales, channels, customers, and website order lines are absent.

Why it matters for website integration: Profitability loop needs revenue and channel attribution.

Affected files/modules:

- models/migrations
- services
- tests

Recommended fix:

- Add sales channel, imported order, imported order line, adjustments/refunds, and channel fee models.
- Keep Medusa/public website as owner of customer-facing order records.

Acceptance criteria:

- Website order lines can be imported idempotently.
- Imported lines can reference inventory lots.
- Refund/adjustment entries do not mutate original sales records destructively.

Suggested tests:

- duplicate order import no-op;
- refund adjustment reverses revenue correctly;
- private customer details minimized.

Migration/data implications: new sales import schema.

Security/privacy implications: limit PII; do not import unnecessary customer details.

Dependencies or sequencing notes: Needed before profitability loop.

### P2-003 - Add Export/Sync CLI

Priority: P2

Problem: There is no manual export/import or sync command-line path.

Why it matters for website integration: Manual/assisted sync is the safest first bridge.

Affected files/modules:

- `backend/scripts/*`
- integration services
- docs/tests

Recommended fix:

- Add CLI to preview/export public availability JSON/CSV.
- Include schema version and validation.
- Never include private notes/costs.

Acceptance criteria:

- Command prints/writes public-safe export.
- Export can be re-run idempotently.
- Docs include operator steps.

Suggested tests:

- CLI output validates against schema;
- hidden/private fields excluded.

Migration/data implications: depends on availability model.

Security/privacy implications: exports must not leak private data.

Dependencies or sequencing notes: Good first step after P0/P1 models.

### P3-001 - Add Forecasting and Production Planning

Priority: P3

Problem: Coming-soon availability is not forecasted from production pipeline.

Why it matters for website integration: The website can show conservative expected availability after the production app has reliable forecasts.

Affected files/modules:

- production reports
- availability services
- tests

Recommended fix:

- Add forecast windows from incubation/fruiting stages by species and historical yield.
- Keep forecasts unpublished unless manually approved.

Acceptance criteria:

- Forecasts are marked provisional.
- Public endpoint exposes only approved public messages.

Suggested tests:

- forecast generated from known fruiting bags;
- unpublished forecast excluded from public response.

Migration/data implications: optional forecast table.

Security/privacy implications: avoid revealing sensitive production details.

Dependencies or sequencing notes: After inventory/availability is stable.

## 4. Production App Readiness Checklist

| Area | Status |
|---|---:|
| Species model | Partially ready |
| Strain/genetics model | Partially ready |
| Batch model | Partially ready |
| Harvest model | Partially ready |
| Inventory model | Missing |
| Product model | Missing |
| Availability status | Missing |
| Quantity tracking | Partially ready |
| Lot/batch traceability | Partially ready |
| Cost tracking | Partially ready |
| Sales/channel tracking | Missing |
| Profitability reporting | Missing |
| API layer | Risky |
| Authentication/authorization | Missing |
| Environment/secrets handling | Risky |
| Database migrations | Partially ready |
| Tests | Partially ready |
| Deployment | Risky |
| Backups | Partially ready |
| Logging/audit trail | Missing |
| Export/sync support | Missing |

## 5. Recommended Claude Code Work Batches

### Batch 1 - Data Model Cleanup and Integration Readiness

Goal: add the security and contract skeleton required before any bridge.

Tasks:

- Add API auth for integration routes.
- Create `/api/integration/*` router.
- Add public product/species mapping schema.
- Add initial read-only integration schemas.
- Document integration boundary.

Files likely involved:

- `backend/app/main.py`
- `backend/app/api.py`
- new backend integration/auth modules
- `backend/app/models.py`
- migrations
- `backend/app/schemas.py`
- tests
- docs

Acceptance criteria:

- No unauthenticated integration access.
- Public-safe route namespace exists.
- Mapping records can be created/seeded.
- Tests prove private operator writes are not exposed through integration auth.

Tests to run:

- `pytest -q`
- migration smoke
- frontend typecheck/build if API contract changes

What not to change:

- Do not connect to the public website.
- Do not deploy.
- Do not change production data.

### Batch 2 - Inventory and Harvest Availability Endpoints

Goal: convert harvests into sellable inventory and safe public availability snapshots.

Tasks:

- Add harvest lot model.
- Add inventory ledger.
- Add public availability states.
- Add `GET /api/integration/public-availability`.
- Add manual export CLI.

Files likely involved:

- models/migrations
- CRUD/services
- schemas
- tests
- docs

Acceptance criteria:

- Harvest lot traceability preserved.
- Available quantity respects ledger entries.
- Public endpoint excludes hidden/private records.

Tests to run:

- backend tests;
- migration smoke;
- API contract tests.

What not to change:

- Do not reserve/decrement inventory from website orders yet.

### Batch 3 - Cost/Profitability Model Hardening

Goal: support COGS and profitability without blocking read-only website sync.

Tasks:

- Roll ingredient lot costs into mix lots.
- Allocate run/mix costs to bags.
- Add packaging/labor/overhead placeholders.
- Add data-quality warnings for missing costs.

Files likely involved:

- ingredient/mix/run models
- reporting service
- tests
- docs

Acceptance criteria:

- Cost per bag and per harvested kg can be calculated for test data.
- Missing values do not create false precision.

Tests to run:

- reporting tests;
- migration tests.

What not to change:

- Do not expose cost/margin data to public integration endpoints.

### Batch 4 - API Auth and Website Sync Endpoints

Goal: make read-only website pull sync reliable.

Tasks:

- Finalize API token/HMAC auth.
- Add snapshot versioning.
- Add idempotent sync/export event logging.
- Add stale/offline behavior docs.

Files likely involved:

- integration router/service
- auth module
- schemas
- tests
- docs

Acceptance criteria:

- Website can pull public availability with read-only credentials.
- Duplicate pulls are safe.
- Snapshot is cacheable and versioned.

Tests to run:

- integration auth tests;
- snapshot contract tests;
- backend suite.

What not to change:

- Do not implement website write/reservation calls yet.

### Batch 5 - Tests, Migrations, and Deployment Hardening

Goal: make production/staging operations safe enough for integration.

Tasks:

- Harden Compose/deployment docs.
- Ensure database is not publicly exposed in production examples.
- Add migration rollback/recovery notes.
- Add integration CI checks.

Files likely involved:

- `docker-compose.yml` or new staging/prod compose examples
- `.env.example`
- `docs/OPERATIONS.md`
- CI workflow

Acceptance criteria:

- Clear local vs staging vs production environment docs.
- No public DB exposure in deployment examples.
- Integration tests run in CI.

Tests to run:

- backend suite;
- migration smoke;
- frontend build/typecheck.

What not to change:

- Do not deploy unless separately approved.

### Batch 6 - Reporting/Export Layer

Goal: prepare for FarmRaise/accounting and profitability exports.

Tasks:

- Add sales/channel import model.
- Add accounting export schema.
- Add export audit log and checksums.
- Add docs for owner/accountant review.

Files likely involved:

- models/migrations
- reporting/export services
- scripts
- docs/tests

Acceptance criteria:

- Export files are repeatable and versioned.
- Corrected exports supersede earlier exports rather than mutating history.

Tests to run:

- export schema tests;
- idempotency tests;
- backend suite.

What not to change:

- Do not make final tax/accounting conclusions.

## 6. Suggested Claude Code Prompts

### Prompt 1 - P0 Integration Security and Router Skeleton

```text
You are working in the `byeonhosa/mushroom-app` repository.

Goal: prepare the production app for a future read-only bridge to The Maury River Mushroom Farm public website by adding an authenticated integration API skeleton.

Safety boundaries:
- Do not deploy.
- Do not connect to or modify production data.
- Do not commit secrets.
- Do not print secret values.
- Do not touch the public website repo.
- Do not implement order reservation or inventory decrement.

Tasks:
1. Read README.md, DEV.md, docs/OPERATIONS.md, docs/DESIGN.md, docs/REQUIREMENTS.md, and current backend API/model code.
2. Add a separate `/api/integration` router with read-only endpoints:
   - `GET /api/integration/health`
   - `GET /api/integration/species`
   - placeholder/skeleton `GET /api/integration/public-availability`
3. Add server-to-server integration auth using environment-configured test/development tokens or an HMAC approach.
4. Ensure missing/invalid credentials fail safely.
5. Ensure read-only integration credentials cannot call operator write endpoints.
6. Add tests for auth, route contracts, and private-field exclusion.
7. Update docs with integration auth setup and safety notes.
8. Run backend tests and any API contract/frontend checks required by changed OpenAPI output.

Do not deploy or connect this to the public website yet.
```

### Prompt 2 - Public Product Mapping

```text
You are working in the `byeonhosa/mushroom-app` repository.

Goal: add a stable production-app-to-public-website mapping model for species/products before any automated sync.

Safety boundaries:
- Do not deploy.
- Do not modify production data.
- Do not touch the public website repo.
- Do not implement live sync.
- Do not expose private production notes or costs.

Tasks:
1. Add a migration and SQLAlchemy model for public product/species mappings.
2. Support production species code/id, website species slug, website product slug/SKU, optional Medusa product/variant ID, visibility default, and notes.
3. Default unmapped items to not publicly visible/cartable.
4. Add schemas/services/tests.
5. Add or update integration endpoint output to include mappings only when public-safe.
6. Update docs with mapping workflow and acceptance criteria.
7. Run backend tests, migration smoke, API contract checks if OpenAPI changes, and frontend typecheck/build if needed.

Do not connect to the public website yet.
```

### Prompt 3 - Harvest Lot and Inventory Ledger

```text
You are working in the `byeonhosa/mushroom-app` repository.

Goal: add a sellable inventory foundation that can later drive public website availability.

Safety boundaries:
- Do not deploy.
- Do not modify production data.
- Do not connect to the public website.
- Do not implement website order reservation yet.
- Do not make accounting/tax conclusions.

Tasks:
1. Review current harvest event, bag, species, and report models.
2. Add harvest lot and inventory ledger models/migrations.
3. Preserve traceability from inventory lot to harvest event, bag, species, and upstream runs.
4. Support ledger entry types for harvest addition, manual adjustment, spoilage, value-added conversion placeholder, commitment placeholder, and sale placeholder.
5. Calculate available quantity from the ledger.
6. Add tests for harvest-to-lot behavior, ledger quantity math, spoilage, idempotency, and traceability.
7. Update docs with the inventory model and future website availability path.
8. Run backend tests and migration smoke.

Keep the website bridge read-only/manual after this batch.
```

### Prompt 4 - Public Availability Snapshot

```text
You are working in the `byeonhosa/mushroom-app` repository.

Goal: implement a public-safe read-only availability snapshot endpoint for future website pull sync.

Safety boundaries:
- Do not deploy.
- Do not touch the public website repo.
- Do not add write/reservation endpoints.
- Do not expose private notes, costs, contamination details, or customer data.

Tasks:
1. Build `GET /api/integration/public-availability` from the inventory ledger and public product mappings.
2. Include schema version, snapshot ID, generated timestamp, source freshness, product/species identifiers, public availability state, public quantity note, and expected availability date if configured.
3. Exclude hidden/unmapped/private records.
4. Require integration auth.
5. Add tests for auth, hidden/private exclusion, available/sold-out/coming-soon states, stale source behavior, and contract shape.
6. Add docs for website pull sync, failure modes, idempotency, and rollback.
7. Run backend tests, migration smoke, API contract checks, and frontend checks as needed.

Do not connect the endpoint to the public website until the owner approves.
```

## 7. Integration Blockers Summary

| Blocker | Priority | Blocks which integration phase? | Recommended owner | Notes |
|---|---:|---|---|---|
| No API authentication | P0 | Manual export/import if networked, read-only sync, push sync, reservations, profitability loop, accounting export | Production app | Local-only manual export can proceed without public API exposure. |
| No integration-only router | P0 | Read-only availability sync and later phases | Production app | Prevents exposing broad operator API to website. |
| Public DB/API exposure risk in deployment defaults | P0 | Any networked integration | Production app | Add staging/prod hardening docs/config. |
| No public product/species mapping | P0 | Manual export/import, read-only sync | Production app and website | Need stable SKU/slug/species ID mapping. |
| No inventory ledger | P1 | Read-only availability sync, reservations, profitability loop | Production app | Harvest events are not enough. |
| No public availability states | P1 | Public availability display | Production app and website | Prevents safe customer-facing status. |
| No channel commitments/reservations | P1 | Website orders reserve/decrement production inventory | Production app | Needed to avoid overselling. |
| No idempotent sync/audit log | P1 | Push sync, reservation writes, profitability loop | Production app | Needed for retries and reconciliation. |
| No sales/channel model | P2 | Profitability loop from website sales to production batches | Production app | Website/Medusa should remain order owner at first. |
| Incomplete cost/COGS model | P2 | Profitability loop, Accounting/FarmRaise export | Production app | BE is present; profitability is not. |
| No export/sync CLI | P2 | Manual export/import | Production app | Useful first bridge before API automation. |
| No production email/accounting integration | P3 | Accounting/FarmRaise export | Production app | Future phase. |

## 8. Notes on Secrets

A redacted scan found no obvious real committed production secrets. The repo contains local/default database credentials and test literals in example/config/test files. Treat these as local-only placeholders and never use them in production.

If real deployment credentials were ever committed outside the inspected files, rotate them before integration work continues.
