# Roadmap

The order of work for the Mushroom Farm App and its current state. Maintained by the lead developer (see `docs/LEAD_DEVELOPER_BRIEF.md`). Requirement IDs refer to `docs/SRS.md`.

Last updated: November 11, 2026, end of the first lead-developer session.

## Owner actions needed

The app is built, deployed and running on the droplet, and nobody can reach it or sign in yet. **O2, O3 and O4, in that order, are what stand between you and signing in from your phone.** None of them blocks further development.

| # | Action | Unblocks | How |
|---|---|---|---|
| O2 | Set the first administrator's sign-in | Anyone signing in at all | GitHub > the `mushroom-app` repository > **Settings > Secrets and variables > Actions > Secrets > New repository secret**. Create `BOOTSTRAP_ADMIN_EMAIL` (your email address) and `BOOTSTRAP_ADMIN_PASSWORD` (at least 10 characters; the app makes you replace it at first sign-in). Then **Actions > Deploy to droplet > Run workflow** (branch `main`). The log line `bootstrap-admin: first administrator created` confirms it. |
| O3 | Point a hostname at the droplet | HTTPS (SEC-1) | At the DNS host for `themauryrivermushroomfarm.com`, add an **A record**: name `app`, value `138.197.88.81`. Then in GitHub **Settings > Secrets and variables > Actions > Variables > New repository variable**: `APP_HOSTNAME` = `app.themauryrivermushroomfarm.com`. |
| O4 | Open the web ports | Reaching the app from outside | DigitalOcean console > **Networking > Firewalls** > the firewall on the mushroom-app droplet: add inbound rules **HTTP (80)** and **HTTPS (443)** from all IPv4 and IPv6. Leave 3000, 8000 and 5432 closed. Then **Actions > Deploy to droplet > Run workflow** once more. The proxy obtains its certificate within a minute or two of the ports opening, and the deploy log says `HTTPS for app.themauryrivermushroomfarm.com: certificate valid`. Open `https://app.themauryrivermushroomfarm.com` and sign in. |
| O1 | Turn on the GitHub safeguards | SEC-4, SEC-5 | In the repository: **Settings > Rules > Rulesets > New branch ruleset** for `main`: require a pull request, and require status checks (`backend-tests`, `migration-smoke`, `api-contract`, `dependency-audit`, `frontend-build`, `compose-stack`, `e2e-tests`). **Settings > Advanced Security**: enable Dependabot alerts, Dependabot security updates, secret scanning and push protection. **Settings > General > Pull Requests**: tick "Automatically delete head branches". |
| O5 | Regain the droplet | SEC-6, SEC-7, the pending reboot, off-server backups | DigitalOcean console > the droplet > **Access > Launch Droplet Console**. Add a new SSH public key to `/root/.ssh/authorized_keys` and remove the old one. In the **Backups** tab enable weekly droplet backups (this is the only copy of the database off the server). Take a snapshot, then reboot the droplet once: it has not restarted in seven months, and the stack now comes back by itself. |
| O6 | Optional: give Claude Code read access to DigitalOcean | Lets the lead developer do O4 and check droplet health itself | Create a DigitalOcean API token (API > Tokens), then in claude.ai/code open the environment's settings > **Network secrets** > **Add secret**: allowed website `api.digitalocean.com`, header `Authorization`, prefix `Bearer`, value the token. |
| O7 | Label printer and stock, when chosen | LBL-3 | Tell the lead developer the model and label size. |

## Deployment state

