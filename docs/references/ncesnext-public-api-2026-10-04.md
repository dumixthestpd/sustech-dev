---
title: NCESnext public API — Anubis gate removed, plain JSON read endpoints
service: nces
captured: 2026-10-04
---

# NCESnext public API — Anubis removed (re-probe 2026-10-04)

> **Captured 2026-10-04** (issue #1, independently re-verified from this host:
> every number below was reproduced with plain `curl`, no cookies, no JS).
> The site's protection posture has flipped **before** — the 2026-07-05 note
> recorded the gate going up — so re-run
> `scripts/probe_ncesnext.sh` before designing anything that depends on this.

## What changed since [ncesnext-anubis-2026-07-05.md](ncesnext-anubis-2026-07-05.md)

| Probe | 2026-07-05 | 2026-10-04 |
|---|---|---|
| `/`, `/search`, `/course/{id}/` | 4441-4492 B Anubis challenge | 200 · 5084 B SPA shell |
| `/api/v1/*` | Anubis challenge | real JSON, no auth |
| `/.within.website/x/cmd/anubis/api/pass-challenge` | PoW machinery | 200 SPA shell (catch-all) |
| `robots.txt` | `Disallow: /api/*` | no `/api` entry at all |
| `X-Frame-Options` | absent | **`SAMEORIGIN`** |

Two consequences:

1. **"No public read API" is no longer true.** `/api/v1/*` serves plain JSON
   for every user agent tried (curl, empty, Chrome UA, python-requests,
   Googlebot) — no `set-cookie`, no challenge headers, no PoW.
2. **The 2026-07-05 recommendation "iframe embed" is dead.**
   `X-Frame-Options: SAMEORIGIN` now blocks cross-origin embedding — the
   SPA (and any wrapper page we host) cannot iframe ncesnext.com anymore.
   Link-out (`direct_url`) is the only in-app surface left.

## Public read endpoints (no auth, GET only)

```
GET /api/v1/stats                      # {user_count, course_count, review_count,
                                       #  teacher_count, running_days, ...}
GET /api/v1/course?page=N&per_page=M   # paginated LIST — per_page max 100 (200 → 422)
GET /api/v1/course/{id}                # full record (dept, teachers, term_ids, ...)
GET /api/v1/course/{id}/reviews        # community reviews
GET /api/v1/teacher/{id}
GET /api/v1/search?q=…                 # q required (empty → 422);
                                       # {courses, reviews, teachers} each with
                                       # {items, page, pages, per_page, total}
```

Verified shapes (2026-10-04):

- **list row** — `id, name, course_code, teacher_names, term_ids,
  review_count, rate_average, difficulty_score, homework_score,
  grading_score, gain_score` (+ `name_highlighted` on search hits).
  `difficulty/homework/grading/gain` are **strings** (`"80.00"`), not numbers.
- **list pagination** — top level is `{items, page, pages, per_page, total}`;
  `total` is the real course count (5,709 at capture), so
  `pages = ceil(total/per_page)` — no secondary discovery call needed.
- **course detail** adds `courseries, dept, introduction, homepage,
  access_count, teachers[]` — `introduction` is often `null`.

## Enumeration: the list endpoint, not id iteration

Course ids are **not contiguous**: `/api/v1/course/4000` → 404 while live ids
run past 8900. Iterating ids silently under-collects; the paginated list
endpoint is the only reliable enumerator. Full walk = 58 requests at
`per_page=100`, and each list row already carries the score fields — only
rows with `review_count > 0` need a `/course/{id}` or
`/course/{id}/reviews` follow-up.

## Rate limiting — burst-sensitive, not rate-sensitive

Reproduced 2026-10-04: a 12-request back-to-back burst to the list endpoint
returned **12× 200** on our line (the issue's reporter saw 429s from the 4th
request on theirs — vantage-dependent), and ~6 req/s sustained also passed.
Treat 429 as retryable with a small backoff; don't parallel-hammer, and
prefer ≤1 req/s for full-enumeration walks.

## Implications

- **`sustech_survival.nces`**: `NCESAuth._solve_anubis_if_needed()` is now a
  no-op path — the OIDC + cas-proxy + CAS chain walks without solving
  anything. Don't rip it out: the gate flipped on once and can flip back;
  the solver is the insurance. Read-only eval queries can now use
  `/api/v1/*` directly instead of the authenticated HTML scrape.
- **TIS code → nces id mapping** (impossible in 2026-07): now trivial —
  `GET /api/v1/search?q={code}` → `courses.items[].id`.
- **Iframe embed strategy**: retired. Use `direct_url` links only.
- **Reviews content is HTML** (`content` field carries `<div><p>…` markup) —
  strip tags before storing or displaying.

## What this does NOT cover

- Write endpoints (upvote / follow / review submission) — still unprobed,
  and `robots.txt` still disallows their paths. Not our surface.
- Whether the unauthenticated read survives — the site toggled Anubis once
  already. Pin your integration to the probe script, not to this page.
