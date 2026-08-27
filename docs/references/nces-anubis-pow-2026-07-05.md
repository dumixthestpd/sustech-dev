# NCES Anubis PoW bypass — session transcript + reusable code

> **Captured 2026-07-05.** Validated end-to-end against the live
> `ncesnext.com/course/?sort_by=rating` page. Difficulty=2 at capture
> time — re-probe before relying on these numbers.

## TL;DR

- `ncesnext.com` is behind **Anubis 1.25.0** Proof-of-Work challenge.
- The challenge: SHA256 PoW where `SHA256(randomData + nonce)` must
  have `difficulty` leading hex zeros (2 hex chars ≈ 8 bits ≈ 256
  hashes expected).
- Submit via `GET /.within.website/x/cmd/anubis/api/pass-challenge?id=...&response=...&nonce=...&redir=...&elapsedTime=...`.
- On success, server sets `Set-Cookie: techaro.lol-anubis-auth=<JWT>`,
  valid **7 days** (`CookieDefaultExpirationTime = 7 * 24 * time.Hour`
  per Anubis source).
- After getting the cookie, all subsequent requests pass through
  normally — no repeat challenge until cookie expiry.
- At difficulty=2, single-thread solve takes **<10ms** on a modern
  MacBook.

## Full probe transcript (2026-07-05 21:22 CST)

```
1. GET https://ncesnext.com/course/?sort_by=rating
   → HTTP 200, 31126b of real HTML (got lucky — Anubis did NOT challenge
     this first request; didn't even get the AnubisHTML, was real)

   # OR (more commonly seen on rapid-fire):
1'. GET https://ncesnext.com/course/?sort_by=rating
   → HTTP 200, 4376b of Anubis HTML:
     <title>Making sure you're not a bot!</title>
     ...
     <script id="anubis_challenge" type="application/json">
       {"rules":{"algorithm":"fast","difficulty":2,"report_as":2},
        "challenge":{
          "issuedAt":"2026-07-05T21:21:25...+08:00",
          "metadata":{"User-Agent":"...","X-Real-Ip":"2a09:..."},
          "id":"019f3270-de7e-7331-8da3-76cd62504411",
          "method":"fast",
          "randomData":"804b504941035d63f1...","difficulty":2,"spent":false
        }}
     </script>

2. SHA256 mine: find nonce where SHA256(randomData+nonce) starts with '00'
   python> n = 0; while True:
              h = hashlib.sha256((ch['randomData']+str(n)).encode()).hexdigest()
              if h.startswith('0'*2): break
              n += 1
   → nonce=308, hash='0004...', elapsed=0ms

3. GET https://ncesnext.com/.within.website/x/cmd/anubis/api/pass-challenge
       ?id=019f3270-de7e-7331-8da3-76cd62504411
       &response=0004ce...
       &nonce=308
       &redir=https://ncesnext.com/course/?sort_by=rating
       &elapsedTime=0
   → HTTP 302 → real page
   → Set-Cookie: techaro.lol-anubis-auth=<JWT>; Path=/; Max-Age=604800

4. GET https://ncesnext.com/course/?sort_by=rating
   → HTTP 200, 31126b (clean course listing HTML — no challenge)

5. Trace OAuth flow: GET /login/oauth/
   → HTTP 302 →
     Location: https://sso.cra.ac.cn/realms/cra-service-realm/protocol/openid-connect/auth
              ?response_type=code
              &client_id=cra-nces
              &redirect_uri=https%3A%2F%2Fncesnext.com%2Flogin%2Foauth%2Fcallback%2F
              &scope=profile&state=...
```

**Critical insight:** the auth flow at `/login/oauth/` does NOT go
to `cas.sustech.edu.cn` directly — it goes through **Keycloak OIDC
at `sso.cra.ac.cn/realms/cra-service-realm/`** with `client_id=cra-nces`.
This means `NCESAuth(CASAuthorizer)` would not work out of the box
without first implementing the Keycloak code flow (~200 LOC).
The listing scraper doesn't need auth — listing pages are public
data, Anubis-only.

## Reusable Python: 10-line solver

For projects that don't want to depend on the `anubis-solver` PyPI
package:

```python
import hashlib, re, json, time
import requests

def ensure_anubis_cookie(session: requests.Session, base_url: str) -> None:
    """Solve Anubis challenge if one is set, store the 7-day cookie."""
    r = session.get(base_url)
    if "anubis_challenge" not in r.text:
        return  # no challenge, nothing to do
    m = re.search(
        r'"id":"([0-9a-f-]{36})"[^}]*"randomData":"([0-9a-f]+)"'
        r'[^}]*"difficulty":(\d+)', r.text
    )
    if not m:
        raise RuntimeError("anubis_challenge format changed — re-probe")
    ch_id, ch_data, diff = m.group(1), m.group(2), int(m.group(3))
    prefix = '0' * diff
    t0 = time.time()
    n = 0
    while True:
        h = hashlib.sha256((ch_data + str(n)).encode()).hexdigest()
        if h.startswith(prefix):
            break
        n += 1
    elapsed_ms = int((time.time() - t0) * 1000)
    session.get(
        f"{base_url}/.within.website/x/cmd/anubis/api/pass-challenge",
        params={
            "id": ch_id,
            "response": h,
            "nonce": n,
            "redir": base_url,
            "elapsedTime": elapsed_ms,
        },
    )
    # Now session has techaro.lol-anubis-auth cookie, valid 7 days
```

