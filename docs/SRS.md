> Source: owner-review draft prepared November 9, 2026 (Revision 1, changes accepted). This Markdown copy is the working reference for development. Requirement statuses are updated here as work lands.

**Mushroom Farm App: Software Requirements Specification**

Draft 1 for owner review, November 9, 2026

Revision 1, same date. Statuses updated from Claude Code's check of GitHub and the vault. BAG-11, RPT-10, SEC-6, SEC-7 and MNT-7 added.

Prepared for John Dryden, The Maury River Mushroom Farm

Baseline: github.com/byeonhosa/mushroom-app, branch main at commit 09a1278

Supersedes on approval: docs/REQUIREMENTS.md (Draft v0, March 24, 2026)

# 1. Introduction

## 1.1 Purpose

This document states what the Mushroom Farm App must do. It is written from three sources: the March 2026 requirements and design documents in the repository, the code as it stands today, and what has been learned about the farm's operation since. It records what is already built, what was required and never built, and what I propose to add or change. You are asked to review it and mark what to modify, add or remove. Once approved it replaces the March requirements as the reference for all further work.

## 1.2 Scope

The app is a production record for one mushroom farm. It follows each bag of grain spawn and each bag of substrate from the run in which it was heat-treated, through inoculation, incubation, fruiting and harvest, to disposal. From those records it reports yield, biological efficiency and contamination, and it shows which upstream culture, spawn or run a problem bag came from. It is used by the people who work at the farm, on a phone in the grow room and on a laptop elsewhere.

## 1.3 How to read the requirement tables

| **Column** | **Meaning**                                                                                                                                                                                                                                                                                                    |
|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ID         | A stable identifier. The prefix names the area (REF reference data, RUN runs, BAG bags, INO inoculation, LIF lifecycle, HAR harvest, DSP disposal, LBL labels, TRC traceability, RPT reports, DSH dashboard, SPR species reference, USR users, COR corrections, INV product disposition).                      |
| Pri        | M = must have for the farm to rely on the app. S = should have. C = could have.                                                                                                                                                                                                                                |
| Status     | **Built**: in the code at the baseline commit and exercised by tests or by my own check. **Partial**: some of it is built; the text says what is missing. **Not built**: required earlier, absent from the code. **Proposed**: new in this draft.                                                              |
| Origin     | Where the requirement comes from. FR and NFR numbers refer to the March requirements. "Code" means the behavior exists in the code and was never written down. "June plan" means the June 10 production review. "New" means proposed in this draft, with the change number from the status report (C1 to C20). |

Text in yellow brackets marks a point that needs your decision or a fact I could not confirm.

## 1.4 Definitions

| **Term**                   | **Meaning**                                                                                                                                                               |
|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Spawn bag                  | A bag of grain, water and vermiculite that is sterilized, inoculated and colonized, then used to inoculate other bags.                                                    |
| Substrate bag              | A bag of hardwood and soy hull pellets and water (with optional add-ins) that is pasteurized, inoculated, incubated, fruited and harvested. Also called a fruiting block. |
| Sterilization run          | One load of spawn bags through a pressure cooker or autoclave.                                                                                                            |
| Pasteurization run         | One load of substrate bags through the atmospheric steamer.                                                                                                               |
| Mix lot                    | One batch of mixed substrate, made to a recipe and a fill profile, that fills the bags of one or more pasteurization runs.                                                |
| Fill profile               | The target dry weight and water weight per substrate bag.                                                                                                                 |
| Liquid culture             | Mycelium grown in a nutrient liquid, used to inoculate spawn bags.                                                                                                        |
| Purchased spawn lot        | Colonized grain spawn bought from a supplier, identified by vendor and lot.                                                                                               |
| Inoculation session        | One sitting in which one source inoculates one or more bags. The code calls this an inoculation batch.                                                                    |
| Lineage                    | The chain from a bag back to its source and forward to the bags it inoculated.                                                                                            |
| Flush                      | One harvest from a substrate bag. A bag may give several.                                                                                                                 |
| Biological efficiency (BE) | Fresh harvest weight divided by the dry weight of the substrate in the bag, shown as a percentage.                                                                        |
| Internal ID                | The identifier a bag record receives when created, before it can be labeled (SPNREC-0001, SUBREC-0001).                                                                   |
| Bag code                   | The printable, scannable identifier assigned to a bag at inoculation.                                                                                                     |

## 1.5 References

- docs/REQUIREMENTS.md and docs/DESIGN.md, Draft v0, March 24, 2026.

- docs/OPERATIONS.md, Draft v1, March 26, 2026.

- docs/integration/public-website-integration-review.md and claude-code-production-app-fix-list.md, April 26, 2026.

- CLAUDE.md at the repository root.

- Mushroom Farm App Status Report, November 9, 2026.

# 2. Overall description

## 2.1 Product perspective

The app is a self-contained web application with three parts: a browser interface built with Next.js, an API built with FastAPI, and a PostgreSQL database. All three run in Docker containers on a single DigitalOcean droplet. It has no connection to any other system today. The farm's public website, its bookkeeping in FarmRaise, and any sensors in the grow tents are separate and stay separate in this version.

## 2.2 Users

| **User**      | **What they do in the app**                                                                                                                     | **Where**                                                                         |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| Operator      | Creates runs and bags, records inoculations, moves bags through the stages, records harvests and disposals, prints labels.                      | Phone or tablet in the work rooms and grow tents, often with wet or gloved hands. |
| Admin (owner) | Everything an operator does. Also maintains species, recipes and other reference data, corrects mistakes, manages users, and reads the reports. | Laptop or phone.                                                                  |

The March requirements assumed a trusted team and no sign-in. This draft changes that (section 4.14). <span class="mark">\[Decision: confirm the two roles and who holds each.\]</span>

## 2.3 Operating environment

- Server: one Linux droplet running Docker Compose with PostgreSQL 16, the API on Python 3.12, and the frontend on Node 22.

- Clients: current versions of Chrome and Safari on phones and laptops. No installed app.

- Network: the farm's sites have ordinary internet service. The app does not need to work offline. <span class="mark">\[Decision: confirm connectivity in the VIA fruiting room and at the garage.\]</span>

