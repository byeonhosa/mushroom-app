# Mushroom App V1 Design

Status: Draft v0
Last updated: 2026-03-24
Depends on: `docs/REQUIREMENTS.md`

## 1. Design Intent

This document translates the v1 requirements into a buildable system design for a bag-centric mushroom farm workflow.

The design is optimized for:

- bag-level traceability
- contamination root-cause analysis
- biological-efficiency reporting
- scan-friendly farm operations
- systematic implementation and testing

## 2. Confirmed Decisions

- The product is bag-centric, not block-centric.
- The system must store both immutable event history and a derived current status.
- One colonized spawn bag may inoculate many child bags, but partial-consumption tracking is not needed in v1.
- Liquid culture is a first-class entity in v1, but should stay lightweight.
- Biological efficiency should be calculated as total fresh harvest weight divided by dry substrate weight.
- Actual dry substrate weight should be used when available; otherwise the system may fall back to a target dry weight from the recipe or fill profile.
- Ready timestamps should be recorded for both spawn bags and substrate bags.
- Printable bag IDs should be generated after inoculation, not at fill time.
- V1 can assume a trusted internal team and does not require role-based permissions.
- Pre-inoculation handling can stay run-centric in v1 and does not require a separate unlabeled-bag screen.
- Printable bag codes should encode bag type, run context, species, and sequence, but not inoculation-source type.

## 3. Design Principles

### 3.1 Bag-First Model

The bag is the primary production object. Runs, recipes, inoculations, harvests, and disposals all exist to explain what happened to a bag.

### 3.2 Events Are Source Of Truth

Lifecycle events must be preserved as history. Current status should be derived from those events and stored only as a cache or convenience field.

### 3.3 Lineage Must Be Explicit

The system must make it easy to answer:

- what inoculated this bag
- what bags came from this source bag
- what runs and harvest outcomes are downstream of this source

### 3.4 Fast Farm Entry Beats Perfect Lab Detail

The design should support practical farm use first. Optional detail is acceptable, but the core workflow must stay fast enough for operators to use during production.

### 3.5 Contracts Must Be Shared

The backend API, frontend types, and tests must be aligned from one contract source so the current drift does not reappear.

### 3.6 Physical Workflow Wins

The software must respect the physical realities of the farm:

- labels cannot survive sterilization or pasteurization heat
- species may be unknown until inoculation
- operators need labels immediately after inoculation, not before

The design should model those realities directly instead of forcing a pre-inoculation label workflow.

## 4. Proposed Architecture

V1 should remain a three-part web app:

- `frontend`: Next.js operator UI
- `backend`: FastAPI application and domain logic
- `database`: PostgreSQL as the system of record

This is sufficient for v1. No additional services are required yet.

## 5. Data Model

## 5.1 Core Entities

### `bags`

One row per physical bag.

This table should use an internal primary key that is separate from the printable bag code.

Core fields:

- `bag_record_id`
- `bag_code` nullable until inoculation
- `bag_type` (`SPAWN` or `SUBSTRATE`)
- `species_id` nullable until inoculation if unknown earlier
- `current_status`
- `is_contaminated`
- `is_disposed`
- `disposed_at`
- `disposal_reason`
- `created_at`
- `labeled_at` nullable
- `run_bag_sequence` nullable
- `notes`

The `bags` table is the primary lookup table for operators and reporting.

Design note:

- `bag_record_id` is the stable internal identity from fill time through disposal.
- `bag_code` is the stable printable and scannable operational identity assigned after inoculation.

This separation is necessary because the team cannot label bags before heat processing and may not know the species until inoculation.

### `spawn_bag_details`

Type-specific data for spawn bags.

Suggested fields:

- `bag_record_id`
- `spawn_recipe_id`
- `grain_type_id`
- `fill_profile_id` or equivalent spawn fill definition
- `target_dry_kg`
- `target_water_kg`
- `actual_dry_kg` nullable
- `actual_water_kg` nullable
- `actual_vermiculite_kg` nullable
- `sterilization_run_id`

### `substrate_bag_details`

Type-specific data for substrate bags.

Suggested fields:

- `bag_record_id`
- `substrate_recipe_id`
- `fill_profile_id`
- `pasteurization_run_id`
- `target_dry_kg`
- `target_water_kg`
- `actual_dry_kg` nullable
- `actual_water_kg` nullable
- `actual_addins_notes` or structured add-in links

This table must hold the dry-weight inputs needed for biological-efficiency reporting.

### `sterilization_runs`

One row per autoclave run of spawn bags.

