# Authorizer subclass patterns — DO NOT hand-roll CAS

**Iron law for any new SUSTech auth integration:** never write a
standalone CAS POST. The `CASAuthorizer` (in `sso/providers/cas.py`)
handles the full CAS 3.0 flow — execution token extraction, credential
POST, ticket exchange, redirect following, cookie collection. Your
subclass only needs to override what's different.

All internal CAS methods are private (prefix `_`). Don't call them
directly — the Authorizer lifecycle handles them via `ensure()`.

## The three override patterns

| Pattern | When to use | What to override | Examples |
|---|---|---|---|
| **Static SERVICE_URL** | Service has a fixed CAS callback URL. Set class attributes, done. | Nothing (just `BASE_URL` + `SERVICE_URL` + `SUBMIT_VALUE`) | BB, TIS, Lib (Primo), WS |
| **CAS + secondary token** | After CAS exchange, need an additional API handshake for a bearer token | `_refresh()` — do CAS via `self._get_ticket_cookies()`, then secondary handshake | ehall booking (`sso/authlib/booking.py`) |
| **Dynamic SERVICE_URL** | CAS service URL is generated per-login (e.g. authcenter pattern with UUID) | `_refresh()` — resolve dynamic URL, set `self.SERVICE_URL`, then call `self._get_ticket_cookies()` | IC library booking (`lib/booking/auth.py`) |

## The `_refresh()` pattern (for extra steps)

**DO NOT** override `_get_ticket_cookies()`. That method IS the wheel —
`_build_session()` → `_post_cas()` → `_exchange_ticket()`.

Override `_refresh()` instead, which is the Authorizer lifecycle hook:

```python
def _refresh(self) -> bool:
    try:
        username, password = self._read_creds()
    except AuthorizerError as e:
        return False

    try:
        # YOUR pre-CAS steps (e.g. authcenter handshake)
        dynamic_url = self._resolve_authcenter_url()

        # Delegate to the parent CAS flow
        old = self.SERVICE_URL
        self.SERVICE_URL = dynamic_url
        try:
            cookies = self._get_ticket_cookies(username, password)
        finally:
            self.SERVICE_URL = old

        # YOUR post-CAS steps (e.g. verify session cookie)
        self._set_session(cookies)
        return True
    except Exception as e:
        print(f"❌ Refresh failed: {e}")
        return False
```

## The new Authorizer API surface (2026-07-01 refactor)

The Authorizer hides all HTTP. Import the subclass and use it:

```python
auth = TISAuth()
ok, msg = auth.ensure()         # (bool, str) — caller decides
data = auth.get("/api/path")     # GET, BASE_URL prepended
result = auth.post("/api/data")  # POST, BASE_URL prepended
sess = auth.session              # requests.Session with cookies+headers
```

### What changed from the old API:

| Old (removed) | New |
|---|---|
| `auth.requests_session` | `auth.session` (requests.Session) |
| `auth.cookies` | `auth.session.cookies` (requests jar) |
| `auth.load()` / `auth.save()` | **Removed** — no disk I/O |
| `auth.probe_session()` | **Removed** — TTL → refresh only |
| `auth.session_file` / `auth.SESSION_SUBDIR` | **Removed** |
| `auth.get_ticket_cookies()` | `auth._get_ticket_cookies()` (private) |
| `auth.post_cas()` / `auth.exchange_ticket()` | `auth._post_cas()` / `auth._exchange_ticket()` (private) |
| `auth.build_session()` | `auth._build_session()` (private) |
| `auth.cas_url` | `auth._cas_url` (private) |
| `auth.ensure()` disk fallback in check() | **Removed** — in-memory only |
| `@require_auth("tis")` | `@require_auth(TISAuth)` — takes class, injects `auth=` kwarg |
| `@auth.ensured` injects `session=raw_dict` | injects `auth=Authorizer` object |

## What NOT to do

- ❌ **Do not** hand-roll `_fetch_execution()`, `_post_cas()`, or
  `_exchange_ticket()`. They're in `CASAuthorizer` (all private).