- Label printing: from the browser to a printer the farm supplies. <span class="mark">\[Decision: printer model and label size.\]</span>

## 2.4 Constraints

- Labels do not survive the pressure cooker or the steamer. A bag cannot carry a printed code until after heat treatment.

- The species going into a bag may not be known until it is inoculated.

- Development is done through Claude Code with pull requests, automated tests as the gate, and automatic deployment on merge. Requirements should be small enough to deliver and test one at a time.

- Database changes are numbered raw SQL migration files applied in order. They only move forward.

## 2.5 Assumptions

- One farm. No second farm will share the database in this version.

- Volume up to 100 pounds of fresh mushrooms a week. I have taken that to mean fewer than 100 new substrate bags a week and about 5,000 bag records a year. <span class="mark">\[Confirm or correct these figures; the performance targets in section 7.3 rest on them.\]</span>

- No more than ten user accounts and three people using the app at the same moment.

- Weights are stored in kilograms and temperatures in the units entered. Display units are a setting.

## 2.6 Out of scope for this version

| **Item**                                                                   | **Why it is out**                                                                 | **Where it stands**                                                       |
|----------------------------------------------------------------------------|-----------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| Cost per bag, overhead allocation, COGS, profitability                     | FarmRaise is the farm's system of record for money.                               | In the February concept. Dropped in March. Recommended to stay out (C18). |
| Customer accounts, orders, invoices, payments                              | Belongs to the website and the books.                                             | Never in scope.                                                           |
| Public website sync: availability feed, product mapping, order reservation | No value until the farm's own records are in the app.                             | Designed in the April integration review. Deferred (C19).                 |
| Sensor data, environment logs, control of humidifiers or fans              | Excluded in March so that it would not shape the core model.                      | Deferred (C19).                                                           |
| Multiple farms, other crops, subscription billing                          | A commercial product question, to be taken up after the farm's own use is proven. | Deferred (C19).                                                           |
| Image recognition of contamination                                         | A research topic with no present farm need.                                       | Deferred.                                                                 |

# 3. The production model

## 3.1 The two workflows

**Spawn.** Fill spawn bags. Sterilize them together as a run. After cooling, inoculate each bag from a liquid culture or from another colonized spawn bag. Label. Incubate until fully colonized. Use the colonized bag to inoculate substrate bags or more spawn bags. Dispose of it early if it contaminates.

**Substrate.** Mix a lot of substrate. Fill bags. Pasteurize them together as a run. After cooling, inoculate each bag with colonized grain from a spawn bag or, as proposed here, from a purchased spawn lot. Label. Incubate until fully colonized. Move to fruiting. Harvest each flush and weigh it. Dispose of the bag when spent or contaminated.

## 3.2 Bag statuses

A bag's status is worked out from its recorded events and is never typed in. The statuses in the code today are below. Section 4.6 proposes replacing the two fixed flush statuses with a single harvesting status that carries a flush count.

| **Bag type** | **Status**                         | **Reached when**                                     |
|--------------|------------------------------------|------------------------------------------------------|
| Spawn        | STERILIZED                         | The bag record is created from a sterilization run.  |
| Spawn        | INOCULATED                         | An inoculation session names it as a target.         |
| Spawn        | INCUBATING                         | Incubation start is recorded.                        |
| Spawn        | READY                              | Marked fully colonized.                              |
| Spawn        | CONSUMED                           | Used as the source of an inoculation session.        |
| Substrate    | PASTEURIZED                        | The bag record is created from a pasteurization run. |
| Substrate    | INOCULATED, INCUBATING, READY      | As for spawn.                                        |
| Substrate    | FRUITING                           | Fruiting start is recorded.                          |
| Substrate    | FLUSH_1_COMPLETE, FLUSH_2_COMPLETE | One harvest, then two harvests, are recorded.        |
| Either       | CONTAMINATED                       | Disposed with reason contamination. Final.           |
| Either       | DISPOSED                           | Disposed for any other reason. Final.                |

## 3.3 Bag identity

Each bag has two identifiers. The internal ID exists from the moment the record is created and never changes. The bag code is printed on the label and is assigned at inoculation, when the species is known and the bag has cooled. Either can be used to look up a bag anywhere in the app.

Since WP-1 a bag code is built from the bag type (SP for spawn, SB for substrate), the species code, the run code and the bag's number in its run, for example SB-LM-261109A-07 (BAG-5). The run code is the run's date as YYMMDD and a letter for its place in the day (RUN-6); sterilization and pasteurization runs are lettered separately. The number is the bag's place in the run whatever species went into it, so a run of twenty bags inoculated with two species still reads 01 to 20. With a species code of two or three characters and at most 999 bags in a run the code is never longer than 18 characters. The recipe stays in the record and is not on the label. Until WP-1 the code was built from a type prefix, the run code, the recipe code, the species code and a sequence number, for example PAST-PAST-20261109-001-MM-LM-0001; no code in that form was ever printed. <span class="mark">\[Decision: approve this format or give me the one you want. Codes are permanent once printed.\]</span>

# 4. Functional requirements

## 4.1 Reference data