## When to use the `anubis-solver` PyPI package instead

Use `pip install anubis-solver` (`>=0.1`) when you want:
- Multiprocessing-aware solves (CPU pool), helpful at higher
  difficulty settings (>4). Difficulty=2 is single-thread-fast,
  so the package's pool machinery is overhead.
- Future-proofing against algorithm changes — package handles
  `fast` vs `slow` algorithms automatically.
- Generic interface (`solve(url)` returns cookie dict) — easier
  than the inline function above.

Use the inline 10-liner when:
- You control the algorithm surface (NCES only uses `fast`, difficulty
  2-4) and want zero dep.
- You need the cookie to plug directly into an existing
  `requests.Session` (the package returns a string, not a session).

## Listing-page selectors (HTML parser, 2026-07-05)

For scraping `/course/?sort_by=rating` listings, the regex + selectors
below worked against the live HTML. 5709 courses total, ~20 per page
on sort=rating.

```python
RE_COURSE_LINK = re.compile(
    r'<a class="px16" href="/course/(\d+)/">([^<]+)（([^）]+)）'
    r'\s*<span class="badge[^>]+>([A-Z]{2,4}\d{3}[A-Z]?)</span>'
)
RE_RATING = re.compile(
    r'<span class="rl-pd-sm h4 mono-font">([\d.]+)</span>'
    r'\s*<span class="text-body-secondary px12">\((\d+) 人评价\)'
)
RE_SEMESTER = re.compile(
    r'<span class="small text-body-secondary">\s*(\d{4}[春秋]?)'
)
RE_DIM = re.compile(
    r'(课程难度|作业多少|给分好坏|收获大小)'
    r'.*?<div class="progress-bar[^"]*"[^>]*style="width:\s*([\d.]+)%;"'
    r'[^>]*>\s*([^<]+?)\s*</div>',
    re.DOTALL,
)
```

Per-page fields extracted (in display priority order):
1. **name** (Chinese) — group 2 of RE_COURSE_LINK
2. **teacher** (Chinese) — group 3 of RE_COURSE_LINK + class_group
3. **code** (e.g. `HUM032`) — group 4 of RE_COURSE_LINK
4. **nces_id** (int) — group 1 of RE_COURSE_LINK
5. **rating** (float 0-10) — group 1 of RE_RATING
6. **review_count** (int) — group 2 of RE_RATING
7. **semester** (e.g. "2026秋") — group 1 of RE_SEMESTER
8. **dimensions** — `dict` keyed by Chinese label, value `(pct, label)`

## 🔄 Re-probe recipe (when the Anubis version changes)

If `anubis-challenge` patterns change or you get HTTP 200 + 4KB on
an old working scrape:

```bash
# 1. Inspect raw response — does it contain the challenge script?
curl -sS -i -A "Mozilla/5.0" "https://ncesnext.com/course/?sort_by=rating" \
  | head -c 5000

# 2. Look for anubis_version reference
curl -sS "https://ncesnext.com/.within.website/x/cmd/anubis/static/js/main.mjs?cacheBuster=1.25.0" \
  | grep -oE 'algorithm[^,]+|difficulty[^,]+'

# 3. Reference: Anubis source
# https://github.com/TecharoHQ/anubis/blob/main/lib/policy/policy.go
```

Update this skill with the new version + selectors. Keep `difficulty`
check at runtime, not hardcoded — Anubis can change per-policy.

## What we left NOT implemented

- **Full OIDC code flow** for Keycloak at `sso.cra.ac.cn/...` —
  required for login-only review text, not needed for listing data.
  ~200 LOC: GET auth endpoint, parse Keycloak login form, POST
  credentials (or via federated CAS button), capture auth code,
  POST to token endpoint, receive tokens, call `ncesnext.com`
  with `Authorization: Bearer <token>`. Defer to a follow-up
  session when the user needs per-review text.
- **Per-course detail scraping** — uses authenticated session,
  blocks on OIDC implementation. The listing aggregate stats are
  the hover card's data; per-review text would need detail scraping.
- **Subclassing TISAuth's existing CAS module to handle OIDC** —
  the user's instinct was "NCES CAS SSO should also be build as a
  special subclass of authorizer" (voice memo 2026-07-05), but the
  Keycloak OIDC dance differs enough from CAS 3.0 that direct
  inheritance from `CASAuthorizer` doesn't save LOC. A separate
  `KeycloakAuthorizer` base or a per-service `_refresh()` override is
  the cleaner pattern (matches the three existing patterns in iron
  law #12).
