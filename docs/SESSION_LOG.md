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
| 32 | WP-2: Caddy proxy, one origin, HTTPS when a hostname is set, Dependabot ignore rules, this log | Open at the time of writing; see the roadmap's deployment state |

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

WP-3: one species list with the cultivation profile attached, the website's eighteen codes and slugs, purchased spawn lots as an inoculation source, reference-data screens, run editing, and the first version of the demo data generator.