| **ID** | **Requirement**                                                                                                                                                                                     | **Pri** | **Status**                                                                                                              | **Origin**          |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|-------------------------------------------------------------------------------------------------------------------------|---------------------|
| REF-1  | The system shall keep a list of species with a short code, common name, Latin name, notes and an active flag. An admin can add, edit and deactivate a species.                                      | M       | Built. Since WP-3 each species also has a slug shared with the farm website, which never changes once set, and the fields the website reads (tier, sale state, in rotation, restriction).                                                                                                                   | FR-001              |
| REF-2  | Each species shall carry a cultivation profile: incubation and fruiting temperature, humidity, CO2, colonization days, pin-to-harvest days, expected biological efficiency and typical flush count. | S       | Built (WP-3). Every species has one profile, linked to it. Editing a profile in the app is SPR-3. | Code; New (C13)     |
| REF-3  | The system shall keep spawn recipes (code, description). An admin can add and edit them.                                                                                                            | M       | Built (WP-3): the Recipes screen. A code is capital letters, digits and hyphens | FR-002              |
| REF-4  | The system shall keep substrate recipes with versions (name, code, description). An admin can add and edit them.                                                                                    | M       | Built (WP-3): the Recipes screen. A changed recipe is entered as a new recipe and the old one deactivated, so earlier runs keep the recipe they were made with | FR-003              |
| REF-5  | The system shall keep fill profiles giving target dry weight and target water weight per bag. An admin can add and edit them.                                                                       | M       | Built (WP-3): the Recipes screen. Bags already created keep the weight they were created with | Code                |
| REF-6  | The system shall keep grain types.                                                                                                                                                                  | M       | Built. In the menu; can be deactivated (WP-3) | FR-004              |
| REF-7  | The system shall keep ingredients and ingredient lots (vendor, lot code, date received).                                                                                                            | S       | Partial. Add and list on the screen, now in the menu. Rename and deactivate through the API only. A unit cost field exists and is used by nothing. | FR-004              |
| REF-8  | The system shall record mix lots with a lot code, recipe version, fill profile, date mixed and notes.                                                                                               | M       | Built. No edit.                                                                                                         | Code                |
| REF-9  | A mix lot may list add-ins drawn from ingredient lots, by dry weight or by percentage of the base mix.                                                                                              | C       | Not built. The table exists with no route or screen.                                                                    | Code                |
| REF-10 | The system shall keep liquid cultures with a code, species, source, date prepared, notes and an active flag. Only an active culture can be used to inoculate.                                       | M       | Built. Source, date, notes and the active flag can be changed (WP-3); the code and the species cannot, because bag codes and lineage rest on them | FR-017              |
| REF-11 | The system shall keep purchased spawn lots with vendor, vendor lot number, species, grain type, date received, quantity, notes and an active flag. Each lot gets a code of the form `PL-{species}-{date received}{letter}`. | M       | Built (WP-3). Any signed-in user can record a lot | New (C1)            |
| REF-12 | A liquid culture may name the culture it was made from, so that a contaminated culture can be traced to its parent.                                                                                 | C       | Built (WP-3). The parent must be of the same species and cannot be the culture itself or one of its descendants | New                 |
| REF-13 | When a species is added the system shall suggest a unique code.                                                                                                                                     | C       | Not built. A species code must be two or three letters or digits (WP-1) and its slug is made from its name (WP-3)                                                                                                               | docs/BACKLOG.md 001 |
| REF-14 | A reference record that is in use shall not be deleted. It is deactivated and remains visible on the records that used it.                                                                          | M       | Built for species, recipes, fill profiles, grain types, ingredients, liquid cultures and purchased lots (WP-3). No route deletes any of them. A deactivated record is refused for new runs and mix lots | NFR-002             |

## 4.2 Runs

| **ID** | **Requirement**                                                                                                                                                                                | **Pri** | **Status**                                                                                                     | **Origin** |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|----------------------------------------------------------------------------------------------------------------|------------|
| RUN-1  | The system shall record a sterilization run with a unique run code, spawn recipe, grain type, cycle start and end, unload time, planned bag count, temperature, pressure, hold time and notes. | M       | Built                                                                                                          | FR-005     |
| RUN-2  | The system shall record a pasteurization run with a unique run code, mix lot, recipe version, steam start and end, unload time, planned bag count and notes.                                   | M       | Built                                                                                                          | FR-006     |
| RUN-3  | The planned bag count shall be a whole number greater than zero. The system shall refuse to create more bag records in a run than its planned count.                                           | M       | Built (WP-1). The count must be from 1 to 999.                                        | Code       |
| RUN-4  | A run page shall list every bag in the run with its status, and for each the downstream bags and harvest results.                                                                              | M       | Built                                                                                                          | FR-037     |
| RUN-5  | An admin can edit a run's details after it is created.                                                                                                                                         | S       | Not built. The functions exist with no route.                                                                  | New (C14)  |
| RUN-6  | The system shall propose the next run code from the date and a daily letter (for example 261109A), so that the operator does not type it.                                                      | S       | Built (WP-1). The form fills the code in from the unload date; the API refuses a code outside the format.                                                                                                       | New (C6)   |
| RUN-7  | A run code that already exists shall be refused with a clear message.                                                                                                                          | M       | Built (WP-1). The same answer on PostgreSQL and on the test database. | Code       |
| RUN-8  | Run lists can be filtered by code and sorted. An unknown sort field shall be refused with a message and shall not cause a server error.                                                        | C       | Built (WP-1). An unknown field or order is answered with a message listing the fields allowed.                                                                | Code       |

## 4.3 Bags

| **ID** | **Requirement**                                                                                                                                                              | **Pri** | **Status**                                                                                       | **Origin**    |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|--------------------------------------------------------------------------------------------------|---------------|
| BAG-1  | The system shall create bag records in bulk from a run before inoculation. Each record receives an internal ID that never changes.                                           | M       | Built                                                                                            | FR-009 to 011 |
| BAG-2  | Every spawn bag shall belong to exactly one sterilization run and every substrate bag to exactly one pasteurization run.                                                     | M       | Built                                                                                            | FR-007, 008   |
| BAG-3  | A substrate bag shall take its target dry weight from the fill profile of its mix lot when created. An actual dry weight can be entered then or later.                       | M       | Built                                                                                            | Code          |
| BAG-4  | A bag code shall be assigned at inoculation, shall be unique, and shall never change.                                                                                        | M       | Built                                                                                            | FR-012        |
| BAG-5  | The bag code shall be at most 18 characters and shall show bag type, species, run and the bag's number in the run.                                                           | M       | Built (WP-1). SB-LM-261109A-07. Codes issued before the change are not rewritten.                          | New (C6)      |
| BAG-6  | Wherever a bag is entered, the internal ID or the bag code shall both be accepted.                                                                                           | M       | Built                                                                                            | Code          |
| BAG-7  | The bag list can be filtered by type, status, species and run, and searched by any part of the code.                                                                         | M       | Built. The screen offers search, type and status. Species and run filters exist in the API only. | FR-038        |
| BAG-8  | A bag page shall show the bag's source, run, species, full event timeline, harvests, total harvest, biological efficiency and, for a spawn bag, every bag descended from it. | M       | Built                                                                                            | FR-033, 036   |
| BAG-9  | A note can be added to a bag at any time.                                                                                                                                    | S       | Not built. The field exists and cannot be set.                                                   | FR-013        |
| BAG-10 | A bag shall have a location (site and room or tent). Moving a bag is recorded as an event. A whole run can be moved at once.                                                 | S       | Proposed. A zones table is seeded and unused.                                                    | New (C16)     |
| BAG-11 | Two users creating bags at the same moment shall never receive the same ID or cause an error.                                                                                | S       | Met (WP-1). Internal IDs come from a locked counter; an inoculation session locks its run. Tested with eight simultaneous sessions on PostgreSQL.                                | June plan     |

