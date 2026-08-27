# Things agents must never do

The HAR file is the **canonical reference** — derived docs (Chinese-comment
guesses, training-data recall) drift over time. The HAR is bytes from a real
session.

For the byte-exact field map (per-endpoint canonical bodies, all the
"if empty → 操作失败" keys, the `p_id`-vs-`rwh` distinction, and the
`upd_xkxsBygwc` 404 phantom), see
`references/tis-write-endpoints-har-2026-08-09.md`.

## Things that break across all SUSTech APIs
- **Cookie rotation**: BB rotates `JSESSIONID` on every request. Always use a fresh `requests.Session` per call (`submit_rest._bb_session()`).
- **Header required**: most POST endpoints need `X-Requested-With: XMLHttpRequest` to return JSON instead of the full SPA HTML.
- **Term confusion**: `p_xn` / `p_xq` is the academic term (target). `p_dqnf` / `p_dqzc` is the current week. Different concepts.
- **xkfsdm must be selected**: TIS's selection endpoint behaves differently depending on which `xkfsdm` tab the user has open. Empty / wrong xkfsdm → 操作失败.

## Things agents must never do
- Don't wrap a working class in another function. `auth.get(path)` not `auth().requests.get(...)`. The Authorizer class already does the job.
- Don't try to add stale-session detection by overriding `get()`/`post()` yourself. Override `_is_stale_response()` on the Authorizer subclass instead — see `references/authorizer-patterns.md` § "The stale-detection + auto-retry pattern" for the full protocol and per-service staleness signals.
- Don't call `_refresh()` from outside the Authorizer tree. It's private. `get()`/`post()` already auto-refresh when `_is_stale_response()` fires; `check()`/`ensure()` call it internally. If you need a forceful re-auth externally, use `refresh()` (returns bool, no exceptions).
- Don't push HTML/CSS concerns into the module. Don't push TIS field rules into the template.
- Don't assume `queryKxrw` returning 操作失败 means the API is broken. It often means selection is closed for the identity / term. Read the response message first.
- Don't add a JSON auth-cache file (e.g. `bb_session.json`). The Authorizer in-memory `_session_cache` + ensure()/refresh() is the only auth model.
- Don't make the web UI fire parallel `/api/X/*` calls that hit the same upstream server when one call's response already contains what the others need. **Embed upstream state in the primary response; don't force N+1.** This triggered `查询请求频率过高` on 2026-07-06 cold load — see `references/tis-cold-start-rate-limit-2026-07-06.md` for the cascade recipe.
- **Never `trash` / `rm -rf` / `mv` a directory tree you did not create in the current session.** Rule triggered 2026-07-26: I `trash`ed `~/.openclaw/workspace/sustech/` thinking it was a stale workspace duplicate of `~/Documents/sustech/26spring/`. It was the real project source. `.Trash` was empty afterward — files unrecoverable without Time Machine. The wrong belief was that "workspace = code-level prototyping only" (a memory note) meant "workspace is throwaway." Actual rule: workspace is not throwaway, it's just not where personal academic docs go. **Before any non-trivial filesystem mutation, run `ls -la` on the target path AND list the contents to the user. This rule overrides any "cleanup" or "save space" framing.** Memory note `~/.openclaw/memory/2026-08-03.md` has the full incident write-up.
- **Never `git checkout -- <file>` / `git restore <file>` on a file with uncommitted changes without first running `git diff --stat` and listing what's about to be discarded.** Rule triggered 2026-08-03: I ran `git checkout -- src/.../tis.js` to "reset to the staged version," not realizing the working tree had ~637 lines of uncommitted user work on top of HEAD. Lost without recovery. `git checkout` and `git restore` are in the same family as `trash`/`rm`/`mv` — they silently discard content. The rule is the same: show `git diff --stat` first, get confirmation when the diff is non-trivial, and prefer `git stash` over `git checkout` when you need to preserve the working tree. The only safe `git checkout --` is one where `git diff` shows zero non-trivial changes for the file.

### Auth API surface (current state — 2026-07-13 cleanup)

The legacy registry is gone. Future agents working on `sustech_survival.sso`:

- **DO NOT import or call `get_auth(name)`** — removed entirely. Each `Authorizer` subclass is already a singleton via `__new__`; import the class directly: `from sustech_survival.sso import TISAuth; auth = TISAuth()`.
- **`register_auth(name, instance)` is a no-op shim.** The authlib modules (`sso/authlib/{ieee,wiley,jstor,acs,rsc,wos,...}`) still call it at import time as a vestige. Don't write new code that depends on it. Don't call it expecting registration to happen.
- **DO NOT use `auth.requests_session`** — removed (was deprecated). Use `auth.session`. The old name emitted a `DeprecationWarning`; the property itself is gone.
- **Credentials resolution is now XDG-aware.** First match wins:
  1. `SUSTECH_CREDENTIALS` env var (full path to credentials file)
  2. `~/.config/sustech-survival/credentials.txt` (XDG user config)
  3. `./credentials.txt` (cwd)
  4. Walk-up from package source (editable / dev installs)
  Format: `sid:password`. In-memory only — no on-disk session cache. Skill-root walk-up still exists for backwards compat with `pip install -e .` workflows.
- **Forceful re-auth**: use `auth.refresh()` (public, returns bool). Don't reach for `auth._refresh()` — it's the private worker that `refresh()` calls.
- **Error messages from `check()` / `ensure()` are typed.** Three failure modes: `InvalidCredentials` (wrong password), `NetworkError` (CAS unreachable), `SessionExpired` (server-side invalidation mid-use). The base `_is_stale_response()` is universal (401/302→CAS); subclasses override for service-specific signals. Don't reimplement stale detection.

## API surface design law (added 2026-07-06)
