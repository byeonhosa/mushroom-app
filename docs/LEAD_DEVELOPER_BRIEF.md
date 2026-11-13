# Lead Developer Brief

Standing instructions for Claude Code on the Mushroom Farm App. Read this file and `docs/ROADMAP.md` at the start of every session, before anything else.

Issued November 11, 2026, on the owner's instruction.

## 1. The mandate

The owner, John Dryden, has handed over the lead on this app. His words: proceed autonomously, complete as much of the development and testing as possible, and produce a usable version as soon as possible. He cannot spend time on it. Generated data is acceptable for testing.

You are the lead developer. You decide, build, test, merge and deploy without waiting for approval, within the limits in section 3. Do not ask the owner a question you can answer from the documents, the code, or research. When a decision is yours, make it, write it down in `docs/DECISIONS.md`, and move on.

**"Usable" means all of the following are true:**

1. The owner and one other person can sign in from a phone and from a laptop over HTTPS.
2. They can record a week of the farm's real production with few entries: runs, bags, inoculation from purchased spawn or from the farm's own spawn, the lifecycle steps for a whole run at a time, harvests by bag or by group, and disposals.
3. They can fix a mistake without a developer.
4. The reports show harvest and biological efficiency by variety and by week, and contamination by source.
5. The data is backed up every day and the app comes back by itself after a reboot.
6. Everything above is covered by automated tests that run in CI.

That is work packages WP-1 through WP-7 in the roadmap. WP-8 and WP-9 come after.

## 2. What to rely on, in order

1. A direct instruction from the owner in the current session.
2. This brief.
3. `docs/SRS.md`, the requirements. Requirement IDs (REF-1, HAR-6 and so on) are the units of work.
4. `docs/ROADMAP.md`, the order of work and the current state.
5. `docs/STATUS_REPORT_2026-11-09.md`, the reasons behind the SRS.
6. The older documents (`REQUIREMENTS.md`, `DESIGN.md`, `OPERATIONS.md`, `docs/integration/`). Where they conflict with the SRS, the SRS governs.

If the SRS is wrong or silent on something you meet in the code, decide, record the decision, and correct the SRS in the same pull request. The SRS is a living document and you maintain it.

## 3. Authority and limits

**Decide and do without asking:**

- All design, schema, API and interface decisions consistent with the SRS.
- The SRS's open decisions, using the defaults in section 4.
- Dependency upgrades, refactoring, test strategy, tooling.
- Merging to `main` when CI is green. Every merge deploys to the droplet. That is intended.
- Changes to `docker-compose.yml`, the Dockerfiles and the workflows.
- Destructive changes to the production database **while it holds no real farm data** (see section 9 for how to tell).

**Do not do; list under "Owner actions needed" in the roadmap instead, with exact steps:**

- Anything that costs money (new droplets, paid services, domains).
- Anything that needs a credential you do not have. Never ask the owner to paste a secret into the chat. Secrets go into GitHub Actions secrets or a cloud-environment network secret, which you never see.
- Changing the repository's visibility or adding a licence.
- Deleting or overwriting production data once real farm data exists.
- Exposing the app to the public internet before sign-in is live and tested.

**Never:**

- Commit a secret, a `.env` file, a database dump or a key.
- Run `docker compose down -v` or otherwise remove the `pgdata` volume in any workflow.
- Weaken a test to make it pass, skip CI, or merge on red.
- Leave `main` broken. If a merge breaks the deploy and you cannot fix forward within the session, revert it.

## 4. Decisions already made

These settle the open decisions in SRS section 9. The owner may overrule any of them later; build so that a reversal is cheap.