## 4.4 Inoculation

| **ID** | **Requirement**                                                                                                                                                                                                                                          | **Pri** | **Status**                                                          | **Origin**  |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|---------------------------------------------------------------------|-------------|
| INO-1  | The system shall inoculate a chosen number of unlabeled spawn bags in a sterilization run from a liquid culture. The bags take the culture's species and receive bag codes.                                                                              | M       | Built                                                               | FR-016, 017 |
| INO-2  | The system shall inoculate spawn bags from a donor spawn bag. The donor must be marked ready and must not be consumed. The parent and child link is recorded.                                                                                            | M       | Built                                                               | FR-018, 022 |
| INO-3  | The system shall inoculate a chosen number of unlabeled substrate bags in a pasteurization run from one ready spawn bag. The bags take the spawn bag's species and receive bag codes. The link is recorded.                                              | M       | Built                                                               | FR-025      |
| INO-4  | An inoculation session can carry the time it was done and a note.                                                                                                                                                                                        | M       | Built                                                               | Code        |
| INO-5  | A bag can be inoculated only once. A disposed bag cannot be inoculated.                                                                                                                                                                                  | M       | Built                                                               | NFR-002     |
| INO-6  | The system shall inoculate substrate bags and spawn bags from a purchased spawn lot. The bags take the lot's species. The lot is recorded as the source. | M       | Built (WP-3) | New (C1)    |
| INO-7  | A purchased spawn lot can be the source of any number of sessions, until the operator marks it used up; it can be reopened if that was a mistake. One of the farm's own spawn bags is consumed by its first session. An administrator setting shall allow partial use of the farm's own spawn bags. | S       | Purchased lots: built (WP-3). The setting for the farm's own spawn bags: not built (WP-4, with the other farm settings) | New (C2)    |
| INO-8  | After a session the system shall offer the new bag codes for label printing in one step.                                                                                                                                                                 | M       | Built                                                               | FR-012      |
| INO-9  | The system shall warn when the source's species differs from the species the operator expected for the run, if one was planned.                                                                                                                          | C       | Proposed                                                            | New         |

## 4.5 Lifecycle events

| **ID** | **Requirement**                                                                                                                                                | **Pri** | **Status**                                                                                       | **Origin**  |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|--------------------------------------------------------------------------------------------------|-------------|
| LIF-1  | The system shall record incubation start for an inoculated bag.                                                                                                | M       | Built                                                                                            | FR-019, 026 |
| LIF-2  | The system shall record that a bag is ready (fully colonized). Incubation must have started.                                                                   | M       | Built                                                                                            | FR-020, 027 |
| LIF-3  | The system shall record fruiting start for a ready substrate bag.                                                                                              | M       | Built                                                                                            | FR-028      |
| LIF-4  | Each event shall be stored as a permanent history row with its type, time, detail and note. Status is derived from the history.                                | M       | Built                                                                                            | NFR-003     |
| LIF-5  | Recording a step that is already recorded shall change nothing and shall not raise an error.                                                                   | M       | Built                                                                                            | Code        |
| LIF-6  | Every event can carry the date and time it happened and a note. The default is now. A date in the future, or earlier than the bag's previous step, is refused. | M       | Partial. Inoculation and harvest accept a time. Incubation, ready, fruiting and disposal do not. | New (C4)    |
| LIF-7  | A step can be recorded for every eligible bag in a run in one action, or for a list of scanned bags in one action.                                             | S       | Not built. One bag per action.                                                                   | New (C9)    |
| LIF-8  | Incubation shall start automatically when a bag is inoculated. <span class="mark">\[Decision: or keep incubation as a separate step.\]</span>                  | S       | Proposed. The March design allowed either.                                                       | New (C9)    |
| LIF-9  | A disposed or consumed bag shall accept no further events.                                                                                                     | M       | Built                                                                                            | Code        |

## 4.6 Harvest

| **ID** | **Requirement**                                                                                                                                                                                                                                                  | **Pri** | **Status**                                                                      | **Origin**  |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|---------------------------------------------------------------------------------|-------------|
| HAR-1  | The system shall record a harvest for a fruiting substrate bag with flush number, fresh weight, time and note.                                                                                                                                                   | M       | Built                                                                           | FR-029, 030 |
| HAR-2  | There shall be one harvest record per bag per flush.                                                                                                                                                                                                             | M       | Built                                                                           | NFR-002     |
| HAR-3  | Flush numbers shall run from 1 to a maximum set by the admin, four by default. The two fixed flush statuses are replaced by one harvesting status with a flush count.                                                                                            | M       | Partial. Fixed at two flushes.                                                  | New (C3)    |
| HAR-4  | The system shall propose the next flush number for the bag. It shall ask for confirmation when the weight exceeds the bag's dry substrate weight.                                                                                                                | S       | Not built. Flush 2 is accepted before flush 1. Any positive weight is accepted. | New         |
| HAR-5  | Weight can be entered in grams, kilograms, or pounds and ounces according to a farm setting. It is stored in kilograms and reports show the farm's unit.                                                                                                         | S       | Proposed. Kilograms only.                                                       | New (C11)   |
| HAR-6  | One weight can be recorded for a group of bags of the same run and species. The system divides it among the bags in proportion to dry weight and marks each record as allocated. <span class="mark">\[Decision: is group weighing how you want to work?\]</span> | S       | Proposed                                                                        | New (C10)   |
| HAR-7  | The system shall show total harvest for each substrate bag.                                                                                                                                                                                                      | M       | Built                                                                           | FR-033      |
| HAR-8  | A harvest can be given a grade (first quality, seconds, unsaleable).                                                                                                                                                                                             | C       | Proposed                                                                        | New         |