| Item | State | As of |
|---|---|---|
| `main` | WP-1 complete and WP-2 merged (pull requests #22, #28 to #32). | Nov 11, 2026 |
| Droplet and runner | Online. Every deploy on November 11 succeeded. Uptime seven months; a reboot is still pending (O5). 48 GB disk, 37% used after the first prune freed 18 GB of build cache. SSH key still lost. | Nov 11, 2026 |
| Containers | `db`, `api`, `frontend`, `backup`, `proxy`: all `restart=unless-stopped`, logs rotated. Only the proxy publishes ports (80, 443); the rest are on the loopback interface. | Nov 11, 2026 |
| Backups | Daily dump to `/var/backups/mushroom-app`, 14 kept, plus one before each deploy. Restore test passes on every deploy. No copy off the server yet (O5). | Nov 11, 2026 |
| Production database | Migrated to 025. No bags, no harvests, no users. Free to migrate and reseed. | Nov 11, 2026 |
| Reachable by users | No. Needs O2 (an administrator), O3 (hostname) and O4 (ports). The cloud firewall's current rules cannot be read from the workflow. | Nov 11, 2026 |
| Branch protection, Dependabot alerts, secret scanning | Not turned on (O1). Dependabot version updates run from `.github/dependabot.yml`. | Nov 11, 2026 |
| Open Dependabot pull requests | #24 (Actions), #26 (frontend packages), #27 (SQLAlchemy 2.1): to be merged by the lead developer when their CI is green. #23 (PostgreSQL 18) and #25 (Python 3.15, Node 26) must not be merged; the ignore rules added in WP-2 make Dependabot close them (decision D-025). | Nov 11, 2026 |

Update this table after every deploy.

## Work packages

Work them in order. WP-1 to WP-7 make the app usable. Each may be several pull requests.

### WP-0. Documents in the repository (done)

- [x] `docs/SRS.md`, `docs/STATUS_REPORT_2026-11-09.md`, this roadmap, the lead developer brief, refreshed `CLAUDE.md`.

### WP-1. Safe and current (done November 11, 2026)

Security fixes, server hardening that can be expressed in the repository, and the small defects that would otherwise be baked into real data.

- [x] Upgrade `next` past the advisory range (above 16.4.0) and clear the other `npm audit` findings. (SEC-4)
- [x] Raise the `fastapi` pin to a release that brings a patched `starlette` (1.3.1 or later, or whatever `pip-audit` accepts), fix what breaks, and add a backend lockfile used by the Docker build and CI. (SEC-4, MNT-7)
- [x] Add `.github/dependabot.yml` for npm, pip, Docker and Actions.
- [x] Upgrade Playwright to a release that supports the current `ubuntu-latest` image. CI is pinned to `ubuntu-24.04` since WP-0 because Playwright 1.58 cannot install Chromium on Ubuntu 26.04.
- [x] `docker-compose.yml`: `restart: unless-stopped` on every service; publish Postgres on `127.0.0.1` only; log rotation options on every service. (REL-1, SEC-2)
- [x] Backups that work: a `backup` Compose service that runs `pg_dump -Fc` daily into a host-mounted directory outside the repository checkout, keeps 14 copies, and exits non-zero on failure. A restore test in CI against a throwaway PostgreSQL. A workflow step that reports the age of the newest dump after each deploy. (REL-2, REL-3)
- [x] Deploy workflow: prune unused images and build cache after a successful deploy; log row counts for `bags` and `harvest_events`; never touch the `pgdata` volume. (Brief section 9)
- [x] Bag codes: new format and run-code suggestion; fix the repeated prefix. Existing codes stay as they are. (BAG-5, RUN-6)
- [x] Input and error fixes: planned bag count must be positive (RUN-3); unknown sort field returns 400 (RUN-8); duplicate-key handling that does not depend on the database driver (RUN-7); the ready count on the pasteurization summary excludes bags that never reached ready (RUN-4); every API time carries its UTC offset (SRS 5.2); bag ID assignment safe under concurrency (BAG-11).
- [x] One status derivation path. (MNT-3)
- [x] Remove the nine legacy redirect routes and decide the fate of the `zones` table (keep it for BAG-10 or drop it). (MNT-6)
- [x] Frontend image: `output: "standalone"` to cut build size and memory on the 2 GB droplet.

Done: pull requests #22, #28, #29 and #30. CI green, `pip-audit` and `npm audit` clean, every deploy green on the droplet.

### WP-2. Sign-in and a way in (built November 11, 2026; going live needs O2 to O4)

- [x] Users, roles (`admin`, `operator`), password hashing, server-side sessions in an HttpOnly, Secure, SameSite cookie, origin checking on state-changing requests, login rate limiting, sign-out, change password. (USR-1 to USR-3)
- [x] First admin created at startup from `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` when no user exists. The deploy workflow passes these from GitHub Actions secrets. If they are absent, the app starts, serves only the health checks and a notice, and admits no one.
- [x] Every route requires a session except the health checks. Admin-only routes enforced on the server, not only hidden in the interface. (USR-1, USR-2)
- [x] User management screen for admins. Each event records who entered it. (USR-4)
- [x] The auth layer has a seam for a second credential type (service tokens) for WP-9. No integration routes yet.
- [x] Caddy reverse proxy as a Compose service: `/api/*` to the API, everything else to the frontend, one origin. Hostname from `APP_HOSTNAME`; automatic HTTPS when it is set, plain HTTP on port 80 when it is not. Frontend built with a relative API base (`/api`). The API and frontend ports published on `127.0.0.1` only. CORS reduced to the one origin. Security headers. The deploy workflow rewrites the non-secret keys in the droplet's `.env` to match. (SEC-1, SEC-2)
- [x] Deploy smoke tests updated: health checks without a session, one authenticated request with the bootstrap admin.
- [x] Browser tests for sign-in, sign-out, role enforcement, and an expired session.

Done: pull requests #31 and #32. Nothing but the health checks and the sign-in routes answers without a session, and CI signs in through the proxy over HTTP and over HTTPS in production mode. Going live needs owner actions O2, O3 and O4.

Left for later, recorded so that it is not lost: an audit trail of administrator actions on users (who changed a role or reset a password); a sessions list with "sign out everywhere" on the account page.

### WP-3. Fit the model to the farm: sources and reference data (in progress)

- [x] One species list with the cultivation profile attached; stable slug per species; the four portal fields. Migrate the eight existing profiles onto it. (REF-1, REF-2, brief section 10)
- [x] Load the farm's eighteen varieties, with the website's codes and slugs. Eleven profiles come from the farm's sources and seven from research, marked as such (`docs/research/species-profiles-2026-11-11.md`). (SPR-2)
- [ ] Screens to add and edit spawn recipes, substrate recipes, fill profiles, grain types, ingredients, mix lots and liquid cultures; all reachable from the menu; deactivate in place of delete. (REF-3 to REF-8, REF-10, REF-14)
- [x] Purchased spawn lots, and inoculation of substrate or spawn bags from a lot. Multi-session use until marked used up. (REF-11, INO-6, INO-7) The setting that lets the farm's own spawn bags serve several sessions moves to WP-4 (D-037).
- [ ] Liquid culture parent link. (REF-12)
- [ ] Edit a run after creation. (RUN-5)
- [x] First version of the demo data generator: `python -m app.seed_demo` (`docs/OPERATIONS.md` 3a). The reports are checked against its own books. Still to do with it: use it in the browser tests (WP-6, when the reports are reworked) and for the user guide's screenshots (WP-7); a third flush when the flush limit becomes a setting (WP-4). (Brief section 7)

### WP-4. Fit the model to the farm: events, harvest, corrections

Research first (brief section 8): bulk steps and group harvest.

- [ ] Date, time and note on every event, with ordering checks. (LIF-6)
- [ ] Incubation starts at inoculation by default. (LIF-8)
- [ ] Record a step for all eligible bags in a run, or for a scanned list. (LIF-7)
- [ ] Farm settings table. First settings: the flush limit, the weight unit, and whether one of the farm's own spawn bags may serve more than one session. (INO-7, D-037)
- [ ] Flush limit as a setting; one harvesting status with a flush count; next flush proposed; confirmation on implausible weight. (HAR-3, HAR-4)
- [ ] Weight entry in the farm's unit. (HAR-5)
- [ ] Group harvest with allocation by dry weight, marked as allocated. (HAR-6)
- [ ] Further disposal reasons and optional contamination type. (DSP-3)
- [ ] Bag notes. (BAG-9)
- [ ] Admin corrections: amend or void an event, void a bag record, with the original kept and status and reports recalculated. (COR-1 to COR-3)

### WP-5. Usable on a phone

Research first: scanning and label practice.

- [ ] Menu grouped by task and collapsed on small screens. (SRS 6.1)
- [ ] The six event screens rebuilt phone-first: large targets, one hand, focus returns to the scan field after each entry. (USE-1, USE-2)
- [ ] Camera QR scanning in the browser on every bag-code field. Needs HTTPS. (LBL-5)
- [ ] Plain-language errors; no double submission. (SRS 6.1, USE-3)
- [ ] Label reprint from the bag page; the 2 x 1 inch layout with species and date; label size setting. (LBL-2 to LBL-4)
- [ ] Bag list filters for species and run. (BAG-7)

### WP-6. Reports that answer weekly questions

- [ ] Harvest and biological efficiency by species, by recipe and by fill profile. (RPT-4)
- [ ] Date range on every report; weekly harvest by species. (RPT-5)
- [ ] Days in each stage by species. (RPT-7)
- [ ] Biological efficiency sanity rule in the data-quality list. (RPT-10)
- [ ] CSV download on every report table. (RPT-9)
- [ ] Trace page for a liquid culture or purchased lot. (TRC-4)
- [ ] Dashboard and reports computed in SQL with paging; stage-overdue flags. Performance test at 10,000 bags. (PRF-1, PRF-2, DSH-4)

### WP-7. Prove it and hand it over

- [ ] Demo generator complete; full browser regression suite driven by it, at phone and laptop sizes.
- [ ] Independent checks of report arithmetic against the generated data.
- [ ] `docs/USER_GUIDE.md`: a short illustrated guide to a week of work, written for a farm hand.
- [ ] `docs/OPERATIONS.md` rewritten for the server as it now is: deploy, backup, restore, reboot, adding a user, recovering access.
- [ ] Old documents retired or marked superseded (`REQUIREMENTS.md`, `IMPLEMENTATION_BACKLOG.md`, `BACKLOG.md`).
- [ ] Tag `v1.0.0`.

### WP-8. Looking ahead

Research first: yield forecasting in comparable tools.

- [ ] Bag location and moves. (BAG-10)
- [ ] Forecast of harvest by species and week. (RPT-8)
- [ ] Product disposition by channel and weekly commitments. (INV-1 to INV-3)

### WP-9. Website integration

- [ ] Service tokens and the `/api/integration/v1/` namespace, read-only, following `docs/integration/` and the website repository's contract: species and availability, harvest and forecast by species and week.
- [ ] Contract tests shared with the website repository.

## Parked

Sensors and environment logs; multiple farms; other crops; cost tracking. See SRS 2.6.
