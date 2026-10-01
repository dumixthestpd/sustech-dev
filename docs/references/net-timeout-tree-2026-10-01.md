---
title: The timeout tree — one budget resolver per service, and the guards that keep it true
service: cross-cutting
captured: 2026-10-01
---

# The timeout tree

**Law:** no module-local timeout default. Every outbound request resolves its
budget through one per-service tree, at the moment of the call.

Why it matters here specifically: measured on a slow campus link,
`raw.githubusercontent.com` took **10.6 s per file** and 21–64 s for a few; TIS
is worse and famously slow on cold start. Upstream defaults of 60 s produced
"timeouts" that were really "the network is slow today", which then read like
signature failures.

## Python lane — `sustech_survival/_net.py`

`service_timeout("bb"|"tis"|"mirror"|…)`, `page_timeout_ms(<service>)`,
`HTTP_DEFAULT`, `LOGIN_DEFAULT` (the batch raised 60 s → 180 s; bb → 240 s).

🔴 The trap is **resolving a budget at import time**: `papers/fetch.py` froze
`DOWNLOAD_TIMEOUT` into a module constant, so configuration and per-call
overrides could never reach it. Resolve per call (`_net.service_timeout(...)`),
including inside `papers/wos_integration.py` and `sso/authlib/rsc_inject.py`
(the RSC cookie-bridge navigation).

The guard is `src/test/test_net_timeouts.py`, written **call-aware**: it scans
backwards from a timeout literal to find the enclosing call and accepts either
a resolver call or an explicit `set_default_timeout(30000)`, because a window
heuristic misclassified multi-line calls and missed positional arguments. Prove
a guard still bites by dropping the offending line into a scratch module and
watching the test fail, then delete the scratch file.

## TypeScript lane — `src/core/net-config.ts`

`requestTimeoutMs(service)` (HTTP), `pageTimeoutMs(service)` (browser
rendering), `loginTimeoutMs(service)` (the CAS dance).

`docs/FORK-NOTES.md` carries the grep gate:

```bash
grep -rn "DEFAULT_TIMEOUT_MS\|DEFAULT_RENDER_TIMEOUT_MS" src/ \
  | grep -vE "src/core/net-config.ts|src/mcp/runner.ts"
# must print nothing
```

`src/mcp/runner.ts` is the one deliberate exception and the gate names it: that
constant bounds a **spawned local process** (`node:child_process`), not a
request, so the tree does not own it. A gate whose exceptions are written down
stays meaningful; one that is quietly widened does not.

## Sites the 2026-10-01 upstream sync found bypassing the tree

All three were fixed then — they are the shape of the bug to look for:

1. `src/online/shared.ts` + `online/manual.ts` used a module constant
   `ONLINE_DEFAULT_TIMEOUT_MS = 15_000` as the fetch default instead of
   `requestTimeoutMs("online")`.
2. `src/sso/cas.ts` hardcoded `DEFAULT_TIMEOUT_MS = 30_000` for the CAS ticket
   dance **and** `casServiceConfig()` never filled `config.timeoutMs` — so the
   tree's `login` layer was unreachable for every CAS login. The config now
   carries `loginTimeoutMs(service)` and the client falls back to the section
   default.
3. The gate itself caught all of this: run it after every upstream merge, not
   once.

## Offline tests must not hit the network

`src/test/calendar/test_calendar.py::TestOnlineLoad::test_load_from_github` was
unmarked, and with the 21–64 s fetch times it stalled the whole suite until it
was marked `@pytest.mark.live`. In the TypeScript repo the same discipline
applies: anything reaching the network is either stubbed or a `live` test.
