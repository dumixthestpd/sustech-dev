# TIS kclb (课程类别) dictionary discovery — 2026-07-08 update

Background: the webui `/tis` page has a Category filter dropdown showing 13
bare kclbmc names: `专业基础课, 专业导论类, 专业必修课, 专业核心课,
专业选修课, 人文类, 培养环节, 外语类, 实践, 社科类, 美育类, 通识必修课,
通识选修课`. Selecting one and clicking Search silently returned 0 results —
every Category filter was broken in personal mode. The bug was filed by the
user on 2026-07-08: "search 美育类 with 通识选修选课 returns nothing".

## Why the bug exists

TIS's `/Xsxk/queryKxrw` (personal mode) does NOT accept the kclbmc name in
`p_kclb` — it expects a **kclbdm code** (numeric). Passing the bare name
silently returns `total=0`. The webui blueprint just forwards `?category=`
verbatim into `p_kclb`, so every category filter in personal mode was
broken.

Campus mode (`/Xsxktz/queryRwxxcxList`) is unaffected because it does
**client-side** substring filtering on the cached catalog (`if category and
category not in c.category: continue`); no TIS API calls.

## Discovery methodology (the right way)

### Step 1: Read the page HTML for component names

The xsxk page (`/Xsxk/query/1`) uses a Vue component `<inco-i-dmb>` with:
```
bm="T_KCK_DM_KCLBB"      ← table name (课程库-代码表-课程类别表)
dmzdm="dm"                ← code field
mczdm="mc"                ← Chinese name
mc_enzdm="ywmc"          ← English name
fdmzdm="fdm"             ← parent code (father dm)
v-model="queryform.p_kclb"
```

This revealed the data source is dictionary table `T_KCK_DM_KCLBB`.

### Step 2: Download the SPA bundle (not guessed URLs)

From the page's 93 script tags, grep for `kclb`:
```
/component/inco/inco.component.kclb-60cab7cc9cccba357d0d6b55ebdb0bab.js
```

Download with `Referer: https://tis.sustech.edu.cn/Xsxk/query/1` + cookies
(Tengine blocks bare curl — must use Python requests.Session with the CAS
cookies and the Referer header).

### Step 3: Read the bundle to find the ACTUAL endpoint

The KCLB bundle (2 KB, clean Vue component definition) reveals:
```js
mounted:function () {
    var self = this
    $.post(baseUrl+'component/queryKclb', {"pylb": this.pylb}, function (res) {
        self.dataList = res.content
    })
}
```

**Key discovery**: the endpoint is `component/queryKclb` (NOT `/Xsxk/queryKclb`
which 404s — the `/Xsxk/` prefix was a wrong guess). Parameter: `pylb`
(培养类别, 1=本科, 2=研究生). Returns `res.content` (array of dicts with
`dm`, `mc`, `ywmc`, `level` fields).

There is also a generic dictionary endpoint `component/queryDmb` that takes
encrypted JSON data — but the kclb-specific one needs no encryption.

### Step 4: Call the endpoint with known-good cookies

Use the webui's TISAuth (which has fresh cookies) to POST to
`https://tis.sustech.edu.cn/component/queryKclb` with `pylb=1` or `pylb=2`.
The response is an array of {dm, mc, ywmc, level, ...} — **22 entries for
undergrad, 9 entries for graduate**.

## The FULL kclbdm mapping (from TIS itself)

### pylb=1 (本科 undergrad — 22 categories)

| kclbdm | Name | Level | English |
|--------|------|-------|---------|
| `03` | 专业基础课 | 1 | MR |
| `04` | 专业必修课 | 1 | MR |
| `05` | 专业选修课 | 1 | ME |
| `07` | 专业核心课 | 1 | MR |
| `08` | 通识必修课 | 1 | GR |
| `09` | 通识选修课 | 1 | GE |
| `0901` | 人文类 | 2 (child of 09) | GE |
| `0902` | 社科类 | 2 (child of 09) | GE |
| `0903` | 艺术类 | 2 (child of 09) | GE |
| `0904` | 其它任选类 | 2 (child of 09) | GE |
| `0905` | 外语类 | 2 (child of 09) | GE |
| `0906` | 劳育类 | 2 (child of 09) | GR |
| `0907` | 美育类 | 2 (child of 09) | GE |
| `0908` | 国学类 | 2 (child of 09) | GE |
| `0909` | 专业导论类 | 2 (child of 09) | GE |
| `10` | 专业必修课 | 1 | MR |
| `11` | 实践 | 1 | EC |
| `13` | 国际化人才培养 | 1 | null |
| `98` | 任选 | 1 | EC |
| `99` | 其他 | 1 | EC |
| `998` | 辅修专业选修学分 | 1 | Minor elective credits |
| `999` | 辅修专业必修学分 | 1 | Minor required credits |

