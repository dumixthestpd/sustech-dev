---
name: sustech-dev
description: SUSTech endpoint catalog + website behavior notes. Reverse-engineered TIS / BB / Lib / PMS / NCES endpoints and the gotchas around them. Load this before wrapping any new sustech.edu.cn endpoint, debugging write-flow 操作失败, or reviewing HAR vs derived code.
---

# sustech-dev

SUSTech endpoint catalog + behavior notes for agents wrapping
`sustech.edu.cn` services. Per-subsystem detail lives in `references/`;
this file is the cross-cutting index.

## When to load

- Wrapping a new `sustech.edu.cn` endpoint (auth shape, headers, cookies)
- Debugging a write-flow `操作失败` (HAR vs derived bytes, missing keys)
- Auditing cross-cutting gotchas (cookie rotation, XHR header, term/xn confusion)
- Reviewing design principles (module/UI split, API naming, docs philosophy)

## URL conventions

- Base: `https://<sub>.sustech.edu.cn` (sub = `tis` / `bb` / `lib` / `pms` / `ws` / `nces`)
- API style: REST-shaped POSTs returning JSON or HTML blobs; most want
  `X-Requested-With: XMLHttpRequest` so they return JSON instead of the SPA HTML
- All endpoints live behind CAS SSO → `TGC` + `JSESSIONID` + `route`
  cookies. Re-login via `sustech_survival.sso.Authorizer.ensure()` —
  never hand-roll the CAS dance.

## Cross-cutting gotchas

- **Cookie rotation**: BB rotates `JSESSIONID` on every request. Always
  use a fresh `requests.Session` per call.
- **Header required**: most POST endpoints need
  `X-Requested-With: XMLHttpRequest` to return JSON, not SPA HTML.
- **Term confusion**: `p_xn` / `p_xq` = academic term (target).
  `p_dqnf` / `p_dqzc` = current week. Different concepts.
- **xkfsdm must be selected**: TIS selection endpoints behave differently
  depending on which `xkfsdm` tab the user has open. Empty / wrong →
  操作失败.

Detail: [references/cross-cutting-gotchas.md](references/cross-cutting-gotchas.md)

## Authorizer patterns

The `Authorizer` class is the only auth model. Per-service subclasses
override `_is_stale_response()` for service-specific staleness signals;
`get()`/`post()` auto-refresh when stale.

- Stale-detection + auto-retry protocol —
  [references/authorizer-patterns.md](references/authorizer-patterns.md)
- Auth API surface (current state, post-2026-07-13 cleanup) —
  [references/auth-api-surface.md](references/auth-api-surface.md)

## API naming law

Our public API is **not** TIS ping-speak. Audit the data flow before
adding new endpoints; surface upstream state in the primary response;
cache session-stable values.

- [references/api-naming-law.md](references/api-naming-law.md)
- [references/api-surface-design-law.md](references/api-surface-design-law.md)

## Documents philosophy

Module docs = facts only (6-month test). Workflow → skill. Procedure →
skill. Open issues → issues/PRs. Top-of-file docstrings repeat module
doc facts so a reader landing on a file cold has context.

- [references/documents-philosophy.md](references/documents-philosophy.md)
- [references/doc-shape-pointer-vs-content.md](references/doc-shape-pointer-vs-content.md)
- [references/doc-pitfalls.md](references/doc-pitfalls.md)

## Module/UI split

The module owns the domain (field meaning, transformations, business
decisions). The webui owns the surface (HTTP, rendering, layout).
Domain transforms never live in `static/<sub>/<sub>.js` — they belong
in `sustech_survival.<service>` and the blueprint wraps the result.

- [references/architecture-module-vs-ui.md](references/architecture-module-vs-ui.md)
- [references/js-trap.md](references/js-trap.md)

## TIS

### Write endpoints (HAR canonical)

- [TIS write endpoints — HAR byte-by-byte field map](references/tis-write-endpoints-har-2026-08-09.md)
- [Verifying a TIS form fix against the HAR](references/tis-form-fix-har-verify.md)

### Selection + enrollment