Suggested fields:

- `sterilization_run_id`
- `run_code`
- `spawn_recipe_id`
- `grain_type_id`
- `cycle_start_at`
- `cycle_end_at`
- `unloaded_at`
- `bag_count_planned`
- `bag_count_actual`
- `notes`

### `pasteurization_runs`

One row per steam pasteurization run of substrate bags.

Suggested fields:

- `pasteurization_run_id`
- `run_code`
- `substrate_recipe_id`
- `mix_lot_id`
- `steam_start_at`
- `steam_end_at`
- `unloaded_at`
- `bag_count_planned`
- `bag_count_actual`
- `notes`

### `liquid_cultures`

Lightweight first-class entity for spawn-bag inoculation source tracking.

Suggested fields:

- `liquid_culture_id`
- `culture_code`
- `species_id`
- `strain_name` nullable
- `vendor` nullable
- `lot_code` nullable
- `prepared_at` nullable
- `received_at` nullable
- `notes`

### `ingredients` and `ingredient_lots`

Keep these as reference data for substrate inputs and future cost or process tracking.

### `recipes` and `fill_profiles`

V1 should preserve separate recipe and fill definitions:

- spawn recipe
- substrate recipe
- fill profile / target weights

This lets the system distinguish formulation from expected bag fill.

## 5.2 Event Model

V1 should use dedicated domain event tables rather than a single untyped JSON event log.

This keeps reporting and lineage queries straightforward while still preserving history.

### `bag_status_events`

Generic lifecycle events that represent stage movement.

Suggested fields:

- `bag_status_event_id`
- `bag_record_id`
- `event_type`
- `occurred_at`
- `actor` nullable
- `notes`

Suggested event types:

- `BAG_CREATED`
- `RUN_ASSIGNED`
- `STERILIZED`
- `PASTEURIZED`
- `BAG_CODE_ASSIGNED`
- `INCUBATION_STARTED`
- `READY`
- `FRUITING_STARTED`
- `DISPOSED`
- `CONTAMINATION_FLAGGED`

### `inoculation_batches`

This is the key lineage table for v1.

One row represents one inoculation session using one source to inoculate many target bags.

Suggested fields:

- `inoculation_batch_id`
- `source_type` (`LIQUID_CULTURE` or `SPAWN_BAG`)
- `source_spawn_bag_id` nullable
- `liquid_culture_id` nullable
- `target_bag_type`
- `performed_at`
- `notes`

Behavior:

- When target bags in an inoculation batch do not yet have printable bag codes, the inoculation transaction should assign them.
- Label printing should happen immediately after successful inoculation recording.

### `inoculation_batch_targets`

Join table from one inoculation session to many target bags.

Suggested fields:

- `inoculation_batch_id`
- `target_bag_record_id`

Rules:

- One spawn bag may be the source for many target bags.
- A spawn bag used as a source is treated as fully consumed by that inoculation batch.
- No per-target quantity is required in v1.

### `harvest_events`

One row per harvest flush for a substrate bag.

Suggested fields:

- `harvest_event_id`
- `bag_record_id`
- `flush_number`
- `fresh_weight_kg`
- `harvested_at`
- `notes`

Constraints:

- unique `(bag_record_id, flush_number)`
- flush numbers limited to `1` and `2` in v1

## 5.3 Why This Model

This structure gives us:

- stable bag records
- label timing that matches the real farm workflow
- explicit lineage
- true event history
- derived status for fast UI filters
- clean reporting joins for contamination and efficiency

It also fits the real workflow better than the current model where bag creation happens too late, printable IDs are treated as the only identity, and one-to-many spawn usage is under-modeled.

## 6. Lifecycle And Status Design

## 6.1 Event History

Event history is immutable and append-only in normal operation.

Operators do not directly edit history rows except through admin correction workflows.

## 6.2 Derived Status

`bags.current_status` should be updated by backend domain logic whenever a new event is recorded.

This gives the UI simple filters without making status the source of truth.

## 6.3 Suggested Status Values

### Spawn bags

- `CREATED`
- `STERILIZED`
- `INOCULATED`
- `INCUBATING`
- `READY`
- `CONSUMED`
- `CONTAMINATED`
- `DISPOSED`

### Substrate bags

- `CREATED`
- `PASTEURIZED`
- `INOCULATED`
- `INCUBATING`
- `READY`
- `FRUITING`
- `FLUSH_1_COMPLETE`
- `FLUSH_2_COMPLETE`
- `CONTAMINATED`
- `DISPOSED`

## 6.4 Recommended Status Rules