- ❌ **Do not** override `_get_ticket_cookies()` unless you're replacing
  the entire CAS exchange (and you shouldn't be).
- ❌ **Do not** subclass `Authorizer` directly for a CAS service —
  use `CASAuthorizer` so you get the `LegacyAdapter`, `SUBMIT_VALUE`,
  `_cas_url` property, and redirect following for free.
- ❌ **Do not** write your own `check()`/`ensure()`/`_refresh()` unless
  you have a non-standard session store. The `Authorizer` base class
  provides all of them.
- ❌ **Do not** name your method `login_password()` if you override
  `_refresh()` instead. The lifecycle calls `_refresh()`, not
  `login_password()`. If client code calls `login_password()`, add
  it as a thin alias that delegates to `_refresh()`.
- ❌ **Do not** wrap the Authorizer in a helper function that returns
  raw cookies ("secondary packing"). See "The secondary packing
  anti-pattern" below.
- ❌ **Do not** add stale-session detection by overriding `get()`/`post()`
  manually. Override `_is_stale_response()` instead — the base class
  handles the retry logic.

## The secondary packing anti-pattern

Do NOT wrap the Authorizer in a helper function:

```python
# ❌ WRONG
tis_auth_singleton = None
def auth():
    global tis_auth_singleton
    if tis_auth_singleton is None:
        tis_auth_singleton = TISAuth()
    ok, reason = tis_auth_singleton.ensure()
    return tis_auth_singleton.cookies    # fragile dict, can't re-ensure
```

`TISAuth()` is already a singleton per subclass — every call site
gets the same in-memory session. The wrapper returns a fragile dict.
Fix:

```python
# ✅ RIGHT
auth = TISAuth()
auth.ensure()
r = auth.get("/api/path")
```

Also don't write `bb/session.py` wrappers that re-export `ensure()`,
`check()`, `refresh()` as module-level functions. Import the class.

## The `@require_auth` decorator

Takes the Authorizer class (not a string), injects the Authorizer as
`auth=` kwarg:

```python
from sustech_survival.sso import TISAuth, require_auth

@require_auth(TISAuth)
def fetch_exams(self, course_id, auth=None):
    data = auth.get("/component/queryKsxxByXs").json()
```

If called without the decorator, `auth=None` and the function can
decide how to handle it. The decorator calls `auth.ensure()` and
raises `AuthorizerError` if it fails.

## How to find the pattern for a new service

1. Open the service URL in the browser (or curl with `--location`).
2. Watch the redirect chain:
   - Direct to CAS → **pattern 1** (static SERVICE_URL)
   - Extra `authcenter/toLoginPage` or `/authcenter/` in the chain
     → **pattern 3** (dynamic SERVICE_URL, authcenter-mediated)
   - Service returns HTML with JS that does an XHR after CAS
     → **pattern 2** (secondary token handshake)
3. Read the JS bundle for `auth/*` or `login/*` API calls to confirm.
4. Set `SERVICE_URL` to the service's CAS callback URL (the URL CAS
   redirects to with the ticket).
5. Test: `auth = YourAuth(); ok, reason = auth.ensure()`.

## Existing subclass gallery

| File | Pattern | What it overrides |
|---|---|---|
| `sso/authlib/booking.py` | CAS + secondary token | `_refresh()` (calls `_get_ticket_cookies()`, then GetUserProfile) |
| `sso/authlib/pms.py` | Direct from Authorizer | Full hand-roll (PMS uses picture-CAPTCHA, not pure CAS) |
| `lib/booking/auth.py` | Dynamic SERVICE_URL | `_refresh()` (resolves authcenter URL, then delegates) |

## The stale-detection + auto-retry pattern (added 2026-07-11)

Since 2026-07-11 `get()` and `post()` on the Authorizer base class
transparently detect stale-session responses and auto-refresh. The
caller never sees `_refresh()` — it's private and stays private.

### How it works

```
get(path):
    1. self.session.get(url)                    # normal request
    2. self._is_stale_response(response)         # subclass decides
    3.   if stale → self._refresh() → retry     # transparent
    4.   if refresh fails → raise typed error   # InvalidCredentials/NetworkError
```

### Three failure modes (distinct exceptions)

| Exception | Meaning | Action |
|---|---|---|
| `InvalidCredentials` | Credentials in `credentials.txt` are wrong | **Don't retry** — same credentials, same result |
| `NetworkError` | CAS is unreachable (timeout, DNS, connection refused) | **Don't retry** — transient from the caller's perspective; upstream won't fix it in 10ms |
| `SessionExpired` | In-memory session stale + refresh succeeded | **Already handled** — `get()`/`post()` retried |

`_last_refresh_error` stores the typed exception after a failed
`_refresh()` call. `check()` / `ensure()` read it to produce
different messages for wrong password vs network failure.