## 4.7 Disposal

| **ID** | **Requirement**                                                                                                                                                                  | **Pri** | **Status**                                                                               | **Origin**         |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|------------------------------------------------------------------------------------------|--------------------|
| DSP-1  | The system shall record disposal of a bag with a time and a reason. The reasons today are contamination and final harvest.                                                       | M       | Built. The March text called the second reason "spent"; the code calls it final harvest. | FR-031, 032        |
| DSP-2  | Final harvest applies only to a substrate bag with at least one harvest.                                                                                                         | M       | Built                                                                                    | Code               |
| DSP-3  | Further reasons shall be available: failed to fruit, damaged, and other with a note. A contamination disposal can name the type observed (green mold, bacterial, cobweb, other). | S       | Proposed                                                                                 | New                |
| DSP-4  | A bag can be flagged as suspect and set aside before it is disposed of.                                                                                                          | C       | Not built. Listed in the March design.                                                   | docs/DESIGN.md 5.2 |

## 4.8 Labels and scanning

| **ID** | **Requirement**                                                                                                                                                            | **Pri** | **Status**                                                           | **Origin**        |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|----------------------------------------------------------------------|-------------------|
| LBL-1  | The system shall print a label for each bag code with a QR code and the code in readable text.                                                                             | M       | Built. One-inch square, four across, printed from the browser.       | FR-012            |
| LBL-2  | A label can be reprinted from the bag page.                                                                                                                                | S       | Not built                                                            | New               |
| LBL-3  | The label layout shall match the farm's printer and stock and stay readable after two weeks in a fruiting tent. <span class="mark">\[Decision: printer and stock.\]</span> | M       | Not verified on real stock.                                          | New               |
| LBL-4  | The label shall also show the species name and inoculation date in plain text.                                                                                             | S       | Proposed                                                             | New               |
| LBL-5  | Every screen that takes a bag code shall accept a scan from the phone's camera as well as typed entry or a handheld scanner.                                               | S       | Partial. Typed entry and handheld scanners work. No camera scanning. | FR-038; New (C12) |

## 4.9 Traceability

| **ID** | **Requirement**                                                                                                                                                                              | **Pri** | **Status**                                                                                     | **Origin**      |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|------------------------------------------------------------------------------------------------|-----------------|
| TRC-1  | For any bag the system shall show its species, recipe, run, inoculation time and source, parent spawn bag, child bags, stage dates, harvest weights and dates, and disposal time and reason. | M       | Built                                                                                          | March section 7 |
| TRC-2  | For any spawn bag the system shall show all descendants through every generation, with their outcomes.                                                                                       | M       | Built                                                                                          | FR-021, 036     |
| TRC-3  | For any bag the system shall work out the liquid culture or purchased spawn lot at the root of its line and its spawn generation. Spawn made from a purchased lot is generation 1; substrate inoculated straight from a purchased lot is generation 0. | M       | Built | FR-036          |
| TRC-4  | For any liquid culture or purchased spawn lot the system shall show every bag descended from it and the contamination rate and yield of those bags.                                          | S       | Partial. Reports group contamination by liquid culture. There is no page for a single culture. | New             |

## 4.10 Reports

| **ID** | **Requirement**                                                                                                                                                                                      | **Pri** | **Status**                                                                                         | **Origin**                  |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|----------------------------------------------------------------------------------------------------|-----------------------------|
| RPT-1  | Biological efficiency for a substrate bag is total fresh harvest divided by dry substrate weight. The actual dry weight is used when recorded, otherwise the target, and the report says which.      | M       | Built                                                                                              | FR-034                      |
| RPT-2  | Contamination count and rate shall be reported by bag type, species, liquid culture, purchased spawn lot, source type, spawn generation, sterilization run, pasteurization run and parent spawn bag. | M       | Built | FR-035                      |
| RPT-3  | For each pasteurization run the system shall report bags, contaminated bags, total harvest, dry weight and biological efficiency.                                                                    | M       | Built. The ready count defect was fixed in WP-1: only bags marked ready are counted | FR-037                      |
| RPT-4  | Total harvest and biological efficiency shall be reported by species, by substrate recipe and by fill profile.                                                                                       | M       | Not built. Harvest by species was in the March metric list.                                        | March section 10; New (C15) |
| RPT-5  | Every report can be limited to a date range. A weekly view shall show harvest by species for each week.                                                                                              | M       | Not built. Reports cover all time.                                                                 | New (C15)                   |
| RPT-6  | The system shall list records that look wrong: inoculated bags with no source or species, ready without incubation, fruiting without ready, final harvest with no harvest.                           | S       | Built. Seven checks.                                                                               | Code                        |
| RPT-7  | The system shall report average days from inoculation to ready, ready to fruiting, and fruiting to first harvest, by species.                                                                        | S       | Not built                                                                                          | New                         |
| RPT-8  | The system shall forecast harvest weight by species and week from the bags now incubating and fruiting, using the farm's own averages where enough history exists and the species profile otherwise. | S       | Proposed. Second phase.                                                                            | New (C17)                   |
| RPT-9  | Any report table can be downloaded as a CSV file.                                                                                                                                                    | S       | Not built                                                                                          | New (C15)                   |
| RPT-10 | A bag whose biological efficiency exceeds a limit set by the admin, 200 percent by default, shall be listed as a data-quality issue.                                                                 | S       | Not built. The June 10 review saw 285 percent displayed with no warning.                           | June plan                   |

## 4.11 Dashboard

| **ID** | **Requirement**                                                                                                                                                                                                                                                                      | **Pri** | **Status**           | **Origin** |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|----------------------|------------|
| DSH-1  | The opening screen shall show how many bags are waiting at each stage, with a link to the list: spawn awaiting inoculation, ready spawn, substrate awaiting inoculation, substrate incubating, substrate ready, substrate fruiting, bags due a further flush, and contaminated bags. | M       | Built. Eight queues. | Code       |
| DSH-2  | It shall list recent sterilization and pasteurization runs with the next action due on each.                                                                                                                                                                                         | M       | Built                | Code       |
| DSH-3  | It shall show the most recent bag events and any contamination or data-quality alerts.                                                                                                                                                                                               | S       | Built                | Code       |
| DSH-4  | It shall flag bags that have stayed in a stage longer than the species profile expects.                                                                                                                                                                                              | S       | Proposed             | New        |

