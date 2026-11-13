# Session log

One dated entry per lead-developer session, newest last. What changed, how it was tested, what was decided, and what was found and left. Decisions are in `docs/DECISIONS.md`; the order of work and the current state are in `docs/ROADMAP.md`.

## 2026-11-11: first lead-developer session (WP-0 merged, WP-1 done, WP-2 built)

### What the owner can do now that he could not before

- Nothing new from a phone yet: three owner actions (O2, O3, O4 in the roadmap) stand between the deployed app and signing in. Once they are done: open `https://app.themauryrivermushroomfarm.com` on a phone or laptop, sign in, add a second person, and record work under each person's name.
- Trust the server: it restarts by itself, backs its database up every day, proves on every deploy that the backup restores, and exposes nothing but the proxy.
- Print a bag label that fits: `SB-LM-261109A-07` in place of `PAST-PAST-20261109-001-MM-LM-0001`.

### Pull requests

| # | What | Result |
|---|---|---|
| 21 | SRS, status report, roadmap, lead developer brief (WP-0, written before this session) | Merged, deployed |
| 22 | WP-1: Next 16.4.6, FastAPI 0.162 with Starlette 1.10, hashed backend lockfile, audit gate in CI, Dependabot, Playwright 1.65 | Merged, deployed |
| 28 | WP-1: restart policy, loopback-only ports, log rotation, backup service with tested restore, standalone frontend image, non-root containers, deploy workflow, `compose-stack` CI job | Merged, deployed |
| 29 | WP-1: bag count validation, duplicate and sort errors, UTC offsets, one status path, legacy routes and `zones` removed | Merged, deployed |
| 30 | WP-1: short bag codes, proposed run codes, concurrency-safe IDs | Merged, deployed |
| 31 | WP-2: sign-in, roles, sessions, user management, attribution, phone menu | Merged, deployed |
| 32 | WP-2: Caddy proxy, one origin, HTTPS when a hostname is set, Dependabot ignore rules, this log | Merged, deployed |

### Requirements closed

SEC-1 and SEC-2 (in the repository), SEC-4, REL-1 to REL-3, MNT-3, MNT-4, MNT-6, MNT-7, RUN-3, RUN-6, RUN-7, RUN-8, RPT-3 (the ready-count defect), BAG-5, BAG-11, USR-1 to USR-4, and the UTC-offset rule of SRS 5.2.

### Tests

| Suite | Start of session | End of session |
|---|---|---|
| Backend (pytest) | 37 passed, 1 skipped | 135 passed, 3 skipped (the skipped ones need PostgreSQL and run in CI) |
| PostgreSQL in CI | migrations apply | migrations apply; eight simultaneous sessions create and inoculate bags without a duplicate or an error |
| Browser (Playwright) | 2 | 10, one of them at 390 × 844 by touch |
| Built stack in CI | none | images built as on the droplet; hardening asserted; backup and strict restore; Docker daemon restart; sign-in through the frontend, through the proxy over HTTP, and in production mode over HTTPS |
| Audits | `npm audit` 6 findings (1 critical), `pip-audit` 12 | both clean, and a CI gate |

Screens were checked in a real browser at 1280 and 390 pixels wide for every pull request that changed one. That check found two faults the tests had not: the dashboard was 108 px wider than a phone, and the 17-link menu covered a third of a phone screen. Both are fixed.

### Found by testing, and fixed

- Two inoculation sessions on one run at the same moment chose the same unlabeled bags (found by the new PostgreSQL concurrency test). The session now locks its run first.
- A refused write left the database session unusable for the next request in the same session object; `get_db` now rolls back.
- The backup script exited silently on an empty backup directory, and ignored the stop signal as process 1.
- GitHub's Ubuntu mirror failed during the Playwright browser install and hung the job for eight minutes; the install now retries and falls back.

### What the droplet told us (deploy logs only; there is still no shell access)

- The self-hosted runner is online and every deploy of the day succeeded.
- Uptime seven months: the reboot pending since June is still pending.
- The database held no bags and no users. It is now migrated to 025.
- The first prune freed 18 GB of build cache; the disk is at 37% of 48 GB.
- Not knowable from the workflow: the cloud firewall's rules and the sshd configuration.

### Found and not fixed

