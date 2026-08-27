## Discovery methodology: when reverse-engineering an internal TIS endpoint or dictionary

User pushed back hard on 2026-07-08 after I brute-force guessed ~30 URL
patterns to find TIS's kclbdm dictionary endpoint. Rule: **find the
presence in the system first; never guess URLs to discover an internal
upstream the docs don't cover.**

Order of attack:
1. **Existing code comments in the codebase**. Often the endpoint name
   is right there. Example: `campus_schedule.py:16` says
   `p_kclb course category code (from queryKclb)` — the kclb dictionary
   endpoint was *named* but `/Xsxk/queryKclb` 404s today (renamed/
   removed). Verify it works before trusting.
2. **Live API probes with known-good inputs**. If code comments give
   `e.g. "08" for 通识必修课`, that's a starting point — test nearby
   codes (`01`–`99`) systematically to derive the rest of the family
   by response shape.
3. **Chrome HTTP cache** at
   `~/Library/Caches/Google/Chrome/Default/Cache/Cache_Data/f_*` —
   the user's own cached requests reveal what they loaded with their
   auth. The `kclbmc` format (`通识选修课-美育类`) was visible only here,
   not in any test data or disk cache.
4. **The webui's own endpoints**. When the webui's auth is fresh
   (`/api/tis/info` returning full data, not the fallback empty arrays),
   `?mode=personal` searches work because they don't need CAS login —
   they reuse the in-memory TISAuth. Cheapest probe target — no browser
   required.
5. **Walk the SPA JS bundle** (static analysis). The page's `<script src=...>`
   tags reveal component bundles. Download them with `Referer` + cookies
   (Tengine blocks bare curl — use Python `requests.Session` with the CAS
   cookies and Referer). Grep for `$.post()` calls and URL strings to find
   endpoint paths.

6. **Live-spectate the page** in a real browser (Playwright or the user's
   Chrome with remote debug). The key distinction from static analysis:
   some Vue components load lazily — their `mounted()` callbacks fire only
   when the component actually renders. You MUST drive the UI to that state
   (open drawer, click tab, select option) to trigger the network call and
   capture it with `page.route()` or a Playwright request handler. The
   `component/queryKclb` endpoint was findable by static analysis (the kclb
   component is always-mounted), but `component/queryDmb` needed reading
   the bundle code. When either is possible, prefer static analysis (step 5)
   since it's faster. When the endpoint is in a lazily-loaded component,
   use live spectate (step 6).

**Critical nuance (user 2026-07-08):** "find the presence in the system"
means steps 5 or 6 — both are valid. The user's complaint was about
`for ep in candidates: sess.post(ep)` brute-force loops, which is neither
static analysis nor live spectate. Steps 5 and 6 are the only acceptable
approaches for discovering undocumented endpoints.

For the TIS kclbdm dictionary specifically — see
`references/tis-kclbdm-discovery-2026-07-08.md` for the resulting mapping,
the `component/queryKclb` endpoint discovery, the parent `fdm`/`level`
hierarchical structure, and the verified codes for all 22 undergrad and
9 grad categories.