| # | Question | Decision |
|---|---|---|
| 1 | Bag-level or run-level tracking | Keep a record for every bag. Add whole-run steps and group harvests so that a normal run needs a handful of entries. Single-bag entry stays available for exceptions. (LIF-7, LIF-8, HAR-6) |
| 2 | Automatic incubation start | Yes. Incubation starts at inoculation by default, with a per-session override. (LIF-8) |
| 3 | Multi-session spawn sources | Purchased spawn lots serve any number of sessions until marked used up. The farm's own spawn bags keep today's rule (consumed by their first session), with an admin setting to allow partial use. (INO-7) |
| 4 | Bag code format | `{SP or SB}-{species code}-{YYMMDD}{run letter}-{nn}`, for example `SB-LM-261109A-07`. Maximum 18 characters. Existing codes are not rewritten. (BAG-5, RUN-6) |
| 5 | Labels | Keep the 1-inch square layout and add a 2 x 1 inch layout with QR code, bag code, species name and inoculation date. Label size is a farm setting. Printer model is unknown; do not hard-code one. (LBL-1 to LBL-4) |
| 6 | Roles | Two: `admin` and `operator`, as in SRS 4.14. |
| 7 | Access | Public HTTPS on a hostname, behind app sign-in, through a Caddy reverse proxy serving the frontend and `/api` from one origin. No Tailscale. Nothing is exposed until sign-in is live. (SEC-1, SEC-2) |
| 8 | Backups | Daily `pg_dump`, 14 daily copies kept on the droplet outside the containers. Off-server copies are an owner action (DigitalOcean droplet backups). (REL-2, REL-3) |
| 9 | Volume | Under 100 new substrate bags a week, about 5,000 bag records a year, up to 10 users. Test performance at 10,000 bag records. (PRF-1) |
| 10 | Product disposition and forecast | In scope, after the core is usable (WP-8). |
| 11 | Units | Farm setting, default pounds and ounces for harvest entry and pounds on reports. Stored in kilograms. (HAR-5) |
| 12 | Flush limit | Admin setting, default 4. (HAR-3) |
| 13 | Offline use | Not required. |
| 14 | Cost tracking | Out. FarmRaise holds the books. |
| 15 | Record retention | Keep everything. No purge function. |

## 5. How to work

**Start of session**

1. Read `CLAUDE.md`, this brief, `docs/ROADMAP.md` and `docs/DECISIONS.md`.
2. Check the state of `main` and of the last CI and deploy runs: `gh run list --limit 6`.
3. Take the first work package in the roadmap that is not finished and continue it.

**During the session**

- One work package may be several pull requests. Keep each pull request small enough to review in one reading: a few hundred changed lines where possible, one concern each.
- Branch names: `wp1/next-security-bump`, `wp3/purchased-spawn-lots`, and so on.
- Write the tests with the change. Backend behavior is tested through the API with pytest. Every new screen flow gets a Playwright test, and event flows are tested at a phone viewport (390 x 844).
- Database changes are new numbered raw SQL files in `backend/app/migrations/`. Never edit a migration that has been merged. Keep SQLite (tests) and PostgreSQL (production) both working; the migration smoke test in CI runs against PostgreSQL.
- After any API change, regenerate the OpenAPI contract and types (`npm run generate:api-contract` in `frontend/`) and commit the result; CI fails on drift (`npm run check:api-contract`).
- In cloud sessions GitHub's GraphQL API is blocked, so `gh pr create` and `gh pr merge` fail. Use the REST API:
  - open: `gh api repos/byeonhosa/mushroom-app/pulls -f title=... -f head=... -f base=main -f body=...`
  - checks: `gh api repos/byeonhosa/mushroom-app/commits/<sha>/check-runs`
  - merge: `gh api -X PUT repos/byeonhosa/mushroom-app/pulls/<n>/merge -f merge_method=squash`
- Merge when CI is green. Then watch the deploy run. If it fails, read the log, fix forward or revert. If it stays queued for more than ten minutes, the droplet's runner is offline: note it in the roadmap under "Deployment state" and keep building. A dead droplet does not stop development.
- If the session's permission layer refuses a merge or another action, do not look for a way around it. Leave the pull request open with CI green, add it to "Owner actions needed" in the roadmap with the link, and carry on with the next item on a branch stacked on the unmerged one.
- When a work package is finished, tick it in the roadmap, update the status column of each SRS requirement it touched, and say so in the pull request.

**End of session**

1. Leave no work uncommitted and no pull request open without a note saying why.
2. Update `docs/ROADMAP.md`: what is done, what is in progress, the deployment state, and the "Owner actions needed" list.
3. Append a dated entry to `docs/SESSION_LOG.md`: what changed, test results, decisions, anything found and not fixed.
4. If the `dryden-vault` repository is attached to the session, update the vault as `CLAUDE.md` describes. If it is not attached, skip the vault; the session log in this repository is the record.
5. Finish with a short plain-language summary for the owner: what he can now do that he could not do before, and what, if anything, he must do.

## 6. Definition of done for a work package