### pylb=2 (研究生 graduate — 9 categories)

| kclbdm | Name | Level |
|--------|------|-------|
| `01` | 培养环节 | 1 |
| `04` | 专业必修课 | 1 |
| `05` | 专业选修课 | 1 |
| `07` | 专业核心课 | 1 |
| `08` | 通识必修课 | 1 |
| `09` | 通识选修课 | 1 |
| `14` | 专业基础课 | 1 |
| `200` | 校外共享课 | 1 |
| `201` | 实践 | 1 |

### Structure: hierarchical via level and code prefix

- `level=1` → top-level (2-3 digit codes)
- `level=2` → child (4-digit codes where first 2 digits = parent code)

The page HTML's `fdmzdm="fdm"` hints at a parent-code column; but
`component/queryKclb` doesn't return an explicit `fdm` field. The
hierarchy is encoded in the `level` field + code prefix (e.g. `0907`
is child of `09`).

## Verified with live TIS search (tested via webui)

`category=0907` on `xkfsdm=xxxk` returns exactly 31 courses with
kclbmc=`通识选修课-美育类`. **Sub-category codes work** as direct
`p_kclb` values in `queryKxrw` — TIS DOES filter by them.

Verified probes across relevant xkfsdm combinations:

| xkfsdm | kclbdm | Expected name | Count | Verified kclbmc in response |
|--------|--------|---------------|-------|---------------------------|
| xxxk | `09` | 通识选修课 | 2 | 通识选修课 (bare) |
| xxxk | `0901` | 人文类 | 21 | 通识选修课-人文类 |
| xxxk | `0902` | 社科类 | 26 | 通识选修课-社科类 |
| xxxk | `0905` | 外语类 | 8 | 通识选修课-外语类 |
| xxxk | `0907` | 美育类 | 31 | 通识选修课-美育类 |
| xxxk | `0909` | 专业导论类 | 28 | 通识选修课-专业导论类 |
| xxxk | `0903` | 艺术类 | 0 | (no courses this term) |
| xxxk | `0904` | 其它任选类 | 0 | (no courses this term) |
| xxxk | `0906` | 劳育类 | 0 | (no courses this term) |
| xxxk | `0908` | 国学类 | (timed out) | — |
| bxxk | `08` | 通识必修课 | 74 | 通识必修课 |
| kzyxk | `05` | 专业选修课 | 10 | 专业选修课 |
| kzyxk | `07` | 专业核心课 | 5 | 专业核心课 |
| kzyxk | `03` | 专业基础课 | 8 | 专业基础课 |
| zynknjxk | `11` | 实践 | 8 | 实践 |

Codes `0903`, `0904`, `0906` return 0 — valid codes, just no courses
in the current term offering. The zero means "code recognized, no results"
not "invalid code".

## Note on code `04` vs `10` in pylb=1

Both `04` and `10` have `mc="专业必修课"` for undergrad. These are
probably distinct sub-types of 必修 across different xkfsdm contexts.
The per-xkfsdm probe confirmed `kzyxk+04` returns 0 (though `kzyxk+03`
专业基础课 returns 8). This is correct TIS behavior — the code selection
depends on context.

## The generic dictionary endpoint (alternative)

For any dictionary table in TIS (not just kclb), the `dmb` component
provides:

```js
$.post(baseUrl + 'component/queryDmb', {data: encrypt_string_data}, ...)
```

Where `data` is AES-encrypted JSON via `this.$root.$encrypt()`. The JSON
has fields: `{bm, dmzdm, mczdm, mc_enzdm, fdmzdm, pxzdm, ldzdm, ldzdz,
cxtj, dgtj}`. For kclb: `bm="T_KCK_DM_KCLBB"`. The encryption is
performed by a function in the inco-ui bundle
(`inco-ui-1.0.0-817f8d27bcd958366877d629d5a89fc6.js`). The unencrypted
`component/queryKclb` endpoint is the simpler path for kclb specifically.

For `xkfsdm=bxxk` (通识必修), every course has `kclbmc=通识必修课`
(bare, matches `kclbdm=08`). No hyphenated sub-categories visible.

