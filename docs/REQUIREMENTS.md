# Mushroom App V1 Requirements

Status: Draft v0
Last updated: 2026-03-24
Primary collaborator: Small mushroom farm team

## 1. Purpose

Mushroom App v1 is a bag-centric production tracking system for a small mushroom farm team.

The system must track individual spawn bags and substrate bags from creation through disposal so the team can:

- Trace contamination back to likely sources.
- Measure harvested yield per substrate bag.
- Calculate farm performance, including biological efficiency and contamination loss.
- Understand lineage between runs, bags, species, and harvest outcomes.

## 2. Product Goals

- Make each production bag individually traceable.
- Support the real-world farm workflow with minimal duplicate entry.
- Preserve lineage from inoculation source to downstream bags and harvest results.
- Give the team reliable yield and contamination reporting.
- Prepare the product for future expansion to other mushroom farms and hardware integrations.

## 3. Non-Goals For V1

- Multi-tenant SaaS features.
- Automated control of HVAC, humidifiers, or other farm hardware.
- Sensor ingestion from humidity, temperature, CO2, water-level, or camera systems.
- Computer vision or automated contamination detection.
- Edge AI features.

These may be future roadmap items, but they should not drive the v1 data model in a way that makes the current farm workflow harder.

## 4. Primary Users

- Farm operator: Creates bags, records inoculations, moves bags through incubation and fruiting, records harvests, and disposes contaminated or spent bags.
- Production lead: Reviews yields, contamination loss, and process performance across sterilization runs, pasteurization runs, species, and recipes.

## 5. Core Domain Concepts

- Spawn bag: A bag containing grain, water, and vermiculite that is sterilized, inoculated, incubated, and later used to inoculate other bags.
- Substrate bag: A bag containing wood pellets, soybean hull pellets, water, and optional add-ins that is pasteurized, inoculated with colonized grain, incubated, fruited, harvested, and disposed.
- Sterilization run: A batch of spawn bags sterilized together in the autoclave.
- Pasteurization run: A batch of substrate bags pasteurized together in the steam pasteurizer.
- Inoculation source: Either liquid culture or colonized grain from another spawn bag.
- Lineage: The parent/child relationship between the inoculation source bag and the bags it inoculates.
- Flush: A harvest cycle for a substrate bag. V1 supports first and second flush tracking.
- Disposal reason: At minimum `CONTAMINATION` or `SPENT`.

## 6. Workflow Summary

### 6.1 Spawn Bag Workflow

1. A spawn bag is filled with a spawn recipe made from grain, water, and vermiculite.
2. Spawn bags are grouped into a sterilization run and sterilized together.
3. After cooling, each spawn bag is inoculated either by:
   - liquid culture, or
   - colonized grain from another spawn bag.
4. The spawn bag is placed into incubation until fully colonized.
5. A fully colonized spawn bag may inoculate:
   - one or more substrate bags, and
   - sometimes one or more new spawn bags.
6. A spawn bag may be disposed of early if contamination is found.

### 6.2 Substrate Bag Workflow

1. A substrate bag is filled with a substrate recipe made from wood pellets, soybean hull pellets, water, and optional add-ins such as spent substrate.
2. Substrate bags are grouped into a pasteurization run and pasteurized together.
3. After cooling, each substrate bag is inoculated with grain from a colonized spawn bag.
4. The substrate bag is placed into incubation until fully colonized.
5. The substrate bag is moved into fruiting and cut open for mushroom formation.
6. Mushrooms are harvested and weighed for flush 1.
7. The bag returns to fruiting for flush 2.
8. Mushrooms are harvested and weighed for flush 2.
9. The spent or contaminated bag is disposed of.

## 7. Required Traceability

The system must preserve enough information to answer these questions for any bag:

- What species is in this bag?
- What recipe or fill configuration was used?
- Which sterilization run or pasteurization run was this bag part of?
- When was the bag inoculated?
- What was the inoculation source?
- Which spawn bag was used to inoculate this substrate bag?
- Which bags were inoculated by this spawn bag?
- When did the bag enter incubation?
- When did the bag enter fruiting?
- What were the first and second harvest weights and dates?
- When was the bag disposed, and why?
- If contamination occurred, what upstream run or parent bag might explain it?

## 8. Functional Requirements

### 8.1 Reference Data

- `FR-001` The system must manage mushroom species used in production.
- `FR-002` The system must manage spawn recipes.
- `FR-003` The system must manage substrate recipes.
- `FR-004` The system must manage grain types and substrate ingredient/add-in definitions needed for production tracking.

### 8.2 Run Tracking

- `FR-005` The system must record sterilization runs for spawn bags, including run identity, date/time, bag count, and relevant process notes.
- `FR-006` The system must record pasteurization runs for substrate bags, including run identity, date/time, bag count, and relevant process notes.
- `FR-007` Every spawn bag must be traceable to exactly one sterilization run.
- `FR-008` Every substrate bag must be traceable to exactly one pasteurization run.

### 8.3 Individual Bag Tracking

- `FR-009` The system must create a unique internal record for each spawn bag at fill time or before its sterilization run.
- `FR-010` The system must create a unique internal record for each substrate bag at fill time or before its pasteurization run.
- `FR-011` Internal bag record identifiers must remain stable for the life of the bag.
- `FR-012` Printable and scannable bag IDs must be generated after inoculation, when species and inoculation context are known, and must remain stable for the life of the bag once assigned.
- `FR-013` The system must support recording bag-level notes for exceptions or observations.