- **Dependabot pull requests #24 (Actions v4 to v7), #26 (three frontend packages) and #27 (SQLAlchemy 2.1)** are open. Merge each when its CI is green after it rebases. #23 (PostgreSQL 18) and #25 (Python 3.15, Node 26) must not be merged; the new ignore rules make Dependabot close them.
- GitHub Actions warns that `actions/checkout@v4`, `setup-node@v4` and `setup-python@v5` run on a deprecated Node version. #24 fixes it.
- The 18-variety species dataset prepared in June is not in the vault either (the vault holds the same 8 as the repository). WP-3 rebuilds it from the website's species list, whose codes and slugs are recorded in `docs/research/website-contract-2026-11-11.md`.
- The brief gives `lions-mane` as an example slug; the website uses `lion-s-mane`. WP-3 must use the website's.
- No audit trail yet of administrator actions on users, and no "sign out everywhere" on the account page.
- The deploy runs on every push to `main` whether or not CI passed on that commit. Branch protection (owner action O1) closes that gap.
- Docker image builds cannot run inside a cloud session (package indexes are unreachable from inside a build), so the `compose-stack` CI job is where the Dockerfiles are proved. The pieces are testable locally without a build: `ops/backup/backup.sh` against a `postgres:16` container, and `ops/ci/check-sign-in.sh` against a locally run API, a standalone frontend build and a Caddy container.

### Next session starts at

Superseded by the entry below: the session went on into WP-3.

## 2026-11-11, continued: WP-3 done (the model fitted to the farm's sources and reference data)

The same session, after the entry above was written.

### What the owner can do now that he could not before

Still gated by owner actions O2, O3 and O4 (nobody can sign in until they are done). Once they are:

- **Set the farm up from the screens.** Recipes, fill profiles, grain types and liquid cultures can be added, changed and switched off. Before, only the one seeded recipe could be used and fill profiles had no screen.
- **Record what the farm really does with spawn.** A delivery of bought spawn is recorded once as a lot (`PL-BO-261111A`) and then chosen as the source every time substrate or spawn bags are inoculated from it, until it is marked used up.
- **See the farm's eighteen varieties**, with the website's own codes and slugs, and say per variety what the website may show.
- **Fix a run entered wrongly** (date, count, settings, notes) from its own page.
- **See the app full.** `python -m app.seed_demo` fills an empty database with twelve weeks of realistic work, so screens and reports can be judged with a thousand bags in them.

### Pull requests

| # | What | Result |
|---|---|---|
| 33 | WP-3: one species list, the website's eighteen codes and slugs, 18 profiles (7 researched) | Merged, deployed |
| 34 | WP-3: purchased spawn lots as an inoculation source | Merged, deployed |
| 35 | WP-3: demo data generator and the app's clock | Merged, deployed |
| 36 | WP-3: recipes, fill profiles, deactivation, a culture's parent | Merged, deployed |
| 37 | WP-3: correct a run after creating it; this entry | Merged, deployed |
| 38 | WP-3: Ingredients and Mix Lots screens finished | See the roadmap's deployment state |

### Requirements closed

REF-1 to REF-8, REF-10 to REF-12, REF-14, INO-6, INO-7 (purchased lots), RUN-5, SPR-1, SPR-2, and the generator of brief section 7. TRC-3 and RPT-2 extended to purchased lots.

### Tests

| Suite | When the entry above was written | Now |
|---|---|---|
| Backend (pytest) | 135 passed, 3 skipped | 220 passed, 5 skipped (the skipped ones need PostgreSQL and run in CI) |
| PostgreSQL in CI | migrations; eight simultaneous sessions on bags | the same, and eight people recording a lot of one species at once, and eight sessions inoculating from one lot |
| Browser (Playwright) | 10 | 23, three of them at 390 pixels wide |
| Generated data | none | the production report equals totals added up from the generator's own books: counts, harvest, dry weight, biological efficiency, contamination by species, by run, and by root culture or lot followed back through the farm's own spawn |

Every screen changed was looked at in a real browser at 1280 and 390 pixels wide. That found three things the tests had not: labels crammed against their fields on the new forms (now above them), unstyled fields when a table row is edited in place, and a heading that read "Add a ingredient".

### Found by testing, and fixed

- Two people recording a lot of the same species at the same moment were given the same lot code, and one got a server error (found by a new PostgreSQL test; the species row is now locked while the code is chosen).
- Migration 015 seeds one mix lot, so the generator's "does this database hold real records?" check refused every new database. Mix lots no longer count; a real one is always followed by a run, which does.

### Measured

- Generating the demo farm: 35 seconds per thousand bags on PostgreSQL; 5 minutes 25 seconds for 10,028 bags.
- With 10,028 bags in PostgreSQL: dashboard 12.8 seconds, production report 6.1 seconds and 7.3 MB, bag list 0.03 seconds. At the farm's own volume, about a second. This is the baseline for WP-6.

### Found and not fixed