### `_is_stale_response()` — the pluggable criterion

Each subclass overrides this single method. The base returns `False`
(no auto-retry). The criterion is **service-specific and sometimes
endpoint-specific** — different endpoints within one service may
return different stale signals.

```python
class TISAuth(CASAuthorizer):
    def _is_stale_response(self, response) -> bool:
        # Signal 1: 302/303 redirect to CAS login
        if response.status_code in self.REDIRECT_STATUS:
            loc = response.headers.get("Location", "")
            if "cas.sustech.edu.cn" in loc:
                return True
        # Signal 2: XHR endpoint returns HTML login page instead of JSON
        ct = response.headers.get("Content-Type", "")
        if ct and "text/html" in ct:
            snippet = getattr(response, "text", "")[:1000].lower()
            if "统一身份认证" in snippet or "cas/login" in snippet:
                return True
        return False
```

### Per-service staleness criteria (verified 2026-07-11)

| Service | Signal | Rationale |
|---|---|---|
| **TIS** | `302` → `cas.sustech.edu.cn` **OR** HTML login page in XHR response | Non-XHR endpoints redirect; XHR endpoints return CAS HTML instead of JSON |
| **BB** | `HTTP 401` on REST API | Blackboard Learn REST API returns 401 when the session cookie is dead |
| **Lib (Primo)** | `302` → `casRedirect` **OR** HTML containing "sign in" | Primo redirects to its CAS callback endpoint |
| **Booking (ehall)** | `302` → authcenter login page | ehall apps redirect through authcenter |
| **PMS** | HTML with login form (no clear HTTP status difference) | PMS doesn't use CAS — custom auth with picture CAPTCHA |
| **WS** | `302` → CAS login | Same CAS pattern as TIS |

### Design rules for stale detection

1. **`_refresh()` stays private.** The public surface is `ensure()`
   (check + auto-refresh), `get()`/`post()` (stale detection + retry),
   and `refresh()` (forceful re-auth, returns bool). Nobody calls
   `_refresh()` from outside the Authorizer tree.

2. **Every subclass CAN override `_is_stale_response()`.** Default is
   `False` (no auto-retry). Services that don't need it (e.g. a
   static API with no session) just leave the default.

3. **Stale criterion may differ per endpoint within one service.**
   TIS is the clearest example: HTML endpoints return 302, XHR
   endpoints return HTML login page. The `_is_stale_response()` method
   checks both signals — it doesn't know which endpoint was called,
   it just recognizes stale patterns.

4. **Test on real endpoints.** The criteria above are derived from
   existing usage patterns but should be verified against every
   endpoint the module calls — especially TIS and PMS. A stale signal
   that's wrong causes false positives (auto-refresh on legitimate
   302s) or false negatives (session silently dead, request fails
   with confusing error).

### What NOT to do with stale detection

- ❌ **Do not** override `get()` or `post()` to add stale detection
  manually. Override `_is_stale_response()` instead — the base class
  wraps the retry logic.
- ❌ **Do not** return `bool` from `_refresh()` and then call
  `_refresh()` from outside the class. If you need a typed error,
  check `_last_refresh_error` after `refresh()` returns `False`, or
  call `_raise_last_error()`.
- ❌ **Do not** add a catch-all `raise` inside `_refresh()` that
  crashes. `_refresh()` catches every failure, stores the typed
  exception in `_last_refresh_error`, and returns `False`. The
  exception is raised later by `_raise_last_error()` in `get()`/`post()`
  or translated to a string by `_refresh_error_message()` in `check()`.
- ❌ **Do not** bail to a Playwright headful `login()` as the sole
  retry strategy. `_refresh()` should handle CAS headlessly. Reserve
  `login()` for services with CAPTCHA (PMS) or where the CAS redirect
  chain is too complex for HTTP-level handling.

### Implementation map (2026-07-11)

| File | What it has |
|---|---|
| `sso/authorizer.py` | `_is_stale_response()`, `_raise_last_error()`, `_refresh_error_message()`, `_last_refresh_error`; wrapped `get()`/`post()`; typed-exception-aware `check()` |
| `sso/providers/cas.py` | `_get_ticket_cookies()` catches `requests.ConnectionError`/`Timeout` → `NetworkError`; `_post_cas()` raises `InvalidCredentials` for wrong password |
| `sso/__init__.py` | `TISAuth._is_stale_response()`, `BBAuth._is_stale_response()`, `LibAuth._is_stale_response()` |