- A bag is `CREATED` when filled and identified.
- A spawn bag becomes `STERILIZED` when its sterilization run completes.
- A substrate bag becomes `PASTEURIZED` when its pasteurization run completes.
- Any target bag in an inoculation batch becomes `INOCULATED`, then immediately `INCUBATING` if the farm treats inoculation as the start of incubation.
- Any target bag in an inoculation batch should also receive its printable `bag_code` if it does not already have one.
- A bag becomes `READY` when fully colonized.
- A substrate bag becomes `FRUITING` when moved into the fruiting tent.
- A substrate bag becomes `FLUSH_1_COMPLETE` after first harvest.
- A substrate bag becomes `FLUSH_2_COMPLETE` after second harvest.
- A source spawn bag becomes `CONSUMED` when used in an inoculation batch.
- A contaminated bag becomes `CONTAMINATED` and is then disposed through a disposal event.
- A spent bag becomes `DISPOSED` with disposal reason `SPENT`.

## 7. Workflow Design

## 7.1 Spawn Workflow

1. Create spawn bags at fill time.
2. Assign them to a sterilization run.
3. Record sterilization completion.
4. Record spawn inoculation:
   - by liquid culture, or
   - by donor spawn bag
5. Assign printable bag codes and print labels immediately after inoculation.
6. Record incubation start.
7. Record ready / fully colonized.
8. Use the ready spawn bag in one inoculation batch to create lineage to child bags.
9. Automatically mark the source spawn bag `CONSUMED`.

## 7.2 Substrate Workflow

1. Create substrate bags at fill time.
2. Assign them to a pasteurization run.
3. Record pasteurization completion.
4. Record substrate inoculation from one source spawn bag to many target substrate bags.
5. Assign printable bag codes and print labels immediately after inoculation.
6. Record incubation start.
7. Record ready / fully colonized.
8. Record fruiting start.
9. Record flush 1 harvest.
10. Record flush 2 harvest.
11. Record disposal as `SPENT` or `CONTAMINATION`.

## 7.3 Why Ready Events Matter

The design records an explicit `READY` event for both bag types.

Reasons:

- It distinguishes "in incubation" from "available for next step".
- It improves planning and throughput reporting.
- It avoids overloading fruiting or inoculation timestamps as a proxy for colonization completion.

## 7.4 Bag Code Timing

The design intentionally assigns printable bag codes after inoculation rather than at fill time.

Reasons:

- labels cannot survive the sterilizer or pasteurizer
- species may not be known until inoculation
- the operational bag code should reflect the actual inoculated bag, not a pre-inoculation placeholder

Implication:

- pre-inoculation tracking uses the internal bag record
- post-inoculation operations use the printable bag code

## 7.5 Printable Bag Code Format

The printable bag code should include:

- bag type
- run context
- species
- per-run or per-stem sequence

The printable bag code should not include inoculation-source type.

Reason:

- inoculation source belongs to traceability and lineage data
- bag codes should stay compact and operator-friendly
- changing or expanding inoculation-source modeling should not force bag-code redesign

## 8. Reporting Design

## 8.1 Biological Efficiency

Per substrate bag:

`bio_efficiency = total_fresh_harvest_weight_kg / dry_substrate_weight_kg`

Reporting rules:

- Prefer `actual_dry_kg`.
- Fall back to `target_dry_kg` only when actual is missing.
- Surface which denominator source was used.

## 8.2 Contamination Reporting

The reporting layer must support contamination summaries by:

- bag type
- species
- sterilization run
- pasteurization run
- source spawn bag
- liquid culture

## 8.3 Traceability Views

The product should support:

- run detail view with all bags in the run
- spawn bag detail with downstream child bags
- substrate bag detail with parent spawn bag and harvest totals
- species-level outcome summaries

## 9. API Design Direction

The backend should be organized around stable resources and event-recording endpoints.

## 9.1 Reference Resources

- `/species`
- `/grain-types`
- `/spawn-recipes`
- `/substrate-recipes`
- `/fill-profiles`
- `/ingredients`
- `/ingredient-lots`
- `/liquid-cultures`

These resources must support list/create/update where the UI needs them.

## 9.2 Operational Resources

- `/sterilization-runs`
- `/pasteurization-runs`
- `/bags`
- `/bags/{bag_code}`
- `/bag-records/{bag_record_id}` for internal or admin use when needed
- `/inoculation-batches`
- `/bags/{bag_code}/harvest-events`
- `/bags/{bag_code}/status-events`

## 9.3 Event Commands

