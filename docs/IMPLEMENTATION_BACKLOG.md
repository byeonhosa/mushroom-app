# Mushroom App Implementation Backlog

Status: Draft v0
Last updated: 2026-03-24
Scope: Phase 0 and Phase 1 from `docs/DESIGN.md`

## How To Use This Backlog

Each item should be implemented with:

- updated acceptance criteria if scope changes
- tests added or updated before merge
- local verification notes
- doc updates if behavior or design changes

## Definition Of Done

An item is done only when:

- acceptance criteria are met
- backend tests pass
- frontend typecheck passes
- frontend production build passes
- any new workflow behavior is covered by tests

## Phase 0: Stabilize The Repo

### `P0-001` Remove or repair stale block-centric frontend flows

Goal:

- Make the shipped frontend reflect the actual bag-centric product.

Scope:

- remove or rewrite stale `blocks`, `spawn-batches`, and broken `ingredients` flows
- remove dead navigation paths
- keep only workflows backed by current or planned APIs

Acceptance criteria:

- `npm run build` succeeds
- `npx tsc --noEmit` succeeds
- no frontend page imports nonexistent shared types
- no visible navigation link leads to a guaranteed 404 or broken page

Tests:

- frontend typecheck
- frontend build

### `P0-002` Align frontend and backend API contracts

Goal:

- Eliminate contract drift between the UI and API.

Scope:

- inventory all currently used frontend endpoints
- either implement missing backend routes or remove the frontend calls
- choose one shared source for response types

Acceptance criteria:

- every shipped frontend API call maps to a real backend route
- frontend types match backend response schemas
- broken calls like missing `PATCH` or missing reference-data routes are resolved intentionally

Tests:

- API contract smoke tests
- frontend typecheck

### `P0-003` Add required frontend and migration checks to the workflow

Goal:

- Make build and schema regressions fail fast.

Scope:

- add a frontend typecheck script
- keep production build in CI
- add migration-from-empty-database test coverage

Acceptance criteria:

- repo has a standard command for frontend typecheck
- CI runs frontend typecheck and frontend build
- CI or test suite verifies a fresh database can apply all migrations successfully

Tests:

- CI workflow validation
- migration integration test

### `P0-004` Fix bag-code uniqueness generation

Goal:

- Prevent duplicate IDs and broken repeat bag creation.

Scope:

- repair next-sequence lookup logic
- ensure repeat creation for the same run/species produces new unique codes
- decide whether code generation logic should be reused later for post-inoculation code assignment

Acceptance criteria:

- repeated bag creation under the same code stem never reuses an existing sequence
- duplicate-ID scenario is covered by tests
- no unhandled integrity error is thrown in the normal repeat-create path

Tests:

- unit test for sequence lookup
- integration test for repeated creation in the same run

### `P0-005` Fix lifecycle status inconsistencies

Goal:

- Make current status reliable enough for operator workflows and filters.

Scope:

- align bag event actions with status changes
- remove unreachable or misleading status values
- make harvest, incubation, fruiting, contamination, and disposal transitions consistent

Acceptance criteria:

- incubation updates produce an incubation status
- fruiting updates produce a fruiting status
- harvest actions update status consistently with the chosen lifecycle model
- disposed and contaminated flows are unambiguous

Tests:

- unit tests for status derivation
- integration tests for lifecycle transitions

### `P0-006` Add workflow-level integration coverage

Goal:

- Stop relying only on isolated CRUD tests.

Scope:

- add end-to-end backend workflow tests for the current bag-centric flows
- include at least one contamination path and one two-harvest path

Acceptance criteria:

- test suite covers creation, inoculation, incubation, fruiting, harvest, and disposal
- test suite covers contamination disposal
- tests run against the API/domain flow, not only direct model construction

Tests:

- integration tests only

## Phase 1: Core Bag Lifecycle Redesign

### `P1-001` Introduce internal bag records created at fill time

Goal:

- Track bags before labels exist.

Scope:

- add internal bag identity separate from printable bag code
- allow species to be nullable until inoculation when needed
- attach pre-inoculation bags to sterilization or pasteurization runs

Acceptance criteria:

- spawn and substrate bags can be created before inoculation
- unlabeled bags are still traceable through their run
- bag records persist across inoculation and labeling

Tests:

- migration test
- integration test for pre-inoculation bag creation

### `P1-002` Support post-inoculation printable bag-code assignment

Goal:

- Match the real-world label-printing process.

Scope:

- assign printable bag codes during inoculation workflows
- include bag type, run context, species, and sequence in the code
- print or return label payloads after successful assignment

Acceptance criteria:

- unlabeled bags receive printable codes only after inoculation
- printable codes are stable after assignment
- code format excludes inoculation-source type
- inoculation response can drive label printing

Tests:

- unit test for code format
- integration test for post-inoculation code assignment

### `P1-003` Implement explicit ready events and timestamps

Goal:

- Distinguish incubation from fully colonized readiness.

Scope:

- add `READY` events and ready timestamps for spawn and substrate bags
- derive current status from this event

Acceptance criteria:

- operators can record a bag as ready
- ready timestamps are queryable in reporting and bag detail views
- ready bags are distinguishable from merely incubating bags

Tests:

- unit tests for status derivation
- integration tests for ready event recording

### `P1-004` Implement inoculation batches with one-to-many lineage

Goal:

- Model real spawn usage correctly.

Scope:

- add inoculation-batch model and target join model
- support one source spawn bag to many target bags
- support spawn-to-spawn and spawn-to-substrate inoculation
- support liquid-culture source for spawn-bag inoculation

Acceptance criteria:

- one colonized spawn bag can inoculate multiple child bags in one recorded action
- lineage queries can list parent and child bags
- source spawn bags become consumed when used in an inoculation batch

Tests:

- integration test for spawn-to-spawn batch
- integration test for spawn-to-substrate batch
- lineage query test

### `P1-005` Rework bag detail and run detail views around the new model

Goal:

- Make traceability visible to operators.

Scope:

- show internal/run context before labeling where appropriate
- show parent source, child bags, status events, ready dates, harvest totals, and disposal outcome
- make run pages the primary place to manage unlabeled bags

Acceptance criteria:

- run detail pages show all bags in the run
- bag detail pages show lineage and lifecycle history
- pre-inoculation operations do not depend on printable bag codes

Tests:

- frontend smoke coverage
- manual verification checklist

### `P1-006` Prepare biological-efficiency reporting inputs

Goal:

- Ensure the raw data needed for correct BE reporting exists before the report UI is built.

Scope:

- store actual dry substrate weight when available
- store target dry substrate weight fallback
- make denominator source explicit

Acceptance criteria:

- each substrate bag has either actual or fallback dry-weight data available for reporting
- reporting code can tell whether actual or target dry weight was used

Tests:

- unit tests for BE calculation
- integration test for denominator selection

## Recommended Execution Order

1. `P0-001`
2. `P0-002`
3. `P0-003`
4. `P0-004`
5. `P0-005`
6. `P0-006`
7. `P1-001`
8. `P1-002`
9. `P1-003`
10. `P1-004`
11. `P1-005`
12. `P1-006`

## Recommended First Slice

If we start implementation next, the best first slice is:

- `P0-001` Remove or repair stale frontend flows
- `P0-002` Align API contracts
- `P0-003` Add frontend typecheck

That slice gives the fastest feedback loop and turns the repo back into something we can safely iterate on.