- [TIS field rules — `Xsxktz/queryRwxxcxList` (catalog rows)](references/tis-catalog-row-field-rules.md)
- [TIS XSXK personal selection window (2026 fall mechanics)](references/tis-xsxk-personal-selection-2026-07-04.md)
- [TIS enrolled endpoint — slot dedup + field semantics](references/tis-enrolled-slot-dedup-and-field-semantics-2026-08-09.md)
- [TIS enrolled endpoint shape](references/tis-enrolled-endpoint-shape-2026-08-09.md)
- [TIS bid panel — locked-enrolled handling](references/tis-bid-panel-locked-enrolled-2026-08-09.md)
- [TIS kclbdm discovery](references/tis-kclbdm-discovery-2026-07-08.md)
- [TIS course selector solver](references/tis-course-selector-solver-2026-07-05.md)
- [TIS browser-side patterns](references/tis-browser-side-patterns-2026-08-06.md)
- [TIS current-week dead end](references/tis-current-week-dead-end-2026-06-28.md)
- [TIS cold start rate limit (cascade recipe)](references/tis-cold-start-rate-limit-2026-07-06.md)
- [TIS sync overlay + beforeunload](references/tis-sync-overlay-and-beforeunload-2026-08-10.md)

### TIS display (course UI)

- [Display rules for course UI (TIS-specific)](references/tis-course-ui-display-rules.md)
- [Display rules for course identity in schedule grid / picked-list](references/tis-course-identity-display.md)

### TIS classroom / venue (cdjy, cdkb)

- [CDKB live occupancy](references/tis-cdkb-live-occupancy-2026-06-28.md)
- [CDJY form schema](references/tis-cdjy-form-schema-2026-06-29.md)
- [CDJY post-probe](references/tis-cdjy-post-probe-2026-06-29.md)
- [CDJY source code](references/tis-cdjy-source-code-2026-06-29.md)
- [CDJY source code extraction recipe](references/tis-cdjy-source-code-extraction-recipe.md)
- [CDJY venue borrowing](references/tis-cdjy-venue-borrowing-2026-06-28.md)
- [Didian room search](references/tis-didian-room-search-2026-06-28.md)

### SPA reverse-engineering

- [SPA menu discovery](references/tis-spa-menu-discovery-2026-06-28.md)
- [SPA JS bundle walk recipe](references/spa-js-bundle-walk-recipe.md)
- [Discovery methodology — reverse-engineering an internal endpoint](references/discovery-methodology.md)
- [TIS probe flakiness — always retry on empty](references/tis-probe-flakiness.md)

### Discovery / unknown

- [TIS course selector solver](references/tis-course-selector-solver-2026-07-05.md)

## Calendar

- [Calendar module design](references/calendar-module-design.md)
- [Calendar architecture](references/calendar-architecture-2026-07-11.md)
- [Calendar data source (sustech-calendar repo)](references/sustech-calendar-data-source.md)
- [Calendar PDF mapping](references/sustech-calendar-pdf-mapping-2026-07-09.md)

## Library + booking

- [Lib-booking IC (research rooms)](references/lib-booking-ic-2026-06-29.md)
- [Lib-booking policy](references/lib-booking-policy-2026-06-29.md)
- [Lib-booking wire fixes](references/lib-booking-wire-fixes-2026-06-30.md)

## E-hall language tutoring (CLE)

Needs a browser-bootstrapped e-hall session (a bare CAS ticket gets 403).
Booking posts the reservation model's **entire control set** (a subset is
rejected with `#E2140600091`); cancellation is a **status write**, not a delete.

- [CLE reservation wire + the rules it enforces](references/ehall-cle-reservation-2026-10-01.md)

## Open-source mirror (mirrors.sustech.edu.cn)

Public, unauthenticated, CC-BY-SA-4.0: course syllabi, undergraduate training
programs, campus map, handbooks, directory listings. The law worth carrying
everywhere: **a raw UTF-8 path is a 404** (nginx), `requests`/`fetch` encode
silently, so an unencoded printed link works in a browser and dies in
curl/wget/scripts. Training-program years 2019–2024级 are *directories* of
per-major PDFs — resolve, never guess.

