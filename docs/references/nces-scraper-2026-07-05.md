# NCES scraper + Anubis solver — reproduction recipe

> **Companion to `sustech-dev/SKILL.md` §8 (Anubis PoW bypass) and §9
> (NCES listing scraper).** Created 2026-07-05. This file is the
> hands-on reproduction recipe; the SKILL.md sections above are the
> catalog summary.

## TL;DR

```bash
# Install (optional extra pulls in anubis-solver)
pip install "sustech-survival[nces]"

# Refresh the cache (~3-5s, 6 pages × ~8 unique courses each)
sustech nces refresh

# Look up a course
sustech nces lookup HUM032
# 写作与交流 · 周秀梅  [HUM032]
#   semester:  2026秋
#   ★ 10.0/10  (38 reviews)
#   Difficulty:       Easy (93%)
#   Workload:         Light (92%)
#   Grading:        Excellent (100%)
#   Takeaways:        Heavy (91%)
#   https://ncesnext.com/course/524/

# Status
sustech nces status
```

## Anubis PoW — verified algorithm

Anubis v1.25.0 (ncesnext.com's deployment). Verified by reading
`/.within.website/x/cmd/anubis/static/js/main.mjs`.

**Challenge JSON** embedded in:
```html
<script id="anubis_challenge" type="application/json">{...}</script>
```

**JSON shape:**
```json
{
  "id": "019f3280-02b9-74ce-b068-f1d052d28f04",
  "method": "fast",
  "randomData": "<hex string ~128 chars>",
  "difficulty": 2,
  "spent": false
}
```

**Regex extraction (robust to markup shifts):**
```python
import re
m = re.search(
    r'"id":"([0-9a-f-]{36})"[^}]*"randomData":"([0-9a-f]+)"'
    r'[^}]*"difficulty":(\d+)',
    html,
)
ch_id, ch_data, diff = m.group(1), m.group(2), int(m.group(3))
```

**PoW solver (no deps beyond stdlib):**
```python
import hashlib
prefix = '0' * diff
n = 0
while True:
    h = hashlib.sha256((ch_data + str(n)).encode()).hexdigest()
    if h.startswith(prefix):
        break
    n += 1
# h = hash result (hex), n = winning nonce
```
At difficulty=2 → ~256 hashes → <1ms on modern hardware.
At difficulty=4 (default per docs) → ~65k hashes → ~50-100ms.

**Submission (GET, server sets cookie + 302s to `redir`):**
```
GET /.within.website/x/cmd/anubis/api/pass-challenge
    ?id={ch_id}
    &response={h}
    &nonce={n}
    &redir=https://ncesnext.com/course/?sort_by=rating
    &elapsedTime={ms}
```

**Cookie:** `techaro.lol-anubis-auth` (JWT, EdDSA-signed),
`CookieDefaultExpirationTime = 7 * 24 * time.Hour` per Anubis source.
Cookie verification cookie: `techaro.lol-anubis-cookie-verification`.

**Verification probe (live 2026-07-05):**
```bash
# Anubis solved — page returns real HTML
curl -sS --max-time 10 -A "Mozilla/5.0" \
  "https://ncesnext.com/course/?sort_by=rating"
# → 31-32 KB real HTML, has <a class="px16" href="/course/...">

# Without Anubis cookie:
# → 4.4 KB Anubis challenge page (or rate-limited)
```

## NCES listing parser — verified regex map

**Block split:** each course is wrapped in
`<div class="ud-pd-md dashed">`. Split HTML on this string and parse
each block independently.

**Per-block extraction:**
```python
# Course link + name + teacher + code
m_link = re.search(
    r'<a class="px16" href="/course/(\d+)/">([^<（]+)（([^）]+)）\s*'
    r'<span class="badge[^>]+>([A-Z]{2,4}\d{3}[A-Z]?)</span>',
    block,
)
# m_link.group(1) → nces_id (e.g. "524")
# m_link.group(2) → name    (e.g. "写作与交流")
# m_link.group(3) → teacher (e.g. "周秀梅")
# m_link.group(4) → code    (e.g. "HUM032")

# Rating + review count
m_rating = re.search(
    r'<span class="rl-pd-sm h4 mono-font">([\d.]+)</span>'
    r'\s*<span class="text-body-secondary px12">\((\d+) 人评价\)',
    block,
)
# group(1) → rating (e.g. "10.0")
# group(2) → count  (e.g. "38")

# Semester
m_sem = re.search(
    r'<span class="small text-body-secondary">\s*(\d{4}[春秋])', block
)

# 4 dimensions × (pct, label)
for cn_label, key in [
    ("课程难度", "difficulty"),
    ("作业多少", "workload"),
    ("给分好坏", "grading"),
    ("收获大小", "takeaways"),
]:
    m_d = re.search(
        rf'{re.escape(cn_label)}'
        r'.*?<div class="progress-bar[^"]*"[^>]*'
        r'style="width:\s*([\d.]+)%;"[^>]*>\s*([^<]+?)\s*</div>',
        block, re.DOTALL,
    )
    pct = float(m_d.group(1)) if m_d else 0.0
    cn_val = m_d.group(2).strip() if m_d else ""
    val = LABEL_EN.get(cn_val, cn_val)  # Chinese→English
```

**Label map (Chinese → English):**
```python
LABEL_EN = {
    "简单": "Easy",      "中等": "Medium",    "困难": "Hard",
    "很少": "Light",     "一般": "Average",   "很多": "Heavy",
    "超好": "Excellent", "好":   "Good",      "差":   "Poor",
}
```

## CAS auth via cas-proxy.cra.moe

**Service URL:** `https://cas-proxy.cra.moe/callback` (NOT
`https://ncesnext.com/login/oauth/callback/` — wrong service URL).

**Flow (4 hops):**
1. `GET https://cas.sustech.edu.cn/cas/login
       ?service=https://cas-proxy.cra.moe/callback`
   → 200 with execution token + login form
2. `POST https://cas.sustech.edu.cn/cas/login` with
   `username`, `password`, `execution`, `_eventId=submit`,
   `submit="登录"`
   → 302 to `cas-proxy.cra.moe/callback?ticket=ST-...`
3. `GET cas-proxy.cra.moe/callback?ticket=...` (allow redirects)
   → cas-proxy validates ticket, sets NCES session cookie, 302s
   to ncesnext.com
4. `GET ncesnext.com/` with the session cookie
   → 200, logged in

**Cas-proxy verifies the ticket by calling CAS, then sets the NCES
session cookie that the application understands. The whole dance takes
~1-2s and produces cookies for: CAS TGC (CAS domain), cas-proxy
session (cas-proxy.cra.moe domain), NCES session (ncesnext.com domain).
NCESAuth(SERVICE_URL=...) flattens all of them into the Authorizer's
session cache via _get_ticket_cookies().

## Pitfalls hit during this session

1. **Old server (PID 97336) stuck on port 61019** with stale Flask
   templates — Jinja reloads by default but blueprints registered at
   startup don't get re-registered. Always `kill` old servers before
   re-launching with new blueprints. Or use port 0 / dynamic port.

2. **Bundled Anubis JS lives at
   `/.within.website/x/cmd/anubis/static/js/main.mjs`** — the
   pass-challenge endpoint URL is in there (`grep pass-challenge`).
   Don't try to discover by URL probing.

3. **`ncesnext.com/search?q=X` returns 308** (redirect to
   `/course/?page=1&sort_by=rating`?) — the search page is NOT what
   naive URL guessing suggests. The listing page (`/course/?sort_by=...`)
   IS the data source. Don't waste time on search endpoints.

4. **`?code=X` query param doesn't filter the listing** — ncesnext.com
   ignores it. To find a course by code, scrape the listing and build
   your own code→course map.

5. **`ncesnext.com/sitemap.xml` is public** (172KB) and lists
   `/course/<id>/#review-<review_id>` URLs. Useful for ensuring full
   coverage when scraping course detail pages. NOT useful for code
   mapping (codes aren't in the sitemap).

6. **web_extract (parallel extractor) times out** on ncesnext.com —
   it doesn't solve Anubis. Don't use it for this site; use raw curl /
   requests AFTER solving PoW.

7. **Anubis gets sticky after rapid calls** — multiple consecutive
   requests from the same IP get the challenge every time. Rate-limit
   to 0.5s between scraper calls; sleep 1-2s; use sleep_if_rate_limited
   on 5xx-like responses.

## Test data (live, 2026-07-05)

| Code | Course | Teacher | Sem | Rating | Reviews | Diff | Work | Grade | Take |
|---|---|---|---|---|---|---|---|---|---|
| HUM032 | 写作与交流 | 周秀梅 | 2026秋 | 10.0 | 38 | Easy 93% | Light 92% | Excellent 100% | Heavy 91% |
| CLE022 | SUSTech English II | 喻永阳 | 2026秋 | 9.9 | 43 | Easy 86% | Light 91% | Excellent 99% | Heavy 88% |
| ESE201 | 大学地球科学 | 叶建淮 | 2026秋 | 10.0 | 26 | Easy 83% | Light 96% | Excellent 100% | Heavy 90% |
| GEM063 | 合唱 | 王奕-外聘 | 2026秋 | 10.0 | 19 | Easy 100% | Light 100% | Excellent 100% | Heavy 89% |
| IPE111 | 思想道德与法治 | 杨少曼 | 2026春 | 9.8 | 27 | Easy 100% | Light 100% | Excellent 98% | Heavy 89% |
| MAE203B | 理论力学I-B | 洪伟 | 2023秋 | 9.5 | 2 | (unverified — not in default sort listing) |
| PHY101 | 普通物理学（上） | 陈伟强 | 2025秋 | 9.9 | 16 | Medium 25% | Medium 63% | Excellent 81% | Heavy 91% |

## Open follow-ups

- **Per-review text scraping** — need authenticated session; doesn't fit
  in the listing-scraper model. Build on top of NCESAuth() session.
- **OIDC code-flow** for users who authenticate via browser (Keycloak
  realm `cra-service-realm`, `client_id=cra-nces`). Not needed for
  headless from Python — CAS-via-proxy covers it.
- **Submitting reviews programmatically** — needs `/api/notifications/` +
  per-course POST endpoint discovery. Out of scope for the hover card;
  user-facing write features would need their own design pass.
- **Real-time sync** — current design refreshes the 38-course-cache
  every 24h. For higher-frequency updates, subscribe to `/sitemap.xml`
  and re-fetch only changed course IDs.