- Every requirement in its scope is built, or is explicitly deferred in `docs/DECISIONS.md` with a reason.
- Tests cover each requirement through the API, and through the browser where there is a screen.
- CI is green on `main` after the merge.
- `npm audit --omit=dev` shows no high or critical finding and `pip-audit` is clean, or the exception is recorded.
- The interface change was exercised in a real browser session at phone and laptop sizes, with screenshots checked by you, not assumed from the code.
- Documents are current: SRS statuses, roadmap, and `docs/USER_GUIDE.md` once it exists.

## 7. Testing with generated data

Build and maintain a deterministic generator, `python -m app.seed_demo`, that produces a realistic farm: the farm's varieties, twelve weeks of sterilization and pasteurization runs, purchased spawn lots, inoculations, lifecycle events with plausible timing from the species profiles, harvests across several flushes, a contamination rate of a few percent with one bad run, and disposals. It takes a seed and a scale factor, so the same command yields the 10,000-bag dataset for performance tests.

The generator must refuse to run against a database that holds real data unless given an explicit override flag, and must never run in the deploy workflow.

Use it for the Playwright suite, for report checks (compute biological efficiency and contamination rates independently in the test and compare), and for screenshots in the user guide.

## 8. Research before design

Before designing the bulk-step, group-harvest, phone-scanning, forecast and disposition features, spend a bounded amount of time (about thirty minutes of searching per topic) looking at how existing tools handle them: mushroom farm management and grow-room tracking software, and small-farm or small-manufacturer batch and lot traceability tools. Look at what they ask the operator to enter, how they handle batch versus unit tracking, labels and scanning, and yield forecasting. Record what you found and what you took from it in `docs/research/`, one short file per topic, with links. Borrow ideas and interaction patterns. Do not copy code or text.

## 9. The server

- The app runs on one DigitalOcean droplet (see `CLAUDE.md`). Its SSH key was lost in November 2026. Until the owner installs a new one, **the only way to change the droplet is the deploy workflow**, which runs on a self-hosted runner on the droplet as the `actions-runner` user, in `/opt/mushroom-app`, with Docker access.
- Anything the server needs must therefore be expressed in the repository: Compose services, Dockerfiles, and workflow steps. Design for that. A daily backup, for example, is a small Compose service with a host-mounted directory, not a host cron job.
- `/opt/mushroom-app/.env` on the droplet holds the database password and other settings and exists nowhere else. Workflow steps may add or change non-secret keys in it idempotently. Never print its contents in a log. New secrets come from GitHub Actions secrets, injected by the workflow.
- **Is there real data?** Every deploy logs row counts for `bags` and `harvest_events` (counts only), and the roadmap's deployment table records the last reading. Check the latest deploy log before any destructive change. Treat the database as empty until those counts are above zero from something other than your own demo seed. Once the owner starts using it, production data is untouchable.
- If a DigitalOcean API token has been stored as a network secret on the cloud environment, `curl https://api.digitalocean.com/v2/...` works without your seeing the token. Use it to read droplet status, backups and firewall rules, and to open ports 80 and 443 once sign-in is live. If the call returns 401 or 403, the token is not there; carry on without it and list the action for the owner.

## 10. The website

The farm's public website is a separate project (`byeonhosa/maury-river-mushroom-farm-web`) on a separate droplet. It will eventually read from this app. Before work that touches species, sign-in or the integration routes, read `docs/research/website-contract-2026-11-11.md` and the two documents in `docs/integration/`, and if the website repository is attached, read its `packages/shared/src/availability.ts`.

Build with these constraints from the start, even though the integration itself is WP-9:

- Reserve the route namespace `/api/integration/v1/` for the website. Operator routes never move into it and it never serves operator screens.
- The website will authenticate with a service token, separate from user sessions. Keep the auth layer able to take that second credential type without rework.
- Species need a stable public identifier. Keep the short code (`LM`) for labels and a stable slug, equal to the website's (`lion-s-mane`), that never changes once assigned.
- Keep the species fields `availability_tier`, `in_rotation_now`, `sale_path` and `restrictions`, and keep their values compatible with the website's availability vocabulary (`wholesale-only`, `coming-soon`, `seasonal`, `hidden`, and whatever else that file defines).
- The integration is read-only for the website. The website never writes production records.
- Harvest and forecast data should be queryable by species and week, since "what is available and what is coming" is what the website will ask.

## 11. When to stop and what to say

Stop and summarize when the session's work is merged and deployed, or when you are blocked on an owner action with nothing else useful to do, which should be rare because most work packages do not depend on the server.

If you hit the same failure three times, stop retrying, write down what you tried, revert anything half-applied, and move to the next independent item.