### 8.4 Spawn Bag Events

- `FR-014` The system must record when a spawn bag is created/filled.
- `FR-015` The system must record when a spawn bag is sterilized via its sterilization run.
- `FR-016` The system must record the inoculation of each spawn bag after cooling.
- `FR-017` For spawn bag inoculation, the system must support at least two inoculation source types:
  - liquid culture
  - donor spawn bag
- `FR-018` If a donor spawn bag is used, the lineage between parent and child spawn bags must be recorded.
- `FR-019` The system must record when a spawn bag enters incubation.
- `FR-020` The system must record when a spawn bag becomes fully colonized and ready to be used for downstream inoculation.
- `FR-021` The system must support one-to-many usage of a colonized spawn bag to inoculate multiple child bags over time.
- `FR-022` The system must allow a spawn bag to inoculate both substrate bags and other spawn bags.

### 8.5 Substrate Bag Events

- `FR-023` The system must record when a substrate bag is created/filled.
- `FR-024` The system must record when a substrate bag is pasteurized via its pasteurization run.
- `FR-025` The system must record which spawn bag inoculated each substrate bag.
- `FR-026` The system must record when a substrate bag enters incubation.
- `FR-027` The system must record when a substrate bag becomes fully colonized and ready for fruiting.
- `FR-028` The system must record when a substrate bag enters fruiting.
- `FR-029` The system must record first-harvest date and weight for each substrate bag.
- `FR-030` The system must record second-harvest date and weight for each substrate bag.
- `FR-031` The system must record disposal date and disposal reason for each substrate bag.
- `FR-032` The system must support early disposal of spawn bags or substrate bags due to contamination.

### 8.6 Reporting And Metrics

- `FR-033` The system must show total harvested weight per substrate bag.
- `FR-034` The system must support farm reporting for biological efficiency.
- `FR-035` The system must support contamination-loss reporting by:
  - species
  - sterilization run
  - pasteurization run
  - parent spawn bag
  - bag type
- `FR-036` The system must support lineage-aware investigation of contamination outcomes.
- `FR-037` The system must let the team review run-level outcomes, including which downstream bags and harvests came from a given run.

### 8.7 Workflow UX

- `FR-038` The system must support scan-friendly or fast-entry workflows for common bag events.
- `FR-039` The system must minimize duplicate entry by reusing known run, recipe, species, and lineage information.
- `FR-040` The system must be usable by a small farm team on shared devices such as desktops, laptops, or tablets.

## 9. Required Data Per Bag

At minimum, each bag record must support:

- stable internal record identifier
- printable and scannable bag ID assigned after inoculation
- bag type
- species, nullable until inoculation if unknown earlier
- recipe or fill context
- related run ID
- inoculation source
- incubation date
- ready / fully colonized date
- current state or latest lifecycle stage
- contamination status
- disposal date and disposal reason

At minimum, each substrate bag must also support:

- parent spawn bag
- fruiting date
- first harvest date and weight
- second harvest date and weight
- total harvested weight

At minimum, each spawn bag must also support:

- inoculation source type
- liquid culture reference or donor spawn bag reference
- downstream child bag links

## 10. Metrics Definitions Needed In V1

V1 must support the following operational metrics:

- harvested weight per substrate bag
- total harvested weight by species
- total harvested weight by pasteurization run
- contamination count and rate by bag type
- contamination count and rate by sterilization run and pasteurization run
- contamination count and rate by parent spawn bag
- biological efficiency

For v1, biological efficiency should be calculated as total fresh harvest weight divided by dry substrate weight.

The system should use actual recorded dry substrate weight when available. If actual dry substrate weight is not available, the system may fall back to a recipe or fill-profile target dry weight, but the source of the denominator should remain explicit.

## 11. Quality Requirements

- `NFR-001` Traceability data must be reliable enough for root-cause analysis.
- `NFR-002` Bag identity and lineage operations must avoid duplicate or conflicting records.
- `NFR-003` The system must preserve historical event data even when a bag changes lifecycle stage.
- `NFR-004` The app must support production use by a small team without requiring developer intervention for normal workflows.
- `NFR-005` The app must be testable in a way that validates real workflows, not only isolated CRUD functions.

## 12. Future Expansion Constraints

The v1 requirements should keep the door open for:

- external farm customers
- SaaS deployment
- standalone deployment
- sensor integrations
- camera integrations
- alerting and automation
- edge AI

However, these future possibilities should not add complexity that blocks or delays the core bag-tracking workflow.

## 13. Confirmed Design Inputs

- Lifecycle should be represented as both immutable event history and a derived current status.
- Liquid culture should be a first-class v1 entity, but lightweight.
- Spawn bag usage does not need partial-consumption quantity tracking in v1 because a spawn bag is considered fully consumed when used to inoculate child bags.
- Biological efficiency should use actual dry substrate weight when available, with recipe or fill-profile targets as an explicit fallback.
- The system should record "fully colonized / ready" timestamps for both spawn bags and substrate bags.
- V1 can assume a trusted internal team and does not require role-based permissions.
- Pre-inoculation handling can be managed at the run level and does not require a separate unlabeled-bag screen in v1.
- Printable bag codes should encode bag type, run context, species, and sequence, but should not encode inoculation-source type.
