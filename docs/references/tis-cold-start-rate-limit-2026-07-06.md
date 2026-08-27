# TIS cold-start rate-limit cascade — diagnosis & fix

> **Symptom:** `查询请求频率过高` after the first page load of the TIS web UI
> (or after a server restart with an empty `selectcourse/cache/`).
> **Affected reproduction:** 2026-07-06 (commits `6b314e7`, `25870ea`,
> `6d9ddd1`, `69de0aa`).
> **Generalizes to:** any SUSTech subsystem whose web UI launches multiple
> parallel/sequential calls to the upstream server.

## The cascade

### Backend layer (commit `6b314e7`)

Counting all TIS calls fired by `GET /tis` on a cold start with an empty
catalog cache, before any fixes:

| # | Where fired                                   | Endpoint                          | Why duplicate?                         |
|---|-----------------------------------------------|-----------------------------------|----------------------------------------|
| 1 | `api_info` → `_ensure_loaded` → `_fetch_catalog` | `Xsxktz/queryRwxxcxList` × 9 pages | Cold catalog: 9 paginated calls in a tight loop. **No throttle.** |
| 2 | `api_courses` (personal) → `search_personal`  | `Xsxk/queryXkdqXnxq`              | Round-trip for `p_dqxn/p_dqxq/p_dqxnxq/cxsfmt` |
| 3 | (same call)                                   | `Xsxk/queryKxrw`                  | The actual data fetch                  |
| 4 | `api_round` (called from JS on mount)         | `Xsxk/queryXkdqXnxq`              | **DUPLICATE OF #2**                    |
| 5 | (same call)                                   | `Xsxk/queryKxrw`                  | **DUPLICATE OF #3**                    |

Total: **up to 13 TIS calls in <2 seconds**. TIS rate-limits at
~1 request per 3-5s, so the cold start is a guaranteed rate-limit error.

### JS layer (commits `25870ea`, `6d9ddd1`, `69de0aa`)

Three **additional** rate-limit causes live in the web-UI JavaScript, not
in the Python backend. Even after the backend fixes above, these kept
triggering bursts:

1. **Multi-event binding on text inputs.** Text `<input>` fires both
   `input` (every keystroke) and `change` (on blur/Enter) events.
   If `onFilterChange()` is bound to both, every user action fires
   N requests. Fix: bind `input` to a 500ms debounced handler, bind
   `change`/`click`/Enter to an immediate variant that cancels any
   pending debounce.
2. **`Search` button dispatch ambiguity.** `if (ALL_CAT.length)
   client_filter` was correct for catalog mode but wrong for
   personal mode — personal mode populates `ALL_CAT` with a per-xkfsdm
   slice (e.g. the bxxk 50), so the Search button silently did
   client-side filter on those 50 instead of hitting TIS. The user
   said "the search param is the catalog params". Fix: dispatch
   explicitly on `MODE === 'campus'`, always `loadCourses()` in
   personal mode.
3. **Initial-page-load vs toggle-handler asymmetry.** Mode-dependent
   setup that lives only in the toggle handler doesn't fire on cold
   load — but the default mode is the one where it should fire.
   See `tis/SKILL.md` "page-load vs toggle-handler asymmetry" for
   the full trap and the fix pattern.

### Combined cold-start TIS-call budget after all fixes

| Action                         | TIS calls |
|--------------------------------|-----------|
| Fresh page load (Selection)    | 1 (1× `queryKxrw` after dq cache hit; course-types is `queryYxkc` separate + `info` is cached) — **but in practice on warm process: 1** |
| Switch Selection → Catalog     | 1 (`queryRwxxcxList` × 9 paginated, 0.6s apart) |
| Switch Catalog → Selection     | 2 (`queryYxkc` + `queryKxrw`, dq cached) |
| Type "physics" in keyword      | 1 (debounced after 500ms) |
| Click xkfsdm tab dropdown      | 1 (immediate) |
| Click Search button            | 1 (immediate, cancels debounce) |
| Press Enter in keyword         | 1 (immediate, cancels debounce) |

## Why the school site itself doesn't trigger this

The TIS SPA `xsxk-*.js` bundle uses axios for parallel calls, but the
upstream tolerates them only from the school network / trusted clients.
Third-party clients (anything going through `sustech_survival`) get
throttled. The SPA also caches `xsxkPage` state in component data so
the round-trip for `p_dqxn/...` only happens once per session.