- **The report's overall biological efficiency reads low on a working farm.** It divides total harvest by the dry weight of every substrate bag, including those still incubating: 43% on the demo farm, whose finished bags come to 100%. Added to WP-6.
- **Nothing records who corrected a run, or what it said before.** RUN-5 is met; the history belongs with COR-1 to COR-3 in WP-4.
- The recipe, grain and mix lot of a run can be corrected through the API only (and only before the run has bag records); the screen offers the code, times, count, settings and notes.
- On a phone, the Actions column of the set-up tables (recipes, cultures, lots) is reached by scrolling the table sideways. The daily event screens are WP-5's subject; these are used rarely.
- The setting that lets one of the farm's own spawn bags serve several sessions is deferred to WP-4 with the other farm settings (D-037).
- The demo generator is not yet used by the browser tests or for user-guide screenshots, and stops at two flushes because the app does.
- Dependabot pull requests #24 (Actions), #26 (frontend packages) and #27 (SQLAlchemy 2.1) are still open; their checks last ran before WP-3 and must be run again on the current `main` before any is merged. #23 (PostgreSQL 18) and #25 (Python 3.15, Node 26) are closed: the ignore rules of D-025 made Dependabot withdraw them.
- The local Docker daemon used for PostgreSQL tests in the cloud session does not survive a worker restart; start it again before running `tests/test_postgres_concurrency.py` locally. CI runs them regardless.

### Next session starts at

1. Rerun the checks on Dependabot #24, #26 and #27 against the current `main` and merge each when green.
2. WP-4, research first (brief section 8): bulk steps and group harvest. Then the farm settings table (flush limit, weight unit, partial use of the farm's own spawn), date and time on every event, and corrections with history.


## 2026-11-13: prompt audit of the instruction files (documentation only)

Not a lead-developer session. The owner had Claude Code's `/doctor prompt-audit` run across his repositories and approved a set of corrections for each. No code, test, migration or workflow changed here, and the order of work is unchanged: the next session still starts where the entry above says.

### What changed

| File | Change |
|---|---|
| `CLAUDE.md` | The session-start heading now says it applies to development sessions, so a session that only audits or answers a question is not told to continue a work package. The session-end heading is unchanged. |
| `docs/LEAD_DEVELOPER_BRIEF.md` | The example slug is the website's `lion-s-mane` (D-027), not `lions-mane`. "Is there real data?" points at the row counts every deploy logs, in place of a guess dated June; both safety sentences stay. The website section no longer sequences its reading list and the service-token seam around WP-2, which is finished. |
| `docs/ROADMAP.md` | The Playwright item says CI runs on `ubuntu-latest` (D-001), not that it is pinned to `ubuntu-24.04`. |

### Found and left

- The audit raised two things and proposed no edit: "Run these in the session before pushing" in `CLAUDE.md` literally covers the development server and the demo seed, and `CLAUDE.md` says to continue the first unfinished work package while the roadmap puts the Dependabot pull requests first. Neither has caused confusion.
- Merged branches stay on GitHub. The cloud session's proxy refuses branch deletion, and it also refuses the change to the repository setting that would remove them automatically; the owner turns that setting on himself (`CLAUDE.md`, Workflow).

## 2026-11-13: owner adopts the wholesale-plan and website-review recommendations (documentation only)

Not a lead-developer session. Claude, working with the owner in chat, compared the wholesale sales plan (November 10) and the website review (November 13) with this app's plan and recommended eleven changes. The owner adopted all of them. No code, test, migration or workflow changed.

### What changed

| File | Change |
|---|---|
| `docs/SRS.md` | Revision 2. New: REF-15 (culture supplier), LIF-10 (cold storage), DSP-5 (grow kits), LBL-6 and TRC-5 (harvest lots), RPT-11 (next-week view), DSH-5 (age alerts), SPR-4 (spawn storage), SPR-5 (species data ownership), section 4.16 with PLN-1 to PLN-3 (inoculation planner). Changed: BAG-10, HAR-8 (C to S), DSP-3, RPT-4 (pounds per bag), INV-2 (channels), INV-3 (two-thirds warning, C to S), 2.6, 4.15 (in, phase 4), 6.4 (read-only feed; a later write route for weekly totals only), 8 and 9. |
| `docs/ROADMAP.md` | The new work placed in WP-4, WP-5, WP-6, WP-8 and WP-9. O8 rewritten (mark varieties in rotation; sale fields belong to the website). New O9: use harvest lot codes by hand from the first restaurant delivery. O2 to O4 asked for before December. |
| `docs/LEAD_DEVELOPER_BRIEF.md` | Owner decisions 16 to 22 in section 4; decision 10 given its trigger; section 10 says which species fields the website owns. |

### For the next development session

- WP-4 has grown by six items (REF-15, LIF-10, DSH-5 with SPR-4, DSP-3/DSP-5, HAR-8, SPR-5). The cold-hold and spawn-age limits belong in the farm settings table WP-4 already creates.
- Freezing the sale fields (SPR-5) touches the species screen and the species update route; keep the values and the seeder's add-only rule (D-030).
- The website repository's own specification (its INT-3 and its species data) should be brought into line with SRS 6.4 and SPR-5 in the website's review.