## SSL / TLS — why the LegacyAdapter needs `get_connection_with_tls_context` override

**Problem:** SUSTech's Primo library server (`sustc.primo.exlibrisgroup.com.cn`)
uses an ancient OpenSSL that requires `OP_LEGACY_RENEGOTIATION` — disabled
by default in OpenSSL 3.2+. Raw Python `ssl.wrap_socket()` works when you
set `OP_LEGACY_SERVER_CONNECT | verify_mode=CERT_NONE | check_hostname=False`,
but urllib3 (and therefore requests) ignores these settings in two places.

**The cascading overrides (discovered 2026-07-01 on macOS 26.5 / OpenSSL 3.5):**

| Layer | What it does | Why it breaks |
|---|---|---|
| 1. `urllib3.util.ssl_.create_urllib3_context()` | Creates a default SSLContext without `OP_LEGACY_SERVER_CONNECT` | Custom context must be passed via `PoolManager(ssl_context=...)` |
| 2. `urllib3.connection._ssl_wrap_socket_and_match_hostname()` | **Overrides `context.verify_mode = resolve_cert_reqs(cert_reqs)`** | Even if you pass a custom SSLContext with `verify_mode=CERT_NONE`, it resets it to `CERT_REQUIRED` (the default) |
| 3. `requests.adapters._urllib3_request_context()` | **Hardcodes `cert_reqs = "CERT_REQUIRED"` and merges it on top of pool kwargs** | Overrides any `cert_reqs` you set in `init_poolmanager()`, including `cert_reqs=0` (CERT_NONE) |

**The fix:** Override `get_connection_with_tls_context` in the HTTPAdapter
to force `verify=False`, which makes `_urllib3_request_context` set
`cert_reqs = "CERT_NONE"` instead of the default `"CERT_REQUIRED"`:

```python
class LegacyAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = legacy_ctx
        return super().init_poolmanager(*args, **kwargs)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        return super().get_connection_with_tls_context(
            request, verify=False, proxies=proxies, cert=cert
        )
```

**Why `verify=False` doesn't weaken security:** The Primo server requires
legacy renegotiation AND has a broken cert chain. Without `CERT_NONE`,
the connection fails at the TLS handshake level — there's no way to verify
the cert anyway. The session cookie (`JSESSIONID` / `ic-cookie`) is
server-randomized per login and carries the real auth.

**Two locations in the codebase with this pattern:**
- `sso/providers/cas.py` — `CASAuthorizer._build_cas_session()` (the CAS
  ticket exchange session, used when the redirect URL targets Primo)
- `sso/__init__.py` — `LibAuth._build_session()` (the Primo session used
  for actual API calls after login)

**The monkey-patch approach:** `cas.py` line 16-22 patches
`urllib3.util.ssl_.create_urllib3_context` to add `OP_LEGACY_SERVER_CONNECT`.
This is a module-level fallback that catches any urllib3-context creation
that doesn't go through our custom adapters. It's insufficient alone
because it doesn't set `CERT_NONE` — the `_ssl_wrap_socket_and_match_hostname`
function still overrides it. The monkey-patch is kept for defensive depth
but the real fix is the adapter override.

**Diagnosis recipe (when a new SUSTech subdomain has SSL issues):**
1. Try `ssl.wrap_socket()` directly with `OP_LEGACY_SERVER_CONNECT | CERT_NONE` → if it works but urllib3 fails, it's the cert_reqs cascade.
2. Monkey-patch `urllib3.connection.ssl_wrap_socket` to see what SSLContext urllib3 actually passes to the socket (patched at `urllib3.connection`, NOT `urllib3.util.ssl_` — the function is imported by name).
3. Check that `verify=False` is reaching `_urllib3_request_context` by tracing the `cert_reqs` value through `connection_from_host` → `_merge_pool_kwargs` → `connection_from_pool_key` → `_new_pool`.

## See also

- `sso/authorizer.py` — base class (contains `_is_stale_response`, `_raise_last_error`, wrapped `get`/`post`)
- `sso/providers/cas.py` — CASAuthorizer (raises `InvalidCredentials` / `NetworkError` from CAS flow)
- `sso/__init__.py` — TISAuth, BBAuth, LibAuth stale detection overrides
- `sustech-dev/SKILL.md` — auth patterns table + "Things agents must never do"
- `sustech-architecture/references/authorizer-subclass-patterns.md` — same content
- `sso/__init__.py` — module docstring with quick-reference