- [CRA mirror — paths, listings, training programs](references/mirror-cra-mirror-family-2026-10-01.md)

## NCES

- [NCES Anubis PoW](references/nces-anubis-pow-2026-07-05.md)
- [NCES scraper](references/nces-scraper-2026-07-05.md)
- [NCESnext Anubis](references/ncesnext-anubis-2026-07-05.md)

## Blackboard

> BB endpoint notes live inline in the local `sustech-dev` skill pack at
> `~/.hermes/skills/sustech-dev/` rather than this public repo. The BB
> API surface is narrower than TIS (file submission, attachment download)
> and is fully covered by `sustech_survival.bb`.

## WebUI / architecture

- [WebUI architecture](references/webui-architecture-2026-07-06.md)
- [Async actions — visible feedback](references/async-actions-visible-feedback-2026-08-09.md)
- [Schedule week display](references/schedule-week-display.md)
- [SUSTech brand assets](references/sustech-brand-assets.md)

## Timeouts and guards

One budget resolver per service (`sustech_survival._net` /
`sustech-cli/src/core/net-config.ts`); no module-local default, and never
resolve a budget at import time. The TS repo carries a grep gate whose single
exception (`src/mcp/runner.ts`, a spawned local process) is written down in
`docs/FORK-NOTES.md`.

- [The timeout tree + the guards that keep it true](references/net-timeout-tree-2026-10-01.md)

## Fork layer, release, CI

Which commits are fork-local (`sustech-cli` keeps `mirror` + `cle`, which
upstream **removed**), how a sync is done (merge the tag, then re-apply the
layer), why the version reads `0.12.1-dumix.1`, and the discoverability contract
(`--help` + `capabilities` + `describe` + command-metadata + consequences).

- [The sustech-cli fork — fork-local layer, sync, versioning, CI](references/sustech-cli-fork-layer-2026-10-01.md)

## Things agents must never do

- Don't wrap a working class in another function. `auth.get(path)` not
  `auth().requests.get(...)`.
- Don't override `get()`/`post()` for stale-session detection —
  override `_is_stale_response()` on the Authorizer subclass.
- Don't call `_refresh()` from outside the Authorizer tree. Use
  `auth.refresh()` (public, returns bool).
- Don't push HTML/CSS concerns into the module. Don't push domain
  logic into the template.
- Don't add a JSON auth-cache file. The Authorizer in-memory session
  + ensure()/refresh() is the only auth model.
- Don't make the webui fire parallel `/api/X/*` calls that hit the
  same upstream server when one call's response already contains what
  the others need. Embed upstream state in the primary response.
- Never `trash` / `rm -rf` / `mv` or `git checkout --` a path without
  `git diff --stat` first AND listing contents to the user. Iron rule;
  triggered 2026-07-26 (trashed real source) + 2026-08-03 (lost 637
  lines via `git checkout -- tis.js`). Daily write-up at
  `~/.openclaw/memory/2026-08-03.md`.

Detail: [references/never-do.md](references/never-do.md)

## Probes

- `scripts/probe_ncesnext.sh` — re-check NCES anti-bot posture (Anubis
  PoW challenge, iframe-embeddable, sitemap reachability)
- `scripts/probe_tis_kclbdm.py` — fetch TIS kclbdm codes directly from
  the authoritative source (`component/queryKclb`), not brute-probing

Run before designing any new NCES / TIS-kclbdm integration.

## Install

```bash
npx skills add dumixthestpd/sustech-dev --skill sustech-dev
```

Then in your agent's filesystem the skill lives at
`~/.claude/skills/sustech-dev/`. Load it before wrapping a new
`sustech.edu.cn` endpoint, or whenever a write-flow returns
`操作失败` after your code prints the right bytes.

## References

- Repo: <https://github.com/dumixthestpd/sustech-dev>
- Docs site: <https://dumixthestpd.github.io/sustech-dev/>
- Companion skills:
  - `sustech_survival` — Python module that implements against this catalog
  - `sustech-skill` — agent knowledge / routing
- Issues / Discussions: open on this repo for questions, corrections, advice