## The three backend fixes (applied, commit `6b314e7`)

### 1. Cache `queryXkdqXnxq` in the client (5 min TTL)

The "current TIS active term" is session-stable — it does not change
mid-session. `SelectCourseClient._fetch_dq()` caches the response and
returns it from memory for 5 minutes. Every `search_personal` call
reuses it.

**Generalizes to:** any upstream response that contains "current
session state" (active term, build version, server time) rather than
"live data". Cache these aggressively.

### 2. Throttle `_fetch_catalog` paginated calls (0.6s between pages)

Cold catalog fetch now takes ~11s instead of <2s, but completes without
triggering the limit. Subsequent fetches are instant from the on-disk
cache (`selectcourse/cache/catalog_<xn>_<xq>.json`, 1h TTL).

**Generalizes to:** any paginated upstream fetch where pageSize can
be small. Always throttle, even if the loop only runs ~5 times.

### 3. Embed round info in `api_courses` personal response

`search_personal` already returns `xkgzszOne` (the current round
config including `jfxs`/`ksrq`/`jsrq`/`lcmc`) — TIS includes it in
every `queryKxrw` response. The blueprint now exposes it as `round`
in the JSON. The bid panel reads from there; no second TIS call.

**Generalizes to:** when designing new web-UI endpoints, look at
what the upstream response already contains. If endpoint A and
endpoint B both call upstream and want fields X/Y/Z, surface X/Y/Z
in A's response and have B's UI read from A. Don't make the UI
fire both endpoints.

## Diagnostic recipe (use this for any new subsystem)

When you see `查询请求频率过高` or any rate-limit message:

1. **Count upstream calls fired by one page load.** Use Playwright
   `page.on("request", ...)` filtered to the upstream domain, count
   requests in the first 5 seconds of a cold load. If the count is
   >3, you have a burst problem. (See `browser-test-before-claiming`
   skill for the test template.)
2. **Trace each call back to where it originates.** Is it module
   code doing a redundant fetch? Is it JS firing parallel `fetch()`
   to multiple `/api/X/*` endpoints that hit the same upstream? Is
   it a multi-event handler firing on every keystroke?
3. **For each "session-stable" upstream response, cache it.** The
   default cache location is per-client-instance (in-memory dict
   keyed by `xn_xq` or similar session context) with a 5-min TTL.
4. **For each "live data" call, throttle.** A 0.5-1.0s sleep between
   paginated calls is fine. TIS sees the human site doing this anyway.
5. **Where two endpoints fetch overlapping state, merge them.** Add
   the overlapping fields to the larger endpoint's response, have the
   other endpoint read from the cached/larger response.
6. **For each form input on the page, audit how many handler
   invocations one user action triggers.** Text inputs with both
   `input` and `change` listeners fire N requests per "change" —
   debounce.
7. **Verify** by restarting the dev server with an empty cache and
   timing the cold load. 5-15s for a full load is acceptable. 30s+
   means you're sleeping too much; <3s on cold cache means you're
   back to bursting.

## Where the mitigations live in the code

- `src/sustech_survival/selectcourse/selectcourse.py`:
  - `_fetch_dq()` — 5-min in-memory cache for `queryXkdqXnxq`
  - `_fetch_catalog()` — `time.sleep(0.6)` between pages
- `src/sustech_survival/webui/blueprints/tis.py:228` —
  `round` field in `api_courses` personal response
- `src/sustech_survival/webui/templates/tis.html`:
  - `initialLoad()` — fires course-types + loadInfo on cold load,
    not just on mode toggle
  - `loadCourses(true)` — populates `ROUND_INFO` from `d.round`,
    no separate `loadRound` call on mount
  - `onFilterChange()` (debounced) and `onFilterChangeImmediate()`
    — separate handlers for input vs change/click/Enter
  - Personal-mode Search dispatch: `loadCourses()` always,
    client-side filter only in catalog mode

## Related skill pointers

- `sustech/tis/SKILL.md` — rate-limit section + page-load-vs-toggle
  asymmetry + search-debounce sections
- `sustech-dev/SKILL.md` — design law: "embed upstream state in the
  primary response"
- `browser-test-before-claiming` skill — how to assert network
  requests + DOM state, not just screenshots
