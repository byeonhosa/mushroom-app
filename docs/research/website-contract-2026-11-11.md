# What the website expects of this app

Read before designing sign-in (WP-2), as the brief requires. Sources: `docs/integration/public-website-integration-review.md` and `docs/integration/claude-code-production-app-fix-list.md` (April 2026), and the website repository `byeonhosa/maury-river-mushroom-farm-web` at commit `a0ff749`, files `packages/shared/src/types.ts`, `availability.ts`, `species-tiers.ts`, `species.ts`. Nothing in that repository was changed.

## What constrains sign-in

- Neither integration document says how users sign in. No session, cookie, hashing or role design is prescribed; they ask only that operator and admin sign-in be planned separately and that CORS not be treated as protection. The SRS design therefore stands.
- The website will use a **service credential** ("API token or HMAC", read-only scope), not a user account. Two rules matter now: a read-only integration credential must never be able to call an operator write route, and token values must never be logged.
- Taken into WP-2: requests are authenticated through one list of authenticators (`backend/app/auth.py`); operator routes depend on `require_user`, which only a user session satisfies. A service token will be a second entry in that list with its own `require_service` dependency, so it cannot satisfy an operator route by construction.
- The documents name the namespace `/api/integration/*`; the brief fixes it as `/api/integration/v1/`. Nothing is served there yet, and a test fails if an operator route ever appears under it.

## Species identity: use the website's own codes and slugs

The website already has eighteen species, each with a code and a slug. WP-3 should load exactly these, so that no mapping table is needed for species.

| Code | Slug | Code | Slug |
|---|---|---|---|
| BO | `blue-oyster` | MTK | `maitake` |
| LM | `lion-s-mane` | BCH | `beech` |
| STK | `shiitake` | NMK | `nameko` |
| CNT | `chestnut` | GEN | `golden-enoki` |
| PO | `pink-oyster` | WEN | `white-enoki` |
| WO | `white-oyster` | CDY | `cordyceps` |
| KT | `king-trumpet` | GO | `golden-oyster` |
| BKO | `black-king-oyster` | RSH | `reishi` |
| PP | `pioppino` | TT | `turkey-tail` |

- Every code is two or three characters, which is the limit set for bag codes (decision D-012).
- The Lion's Mane slug is **`lion-s-mane`**, with the apostrophe turned into a hyphen. The brief's example, `lions-mane`, is not what the website uses.
- The website calls king oyster "King Trumpet" (`KT`) and has no separate king oyster entry.

## Availability vocabulary

- **Tier** (`AvailabilityTier`, for grouping and badges): `year-round`, `in-rotation-now`, `returning`, `wholesale-only`, `functional-coming-later`.
- **State** (`availabilityStates`, what a shopper can do): `available`, `low-stock`, `sold-out`, `coming-soon`, `seasonal`, `preorder`, `hidden`, `wholesale-only`, `inquiry-only`.
- **Visibility**: `shop`, `catalog`, `hidden`.
- The brief's field names `in_rotation_now`, `sale_path` and `restrictions` do not exist in the website's code. The nearest things there are the tier value `in-rotation-now`, the `wholesaleOnly` and `inquiryOnly` flags, and `requiresLegalReview` (set on Lion's Mane, Maitake, Cordyceps, Reishi and Turkey Tail). WP-3 should store tier and state in the website's exact strings and decide the other three fields then.

## Never to be exposed to the website

Supplier costs, contamination details, private notes, margins, customer or restaurant names, and any operator write route.