This was the key insight from Chrome's HTTP cache: a cached
`?xkfsdm=xxxk` response had `category="通识选修课-美育类"` for 31 courses,
proving the hyphenated format is real TIS data.

## Implication for the fix (hybrid: TIS filter + client suffix filter)

You CANNOT map every dropdown value to a kclbdm. The fix has two parts:

1. **Known codes** (top-level): map bare names → DM code.
2. **Sub-categories**: pass the parent's kclbdm to TIS, then filter
   the response client-side by the suffix (e.g. `-美育类`).

```python
KCLBDM = {"专业选修课": "05", "通识必修课": "08", "通识选修课": "09"}
KCLB_PARENT = {
    "美育类": "通识选修课", "外语类": "通识选修课", "社科类": "通识选修课",
    "实践": "通识选修课", "专业导论类": "通识选修课",
    # anything else: leave alone (no parent match for the 余 ones)
}
```

User's 2026-07-08 instruction was "let TIS do the filtering" — but TIS
can't filter sub-categories, so the hybrid is the only option. The
sub-category case: webui passes `category=09`, TIS returns 119 xxxk
courses, then webui client-side filters to those with
`category="通识选修课-美育类"`, leaving 31.

## Discovery methodology (rule called out 2026-07-08)

When looking for an internal TIS API endpoint or dictionary the upstream
doesn't document: **do NOT guess URL patterns**. Find the presence in
the system first:

1. **Code comments**: `campus_schedule.py:16` literally says
   `p_kclb course category code (from queryKclb)` — the endpoint name is
   right there. But `/Xsxk/queryKclb` 404s, so the comment names a
   no-longer-extant endpoint. Verify; don't trust blindly.
2. **Live API probes with known-good inputs**: the comment also gave
   `e.g. "08" for 通识必修课`. From there we had two more codes (05, 09)
   and could systematically test `01`–`99` to derive the rest by family.
3. **Chrome HTTP cache** at
   `~/Library/Caches/Google/Chrome/Default/Cache/Cache_Data/f_*` — the
   user's own cached requests reveal what they've loaded with their auth.
   The `kclbmc` format (`通识选修课-美育类`) was visible only here, not
   in any test data or disk cache.
4. **The webui's own endpoints**: when the webui's auth is fresh
   (`/api/tis/info` returning full data, not the fallback empty arrays),
   `?mode=personal` searches work because they don't need CAS login —
   they reuse the in-memory TISAuth. These are the cheapest probe targets.

## TISAuth internal structure (notes for future probe work)

Authorizer stores cookies in **`_session_cache` dict**, NOT in a
`requests.Session`. The dict has three keys: `TGC` (JWT), `JSESSIONID`,
`route` (sticky-routing token). TTL is 25 min (`_session_ttl`).
`_cached_session` is the lazily-built requests.Session that's actually
used for outgoing calls. To inspect:

```python
from sustech_survival.sso import TISAuth
a = TISAuth()
a.ensure()
print(a._session_cache)  # {'TGC': '...', 'JSESSIONID': '...', 'route': '...'}
print(a._session_time, a._session_ttl, a._is_session_fresh())
```

To use cookies in Playwright: domain is the parse of `a.BASE_URL`
(`tis.sustech.edu.cn`), path `/`, secure=True, httpOnly=True.

## TIS probe flakiness (rate-limit behavior)

CAS-side rate limit produces ~**1-in-4 empty/timeout responses** even when
TIS is up. Any probe loop MUST treat `total=0` + empty `categories` as
"unknown, retry" not "confirmed no-match". Validated pattern:

```python
def fetch(xkf, code, retries=5):
    for i in range(retries):
        try:
            d = json.loads(urllib.request.urlopen(...).read())
            n = d.get("total", 0); cats = sorted(set(c["category"] for c in d["courses"]))
            if n > 0 or cats:
                return n, cats, d.get("message", "")
        except: pass
        time.sleep(2)
    return 0, [], "GIVEUP"
```

Long sleep between probes (2–3s) plus 5 retries was enough. Without it, the
same code can return 0 once and 74 the next — never trust a single probe.

## Related: kclb dropdown is displayed in `filter_options`

The webui's `/api/tis/info` derives the categories list from the disk-cached
catalog (the same `cache/393f...json` file). It does NOT trigger a live TIS
call to enumerate categories. So the dropdown values are whatever TIS
returned in the most recent `queryRwxxcxList` campus-mode call. To see
fresh categories: hit `/api/tis/refresh` (re-runs the catalog fetch).