Recommended command-style endpoints for operator workflows:

- `POST /bags/spawn/create`
- `POST /bags/substrate/create`
- `POST /sterilization-runs/{id}/complete`
- `POST /pasteurization-runs/{id}/complete`
- `POST /inoculation-batches`
- `POST /bags/{bag_code}/incubation-start`
- `POST /bags/{bag_code}/ready`
- `POST /bags/{bag_code}/fruiting-start`
- `POST /bags/{bag_code}/harvest-events`
- `POST /bags/{bag_code}/dispose`
- `POST /bags/{bag_code}/flag-contamination`

The exact route names can vary, but command endpoints should mirror operator actions and enforce domain rules centrally.

Design note:

- run-level and pre-label workflows should primarily use run resources and internal bag records
- operator scan workflows after labeling should primarily use `bag_code`

Recommended inoculation response behavior:

- return the updated target bags
- include assigned printable bag codes
- include label-print payloads for the newly inoculated bags

## 10. Frontend Design Direction

The frontend should favor fast operational workflows over generic admin CRUD screens.

## 10.1 Core Screens

- Dashboard
- Bags list
- Spawn bag detail
- Substrate bag detail
- Sterilization run detail
- Pasteurization run detail
- Inoculation batch entry
- Incubation entry
- Ready / colonized entry
- Fruiting entry
- Harvest entry
- Disposal / contamination entry
- Reference-data admin pages
- Reports page

## 10.2 UX Priorities

- batch-friendly creation flows
- scanning or quick bag lookup
- clear lineage display
- label printing directly after inoculation
- strong error messages when a bag cannot move to the next stage
- current status visible everywhere

## 10.3 Contract Safety

The frontend should not hand-maintain types that can drift from the backend.

Recommended direction:

- define API response schemas centrally
- generate or share frontend types from backend schemas
- make `tsc --noEmit` and production build required CI checks

## 11. Testing Strategy

This is the most important section for making development systematic.

## 11.1 Required Test Layers

### Unit tests

Test pure domain rules:

- bag ID generation
- status derivation
- biological-efficiency calculation
- contamination-rate calculation
- inoculation lineage rules

### Integration tests

Test the real workflow using the API and database:

- spawn bag creation through ready state
- spawn-bag-to-spawn-bag inoculation
- spawn-bag-to-substrate-bag inoculation
- substrate bag harvest flow
- contamination disposal flow
- reporting queries

### Migration tests

Test that a fresh database can apply all migrations successfully and produce the expected schema.

This is required because the current codebase shows schema drift risk.

### Frontend contract tests

At minimum:

- `tsc --noEmit`
- production build
- smoke tests for the main workflows

### End-to-end tests

Once the core workflows stabilize, add browser-based tests for:

- create bags
- record inoculation batch
- move bag to incubation
- move bag to fruiting
- record two harvests
- dispose bag

## 11.2 Minimum CI Gate

Every PR should run:

- backend tests
- migration-from-empty-database test
- frontend typecheck
- frontend build

Later, add end-to-end smoke tests.

## 11.3 Feature Development Workflow

Every feature or change should follow this sequence:

1. Update requirements if the user-facing behavior changes.
2. Update design if schema, status logic, lineage, or API contracts change.
3. Add or update acceptance criteria.
4. Write or update failing tests first when practical.
5. Implement backend domain logic and API.
6. Update shared types or generated contracts.
7. Implement frontend changes.
8. Run CI checks locally.
9. Review against workflow scenarios, not just code diff size.

## 12. Recommended Implementation Order

## Phase 0: Stabilize The Current Repo

- remove or repair stale block-centric pages
- align frontend routes with actual backend routes
- add frontend typecheck and build as local/CI requirements
- add migration tests
- fix bag ID uniqueness logic
- fix lifecycle status inconsistencies

This phase should happen before new feature work.

## Phase 1: Core Bag Lifecycle

- create internal bag records at fill time
- complete sterilization and pasteurization run workflows
- assign printable bag codes at inoculation time
- implement ready events
- implement inoculation batch model
- implement derived status updates

## Phase 2: Lineage And Reporting

- spawn-to-spawn lineage
- spawn-to-substrate lineage
- bag detail traceability views
- biological-efficiency reporting
- contamination reporting

## Phase 3: Operator Experience

- batch entry improvements
- scan-friendly workflows
- reports dashboard
- admin/reference-data cleanup

## 13. Remaining Open Questions

No major open product-design questions remain for Phase 0 and Phase 1.

Future questions can be handled as implementation details unless they change requirements.