## 4.12 Species reference

| **ID** | **Requirement**                                                                                                                                                                                                          | **Pri** | **Status**                                                  | **Origin**           |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|-------------------------------------------------------------|----------------------|
| SPR-1  | The system shall show a reference page of cultivation parameters by species that can be searched, filtered and sorted.                                                                                                   | S       | Built for all 18 varieties (WP-3).                                        | Code (PR \#20)       |
| SPR-2  | The reference shall cover the farm's full list of 18 varieties, with availability tier, whether in rotation, sale path and restrictions. Values taken from research and not from the farm's sources stay marked as such. | S       | Built (WP-3). The June dataset was lost; the list was rebuilt from the website's own species list and the profiles from the farm's sources (11 varieties) and outside research (7), each marked on the page. Sources: docs/research/species-profiles-2026-11-11.md. | June plan; New (C13) |
| SPR-3  | An admin can edit profile values in the app.                                                                                                                                                                             | C       | Not built. Depends on sign-in.                              | June plan            |

## 4.13 Corrections

| **ID** | **Requirement**                                                                                                                                                                                                  | **Pri** | **Status** | **Origin**                   |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|------------|------------------------------|
| COR-1  | An admin can amend the time or weight of a recorded event, or void an event entered in error, including a disposal. The original stays in the history, marked as superseded, with who changed it, when, and why. | M       | Not built  | docs/DESIGN.md 6.1; New (C5) |
| COR-2  | After a correction the bag's status and every affected report shall be recalculated.                                                                                                                             | M       | Not built  | New (C5)                     |
| COR-3  | An admin can void a bag record that was created in error and never inoculated.                                                                                                                                   | S       | Not built  | New (C5)                     |

## 4.14 Users and access

| **ID** | **Requirement**                                                                                                                                                               | **Pri** | **Status**                                                                                                                                                                         | **Origin**                               |
|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| USR-1  | Every screen and every API route except the health checks shall require a signed-in user.                                                                                     | M       | Built (WP-2). A test walks every route in the API and requires 401 without a session.                                                                                                                                                    | New (C7). Reverses the March assumption. |
| USR-2  | There shall be two roles. An operator can create runs and bags, record events and read reports. An admin can also maintain reference data, make corrections and manage users. | M       | Built (WP-2). Enforced in the API, not only in the menu. An operator may also record the inputs of a run: mix lots, liquid cultures and ingredient lots (decision D-018).                                                                                                                                                                          | New (C7)                                 |
| USR-3  | Passwords shall be stored hashed. Sessions shall expire. The first admin account is created from server configuration at install.                                             | M       | Built (WP-2) to the April design: server-side sessions, bcrypt, first administrator from deployment settings. A session ends after 14 days unused or 30 days in all. | New (C7)                                 |
| USR-4  | Each event shall record which user entered it.                                                                                                                                | S       | Built (WP-2) for bag events and harvests; the bag page shows who entered each.                                                                                                                                                                          | New (C7)                                 |

## 4.15 Product disposition (second phase)

These requirements extend the record one step past harvest. They are the largest addition in this draft and depend on your answer to the scope question in the status report. <span class="mark">\[Decision: include, defer, or strike this section.\]</span>

| **ID** | **Requirement**                                                                                                                                                                      | **Pri** | **Status** | **Origin** |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|------------|------------|
| INV-1  | The system shall show, for any week, the weight harvested of each species.                                                                                                           | S       | Proposed   | New (C17)  |
| INV-2  | The operator can record where each week's harvest of a species went, by weight: restaurants, farmers markets, value-added products, and waste. No customer names or prices are kept. | S       | Proposed   | New (C17)  |
| INV-3  | The admin can record a standing weekly quantity per species committed to restaurants. The forecast in RPT-8 shall show the surplus or shortfall against it.                          | C       | Proposed   | New (C17)  |

# 5. Data requirements

## 5.1 Records kept

| **Record**                                                                             | **Main contents**                                                                                            | **Table at baseline**                                                |
|----------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| Species                                                                                | Code, name, Latin name, active flag                                                                          | mushroom_species                                                     |
| Species profile                                                                        | Cultivation ranges, expected yield, notes                                                                    | species_profiles                                                     |
| Spawn recipe; substrate recipe version; fill profile; grain type                       | Codes, names, target weights                                                                                 | spawn_recipes, substrate_recipe_versions, fill_profiles, grain_types |
| Ingredient; ingredient lot; mix-lot add-in                                             | Name, vendor, lot, date received, quantity added                                                             | ingredients, ingredient_lots, mix_lot_addins                         |
| Mix lot                                                                                | Lot code, recipe, fill profile, date mixed                                                                   | mix_lots                                                             |
| Liquid culture                                                                         | Code, species, source, date prepared, active flag                                                            | liquid_cultures                                                      |
| Sterilization run; pasteurization run                                                  | Run code, inputs, times, planned bag count, process readings                                                 | sterilization_runs, pasteurization_runs                              |
| Bag                                                                                    | Internal ID, bag code, type, species, run, recipe, source, dry weights, stage times, disposal reason, status | bags                                                                 |
| Bag event                                                                              | Bag, event type, time, detail, note                                                                          | bag_status_events                                                    |
| Inoculation session and its targets                                                    | Source type, source, species, time, the bags inoculated                                                      | inoculation_batches, inoculation_batch_targets, inoculations         |
| Harvest                                                                                | Bag, flush number, fresh weight, time, note                                                                  | harvest_events                                                       |
| Proposed: purchased spawn lot, user, correction log, bag location, product disposition | As described in section 4                                                                                    | None yet                                                             |

## 5.2 Rules the data must obey

- Run codes, bag codes, species codes, recipe codes, mix lot codes and liquid culture codes are each unique.

- A bag has one run, at most one inoculation, and at most one harvest record per flush.

- Harvest weight is greater than zero. Planned bag count is greater than zero.

- Events on a bag fall in order: inoculation, incubation, ready, then for substrate fruiting, harvests and disposal.

- Event history is added to and never overwritten. A correction adds a row and marks the old one superseded.

- No bag, run or event is deleted through the app.

- Times are stored in UTC and shown in Eastern time. Every time the API sends shall carry its UTC offset. The June 10 review found one harvest shown at two different times on the same page. Since WP-1 every time in a response is normalised to UTC with its offset, and a time sent to the API without an offset is refused.

## 5.3 Retention

All production records are kept without limit. <span class="mark">\[Decision: confirm. If any product is later sold as a supplement, lot records will need a stated retention period.\]</span>

# 6. External interfaces

## 6.1 User interface

- A responsive web interface. Event screens (inoculation, incubation, ready, fruiting, harvest, disposal) are designed for a phone first.

- The menu is grouped by task (daily work, runs, reports, setup) and collapses on a small screen. Since WP-2 it collapses behind a Menu button below 980 pixels; grouping by task is WP-5.

- Errors are shown as a plain sentence saying what was wrong and what to do. Since WP-2 the screens show the server's own sentence and no longer the raw response; the wording of each message is reviewed in WP-5.

## 6.2 API

- A REST API under /api, described by an OpenAPI document generated from the code. At the baseline it has 51 operations on 42 paths.

- The frontend's types are generated from that document, and CI fails when the two drift apart.

- Health endpoints: /api/health, /api/health/live, and /api/health/ready, which checks the database connection, the migration state and the core tables.

## 6.3 Hardware

- A label printer driven from the browser's print dialog.

- Optionally a handheld barcode scanner that types into the focused field.

- The phone's camera for QR scanning (LBL-5).

## 6.4 Other systems

None in this version. A read-only feed for the farm website, with its own credentials and its own route namespace, is described in the April integration review and is deferred.

# 7. Non-functional requirements

## 7.1 Security

| **ID** | **Requirement**                                                                                                                                                                                                                                                                         | **Status at baseline**                                                                                                                   |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| SEC-1  | The app shall be reachable only over an encrypted connection and only by signed-in users. Until sign-in exists it shall be reachable only over a private network. <span class="mark">\[Decision: private network (Tailscale, as planned in June) or public address with HTTPS.\]</span> | Met in the repository (WP-2). Every route needs a session; a Caddy proxy serves the frontend and the API on one origin with HTTPS as soon as a hostname is configured; in production a password is not accepted over plain HTTP from the internet. Going live needs owner actions O2 to O4 in the roadmap. The owner chose a public HTTPS address over a private network (brief, decision 7). |
| SEC-2  | The database port shall not be published outside the server. The API shall be reached through a proxy on the same origin as the frontend.                                                                                                                                               | Met (WP-1, WP-2). The database, the API and the frontend are published on the loopback interface only; the proxy is the one way in. CI asserts both. |
| SEC-3  | No secret shall be committed to the repository.                                                                                                                                                                                                                                         | Met as of June 10 (full history scan). The vault repository, which is outside this specification, holds two API keys that need rotating. |
| SEC-4  | No release shall ship with a known critical or high advisory in a direct dependency. Dependency alerts shall be turned on.                                                                                                                                                              | Met in the repository (WP-1). `npm audit` and `pip-audit` are clean and gate every pull request; Dependabot opens weekly update pull requests. Dependabot alerts are a repository setting (owner action O1). |
| SEC-5  | The main branch shall accept changes only through a pull request that has passed CI.                                                                                                                                                                                                    | Not met as of June 10.                                                                                                                   |
| SEC-6  | Administrative access to the server shall not depend on one device. At least two independent ways in shall exist, for example an SSH key held on a second device and the hosting provider's console. No SSH key shall be shared between servers.                                        | Not met. The only key was lost with the laptop and had been used on other droplets.                                                      |
| SEC-7  | Password sign-in over SSH shall be switched off.                                                                                                                                                                                                                                        | Not met as of June 10. A cloud-init file switches it back on.                                                                            |

## 7.2 Reliability and recovery

| **ID** | **Requirement**                                                                                                                                                                                        | **Status at baseline**                                                                                                    |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| REL-1  | All services shall restart by themselves after a server reboot or a crash.                                                                                                                             | Met (WP-1). `restart: unless-stopped` on every service; CI restarts the Docker daemon and checks that the stack returns. The droplet's pending reboot is owner action O5. |
| REL-2  | The database shall be backed up every day to a location outside the containers, kept for 14 days, with one copy a week kept off the server. <span class="mark">\[Decision: confirm retention.\]</span> | Met on the server (WP-1): a dump every 24 hours to `/var/backups/mushroom-app`, 14 kept, plus one before every deploy. The weekly copy off the server needs DigitalOcean droplet backups (owner action O5). |
| REL-3  | A restore from backup shall be tested when the backup is set up and every three months after.                                                                                                          | Met (WP-1). A restore into a scratch database runs on every deploy and in CI. |
| REL-4  | A failed deployment shall leave the previous version running.                                                                                                                                          | Met for a failed build. A build that succeeds and then fails to start is not covered.                                     |
| REL-5  | Database migrations shall run automatically at deployment, and the readiness check shall fail if any is pending.                                                                                       | Met.                                                                                                                      |

## 7.3 Performance

| **ID** | **Requirement**                                                                                                      | **Status at baseline**                                                                         |
|--------|----------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| PRF-1  | With 10,000 bag records, the dashboard, the bag list and a bag page shall each appear within two seconds on a phone. | Not measured. The dashboard reads every bag on each request and will not meet this as written. |
| PRF-2  | Recording an event shall complete within one second.                                                                 | Not measured.                                                                                  |

## 7.4 Usability

| **ID** | **Requirement**                                                                                                 | **Status at baseline**                                       |
|--------|-----------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| USE-1  | The six event screens shall be usable with one hand on a phone, with controls large enough for a gloved finger. | Not met. Desktop layout.                                     |
| USE-2  | After a scan, recording a routine event shall take no more than two taps.                                       | Partly met. Requires typing or a handheld scanner.           |
| USE-3  | A submit control shall not send the same entry twice when tapped twice.                                         | Not met on the event and bag-creation screens.               |
| USE-4  | A new operator shall be able to record a harvest correctly after ten minutes of instruction.                    | Untested. The March tester task lists were written for this. |

## 7.5 Maintainability

| **ID** | **Requirement**                                                                                                                                                                   | **Status at baseline**                                   |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| MNT-1  | CI shall run backend tests, a migration test against PostgreSQL, the API contract check, the frontend type check and build, and the browser workflow tests on every pull request. | Met.                                                     |
| MNT-2  | Every new workflow shall come with a test that exercises it through the API.                                                                                                      | Met to date.                                             |
| MNT-3  | Bag status shall be computed in one place.                                                                                                                                        | Met (WP-1). One function derives status from the stage timeline.         |
| MNT-4  | The requirements, design and operations documents shall be updated in the same pull request as the change they describe.                                                          | Met since WP-1: SRS statuses, decisions and the roadmap change in the pull request that changes the code. |
| MNT-5  | Backend logic is organized in modules by domain, as it has been since the March split.                                                                                            | Met. The largest module is 728 lines.                    |
| MNT-6  | Unused routes, tables and seed data are removed.                                                                                                                                  | Met (WP-1). The redirect pages and the zones table are removed. |
| MNT-7  | The backend shall have a lockfile so that every build installs the same package versions.                                                                                         | Met (WP-1). Hashed lockfiles compiled from `requirements.in`. |

# 8. Phasing

| **Phase**                  | **Requirements**                                                                                                                                             | **Outcome**                                                                             |
|----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| 1\. Safe to hold real data | Section 7.1 and 7.2. BAG-5, RUN-6 (bag code). USR-1 to USR-4.                                                                                                | The server survives a reboot, is backed up, is private, and requires sign-in.           |
| 2\. Fits the farm          | REF-2 to REF-5, REF-11. RUN-3, RUN-5. INO-6, INO-7. LIF-6 to LIF-8. HAR-3 to HAR-6. COR-1 to COR-3. LBL-2 to LBL-5. RPT-4, RPT-5, RPT-9. SPR-2. Section 7.4. | The farm's actual practice can be recorded with few entries, and mistakes can be fixed. |
| 3\. In use                 | No new requirements. One full production cycle is recorded and the reports are checked by hand.                                                              | The numbers can be trusted.                                                             |
| 4\. Looking ahead          | BAG-10. RPT-7, RPT-8. DSH-4. INV-1 to INV-3. PRF-1.                                                                                                          | The app says what will be ready next week.                                              |
| Later                      | Website feed, sensors, other farms.                                                                                                                          | Not specified here.                                                                     |

# 9. Open decisions

Collected from the yellow flags above.

1.  Bag-level tracking throughout, or run-level steps and group harvests with bag-level exceptions (LIF-7, LIF-8, HAR-6).

2.  Whether a spawn source can serve more than one session (INO-7). Settled: a purchased lot can; one of the farm's own spawn bags is consumed by its first session unless a setting allows partial use (brief, decision 3).

3.  The bag code format (BAG-5) and the run code format (RUN-6).

4.  Label printer, stock and size (LBL-3).

5.  The two roles and who holds them (USR-2).

6.  Private network or public address (SEC-1).

7.  Backup retention (REL-2) and record retention (5.3).

8.  Volume assumptions (2.5).

9.  Whether section 4.15, product disposition, is in, deferred or out.

10. Connectivity at each site (2.3).

# Appendix A. March requirements traced to this document

| **March ID**          | **Subject**                                    | **Here**                     | **Status**                       |
|-----------------------|------------------------------------------------|------------------------------|----------------------------------|
| FR-001                | Species                                        | REF-1                        | Built                            |
| FR-002, 003           | Spawn and substrate recipes                    | REF-3, REF-4                 | Partial                          |
| FR-004                | Grain types, ingredients, add-ins              | REF-6, REF-7, REF-9          | Partial                          |
| FR-005, 006           | Sterilization and pasteurization runs          | RUN-1, RUN-2                 | Built                            |
| FR-007, 008           | Each bag traceable to one run                  | BAG-2                        | Built                            |
| FR-009 to 011         | Internal bag records at fill time              | BAG-1                        | Built                            |
| FR-012                | Printable code after inoculation               | BAG-4, LBL-1                 | Built                            |
| FR-013                | Bag notes                                      | BAG-9                        | Not built                        |
| FR-014, 015, 023, 024 | Creation and heat-treatment events             | BAG-1, LIF-4                 | Built                            |
| FR-016 to 018         | Spawn inoculation and lineage                  | INO-1, INO-2                 | Built                            |
| FR-019, 020, 026, 027 | Incubation and ready                           | LIF-1, LIF-2                 | Built                            |
| FR-021, 022           | One spawn bag to many children, of either type | INO-2, INO-3, TRC-2          | Built                            |
| FR-025                | Substrate inoculation from a spawn bag         | INO-3                        | Built                            |
| FR-028                | Fruiting                                       | LIF-3                        | Built                            |
| FR-029, 030           | First and second harvest                       | HAR-1, HAR-3                 | Built; cap to be lifted          |
| FR-031, 032           | Disposal and early disposal                    | DSP-1                        | Built                            |
| FR-033                | Total harvest per bag                          | HAR-7                        | Built                            |
| FR-034                | Biological efficiency                          | RPT-1                        | Built                            |
| FR-035                | Contamination by five groupings                | RPT-2                        | Built, with three more groupings |
| FR-036, 037           | Lineage investigation and run outcomes         | TRC-1 to TRC-3, RUN-4, RPT-3 | Built                            |
| FR-038                | Scan-friendly entry                            | BAG-6, LBL-5                 | Partial                          |
| FR-039                | No duplicate entry                             | INO-1 to INO-3, BAG-3        | Built                            |
| FR-040                | Usable on shared devices                       | Section 7.4                  | Partial                          |
| Section 10            | Harvest by species                             | RPT-4                        | Not built                        |
| NFR-001 to 003        | Reliable, non-conflicting, preserved history   | LIF-4, section 5.2           | Built                            |
| NFR-004               | No developer needed for normal work            | REF-3 to REF-5, COR-1        | Not met                          |
| NFR-005               | Workflow-level tests                           | MNT-1, MNT-2                 | Built                            |
