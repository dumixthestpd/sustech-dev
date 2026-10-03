# ncesnext.com — Anubis PoW challenge probe

> **Superseded 2026-10-04**: the Anubis gate is gone and `/api/v1/*` now
> serves plain JSON. Read
> [ncesnext-public-api-2026-10-04.md](ncesnext-public-api-2026-10-04.md)
> first; this note remains as the record of the gate-**up** posture (and the
> warning that the posture flips). One fact below is now wrong: the header
> check says iframe embedding is allowed — the site now sends
> `X-Frame-Options: SAMEORIGIN`, so it isn't.

> Verified 2026-07-05. Re-probe with
> `bash scripts/probe_ncesnext.sh` before designing any new
> ncesnext.com integration — the protection may change.

## TL;DR

- Every request to `ncesnext.com` (HTML and `/api/*`) is gated by
  **Anubis** proof-of-work challenge. The browser must solve SHA256
  PoW (`difficulty:2`, ~5-15s of mining in JS) before the real
  content is served.
- Server-side `requests` / `curl` / `cloudscraper` cannot solve it.
- **No public read API** — all `/api/*` paths return the Anubis
  challenge HTML (HTTP 200, `content-type: text/html`).
- `web_extract` (Hermes parallel extractor) also times out — it
  doesn't run JS to solve the challenge either.
- The user's browser, however, handles it transparently.
- **Iframe embedding works**: no `Content-Security-Policy` /
  `frame-ancestors` and no `X-Frame-Options` headers (verified
  with `curl -I`).

## Probed URLs (all returned Anubis challenge, not real content)

```
https://ncesnext.com/                             → 4441B Anubis challenge
https://ncesnext.com/search?q=MSE306              → 4441B Anubis challenge
https://ncesnext.com/course/8721/                 → 4492B Anubis challenge
https://ncesnext.com/api/courses/?search=MSE306   → 4386B Anubis challenge
https://ncesnext.com/api/v1/courses/              → 4386B Anubis challenge
https://ncesnext.com/api/evaluations/             → 4386B Anubis challenge
https://ncesnext.com/graphql                      → 404 (or Anubis)
https://ncesnext.com/_next/data                   → 404 (or Anubis)
https://ncesnext.com/api                          → 4386B Anubis challenge
https://ncesnext.com/swagger                      → 4386B Anubis challenge
https://ncesnext.com/openapi.json                 → 4386B Anubis challenge
https://ncesnext.com/.well-known/openapi.json     → 4386B Anubis challenge
https://ncesnext.com/courses/MSE306               → 4386B Anubis challenge
```

All returning `4441B Anubis` had identical body — the same PoW
challenge page that runs in the browser.

The exception is the sitemap:

```
https://ncesnext.com/sitemap.xml   → HTTP 200, 172859B
https://ncesnext.com/robots.txt    → HTTP 200, 533B
```

Both are served without Anubis gate — useful for discovery.

## What the Anubis challenge looks like

The challenge page is a small standalone HTML page with:

```html
<script id="anubis_challenge" type="application/json">
  {
    "rules": {"algorithm": "fast", "difficulty": 2},
    "challenge": {
      "issuedAt": "...",
      "metadata": {
        "User-Agent": "...",
        "X-Real-Ip": "..."
      },
      "id": "019f3234-a95e-...",
      "method": "fast",
      "randomData": "f527d4b4...3c59",
      "policyRuleHash": "ac980f49c4d35fab",
      "difficulty": 2,
      "spent": false
    }
  }
</script>
```

After solving, the browser POSTs back to
`/.within.website/x/cmd/anubis/api/<id>/check` and receives a
cookie (`anubis-challenge-pass`) that the server accepts on
subsequent requests.

## Sitemap structure

URLs that DO exist in the sitemap:

- `https://ncesnext.com/course/<numeric_id>/` — course landing page
- `https://ncesnext.com/course/<numeric_id>/#review-<review_id>` — review anchor on a course page

There are **no course-code (e.g. `MSE306`) URLs** in the sitemap.
The site identifies courses by internal numeric IDs, not TIS codes.
The course code → numeric ID mapping is NOT publicly exposed —
finding it would require Anubis-solving the search page.

## robots.txt

```
User-agent: *
Disallow: /api/*                        ← /api routes exist but are gated
Disallow: /course/*/material/           ← course materials
Disallow: /course/*/upvote/             ← voting
Disallow: /course/*/undo-upvote/
Disallow: /course/*/downvote/
Disallow: /course/*/undo-downvote/
Disallow: /course/*/follow/             ← following courses
Disallow: /course/*/unfollow/
Sitemap: https://ncesnext.com/sitemap.xml
```

The presence of `Disallow: /api/*` is a strong signal that
`/api/*` routes DO exist — they're just behind Anubis.

## Header check

```
X-Frame-Options:        (absent)
Content-Security-Policy: (absent — would have frame-ancestors directive)
```

→ **iframe embedding is allowed for any origin.** No
`Content-Security-Policy: frame-ancestors 'none'` or
`X-Frame-Options: DENY` to block us.

## Implications for `sustech_survival.nces`

### What is NOT possible server-side

- Scraping `__NEXT_DATA__` from course pages — Anubis
- Calling `/api/*` endpoints — Anubis
- Caching/aggregating community eval data — Anubis
- Building a TIS code → nces course ID mapping — would require
  Anubis solving the search page for every code
- Pure-Python SHA256 mining PoW solver — possible (~200 LOC) but
  **directly violates the site's stated anti-AI-scraping policy**.
  The Anubis challenge page literally says *"make scraping much
  more expensive"*. Any session that builds this is opting into an
  arms race with the maintainers.

### What IS possible

| Path | How | Trade-offs |
|------|-----|------------|
| **User-facing link** | Server returns `direct_url: "https://ncesnext.com/search?q={code}"` | User leaves app. **Zero new deps, zero maintenance.** |
| **Iframe embed** | Server returns an HTML wrapper page that `<iframe src="https://ncesnext.com/search?q={code}">`s; user solves Anubis once, then the search renders inside | Stays in app. No backend deps. ~25 LOC. **Best UX/dependency tradeoff.** |
| **Playwright per request** | Headless Chromium solves Anubis, scrapes `__NEXT_DATA__`, returns JSON | Heavy: 200MB+ Chromium, 3-5s latency per request, ongoing Anubis-version arms race, likely violates ToS |
| **Cached snapshots** | Power users submit eval JSON manually; server caches + serves to other users | Requires a sharing backend (separate service) |

### Recommended approach

**Iframe embed for the web UI + direct URL fallback.** The
`/api/tis/nces?code=X` endpoint should return BOTH `embed_url`
and `direct_url`. The frontend renders the iframe in the eval tab
with a "Open in new tab" footer button.

## Verification recipe (re-run anytime)

```bash
bash ~/.hermes/skills/sustech-dev/scripts/probe_ncesnext.sh
```

The script re-checks:

1. Whether the homepage still returns Anubis challenge (vs real HTML)
2. The `X-Frame-Options` / `Content-Security-Policy` headers (iframe-friendly?)
3. Whether `/sitemap.xml` is still accessible without Anubis

If any of these flips, the recommended strategy may need to
change. Re-run before starting any new NCES design work.

## What this DOES NOT cover

- The actual user-facing search/eval UI on ncesnext.com
- The community eval submission flow (would require solving Anubis
  + cookies)
- Any changes Anubis makes to its challenge algorithm

For those: re-probe with the script first, then drive the live UI
in Playwright with a real browser session.
