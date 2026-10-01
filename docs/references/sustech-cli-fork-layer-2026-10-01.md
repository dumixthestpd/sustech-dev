---
title: The sustech-cli fork — what is fork-local, how to sync, how to version it
service: cross-cutting
captured: 2026-10-01
---

# The sustech-cli fork layer

`dumixthestpd/sustech-cli` is a fork of `wormforce/sustech-cli`. Two repos, one
installable command name (`sustech`), so `sustech version` and the presence of
`:*##:`-style dashboard output are the practical ways to tell which lane an
agent is driving.

## What is fork-local

| Layer | Files | Note |
|---|---|---|
| `mirror` family | `src/mirror/{client,index,text,types}.ts`, cli group | originated in the Python module |
| `cle` family | `src/services/cle.ts`, `cle-wire.ts`, cli group | e-hall language tutoring |
| timeout routing | `src/core/net-config.ts`, ws/detail fixes | see `net-timeout-tree-2026-10-01.md` |
| build/packaging | `tsconfig.build.json`, `files: dist/mirror` | tests excluded; the packed build was missing `dist/mirror` |

## 🔴 Sync = merge the upstream **tag**, then re-apply the layer

The procedure lives in the fork's own `docs/FORK-NOTES.md`; the important part
is the direction of the surprise. Upstream **removes** things a fork keeps:
`mirror` and `cle` do not exist upstream at all, so a merge is not "add what we
lack" — it is "check what the merge dropped and put it back".

Merging `v0.12.1` on 2026-10-01 produced one conflict (`CHANGELOG.md`) and no
losses, because upstream had never touched the fork-local files. Worth knowing:
upstream had **generalised our timeout routing** into
`src/core/http.ts` (`requestTimeoutMs(options.service)`), i.e. upstream's
version was better than the fork's hardcoded 60 s — so adopt theirs instead of
forcing ours back in. Re-run the grep gate after every merge.

## Discoverability is a contract, not a nicety

A command that exists but is invisible is not shipped. Every command needs all
four:

1. an entry in the `--help` block (`src/cli.ts`),
2. a `capability(...)` row in `src/core/capabilities.ts` (`read` / `local` /
   `mutation`, plus auth and confirmation),
3. the option list in `src/core/command-metadata.ts` (and the option itself in
   the parser table + the `Values` type),
4. a consequence entry for every `mutation` (`src/core/consequences.ts`) with a
   **read-back verification rule** — the registry refuses a mutation without
   one, which is exactly how the mirror downloads were caught.

That is the difference the 2026-10-01 pass made: `describe "mirror syllabus get"`
answered "Unknown command to describe" and `capabilities` had zero mirror rows,
while `--help` never listed the family.

## Versioning

The fork reports **`0.12.1-dumix.1`**: upstream's release it aligns to, plus a
fork marker. Publishing plain `0.12.1` under the same npm name is rejected
because upstream owns that number, so the marker is not decoration — it is the
only publishable form. `src/core/version.ts` (printed, and sent as USER_AGENT)
and `package.json` (published) must agree; a test pins them equal so a release
cannot bump one and ship the other.

## CI reality (checked 2026-10-01)

- The fork's workflows **had never run**: `total_count: 0` across all workflows
  and branches, and two pushes to `main` produced nothing. The API reports
  `enabled: true` and `state: active` while GitHub's fork gate still blocks
  scheduling — a fork needs the owner to enable workflows once from the Actions
  UI. Enabling does not retroactively run past pushes; it needs a fresh event.
- The Python repo's CI runs on **`main` pushes and PRs to `main`** only: a
  branch push runs nothing. To get a Test Suite + Docs run for branch work, open
  a PR.
- Local evidence that ships with the repo: `npm run check` (tsc --noEmit),
  `npm test` (build + `node:test` suite), the timeout grep gate above, and the
  Python side `python -m pytest src/test -q -m "not live"`.
