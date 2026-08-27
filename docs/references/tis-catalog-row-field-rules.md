# TIS 个人选课 (Personal Selection) — `Xsxk/queryKxrw`

> **Verified on:** 2026-07-04 (but selection rounds NOT configured for Fall 2026)
> **Active semester:** Summer 2026 (`2025-2026/3`)
> **Target semester:** Fall 2026 (`2026-2027/1`) — rounds not yet configured
> **Code:** `sustech_survival.selectcourse.selectcourse.SelectCourseClient.search_personal()`

## Endpoint

```
POST https://tis.sustech.edu.cn/Xsxk/queryKxrw
Content-Type: application/x-www-form-urlencoded
X-Requested-With: XMLHttpRequest
Cookie: route=<ROUTE>; JSESSIONID=<JSESS>
```

## Response shape

On success (`jg: "1"`):
```json
{
  "jg": "1",
  "message": "",
  "kxrwList": {"list": [...], "total": N},
  "yxkcList": [...],         // enrolled courses
  "xkgwcList": [...],        // shopping cart
  "xkgzszList": [...],       // selection rounds config ← KEY
  "xsxkPage": {"xkgzszOne": {...}},  // current active round
  "kbjclist": [...]
}
```

On failure (`jg: "-1"`):
```json
{
  "jg": "-1",
  "message": "操作失败"
}
```

## Critical parameter: `p_xkfsdm` (selection round code)

**This is the single most important parameter.** Unlike `queryRwxxcxList`
(campus-wide catalog) which works for any semester, `queryKxrw` requires
a valid `p_xkfsdm` to know which selection round to query. Without it,
TIS returns `jg=-1, message="操作失败"`.

Each selection round has:
- `xkfsdm`: code (e.g. `"1"`, `"tsbxxk"`, `"pyfanxk"`)
- `xkfsmc`: Chinese name (e.g. `"通识必修选课"`, `"培养方案内课程"`)
- `lcmc`: process name
- `xkms`: selection mode (`"1"`=直选/FFS, `"2"`=志愿/priority)
- `sfkx`: `"1"`=可选, `"0"`=不可选
- `sfkt`: `"1"`=可退, `"0"`=不可退
- `ksrq`/`jsrq`: round date range
- `xkqzsj`: quota per student
- `lbxsxs`: display mode (`"3"`=special layout)

The rounds data (`xkgzszList`) is **embedded in the queryKxrw response**
itself — there is no separate API endpoint to get available rounds.
When queryKxrw returns `jg=1` (success), both the course data AND the
rounds config are in the same response.

## The SPA data-loading flow

The Vue component at `/Xsxk/query/1` loads data in this sequence:

1. **`mounted()` → `Xsxk/queryXkdqXnxq`** — gets current semester info.
   Response: `{p_dqxn, p_dqxq, p_dqxnxq, cxsfmt}`. Sets `p_xn`, `p_xq`
   on the queryform. **NOTE: for Fall 2026, the TIS active semester is
   Summer 2026 (`2025-2026/3`), not Fall 2026.**

2. **`mounted()` → `Xsxk/queryKkxqList`** — gets academic year options
   (学年列表 for dropdown). Returns available semesters per year.

3. **`cxqhquery(sfsccx, pageNum)`** — the core data-loading method.
   Depending on `p_xkfsdm`:
   - `'gouwuche'` → `Xsxk/queryXkgwc` (shopping cart)
   - `'yixuan'` → `Xsxk/queryYxkc` (already enrolled)
   - Anything else → **`Xsxk/queryKxrw`** with all queryform params

## Full queryform shape (40+ keys)

```
p_xn, p_xq, p_xnxq, p_gjz (keyword), p_kc_gjz, p_kcdm_js,
p_kclb (category), p_kkxnxq, p_kkyx (college), p_ksjc (period start),
p_jsjc (period end), p_kxsj_ksjc, p_kxsj_jsjc, p_kxsj_xqj (weekday),
p_pylx (cultivation: 1=本科, 2=研究生), p_sfgldjr, p_sfhlctkc (ignore conflict),
p_sfhllrlkc (ignore zero cap), p_sfmxzj, p_sfredis, p_sfsyxkgwc,
p_sfxsgwckb, p_skjs (teacher), p_skyy (language), p_xiaoqu (campus),
p_xkfsdm (round code — REQUIRED), p_chaxunxkfsdm (same as xkfsdm),
p_xqj, p_xzcxtjz_bj (class group), p_xzcxtjz_nj (grade year),
p_xzcxtjz_yx (college), p_xzcxtjz_zy (major), p_xzcxtjz_zyfx (specialization),
pageNum, pageSize
```

**Gotcha — p_xkfsdm and p_chaxunxkfsdm are typically sent with the same
value.** The TIS JS sets both from `this.queryform.p_xkfsdm`.

## Known selection round types (per user, historical)

| Type | Description | Endpoint |
|---|---|---|
| 已选 | Already enrolled (built-in tab) | `queryYxkc` (separate) |
| 购物车 | Shopping cart (built-in tab) | `queryXkgwc` (separate) |
| 通识必修选课 | General compulsory | `queryKxrw` with xkfsdm |
| 通识选修选课 | General elective | `queryKxrw` with xkfsdm |
| 培养方案内课程 | Within training plan | `queryKxrw` with xkfsdm |
| 非培养方案内课程 | Outside training plan | `queryKxrw` with xkfsdm |
| 重修选课 | Retake selection | `queryKxrw` with xkfsdm |

**Round codes (xkfsdm) are generated per semester by TIS admin.** The
exact codes for Fall 2026 are unknown because rounds haven't been
configured yet.

## Why queryKxrw returns "操作失败" (jg=-1)

**Re-checked 2026-07-06 against the live 2026 fall selection window** (a student with jffs=155.0,
xkfsdm=bxxk verified working — `referenced/credit-based-selection.md` in `sustech/tis/`).
Cause ordering updated:

1. **Missing or invalid payload fields.** This is the most common cause in active
   selection windows. `queryKxrw` requires the FULL xsxk JS bundle payload — the smaller
   payload (just `p_xn/p_xq/p_xkfsdm` + a handful of filters) is not enough. Required:
   - `p_sfsyxkgwc: "1"` — 是否使用选课购物车
   - `p_sfxsgwckb: "1"` — 是否显示购物课表
   - `p_sfmxzj: "0"` — 满足性自荐 flag
   - `cxsfmt` — from `Xsxk/queryXkdqXnxq` round-trip
   - `p_dqxn`, `p_dqxq`, `p_dqxnxq` — current TIS active term, also from `queryXkdqXnxq`

   Verified all 5 are required; missing ANY returns 操作失败 even when rounds ARE
   configured and `xkfsdm` is correct. (Earlier doc versions listed "no active selection
   round" first — that was the dominant cause when rounds hadn't been configured for
   a new term; with rounds live, the missing-fields cause is more frequent.)

2. **No active selection round.** TIS admin must configure rounds (`xkgzszList`
   non-empty) for the queried semester.

3. **Missing or invalid `p_xkfsdm`.** Even when rounds exist, omitting `p_xkfsdm`
   or passing an invalid code will fail. The value must match an entry in `xkgzszList`.

4. **Rate limiting.** Multiple rapid requests → `message="查询请求频率过高 请稍后重试！"`
   Add 2-3s delay.

The reference impl is `sustech_survival.selectcourse.SelectCourseClient.search_personal()`
which builds the 40+ key queryform with the `queryXkdqXnxq` round-trip and is the source
of truth for "what TIS accepts".

## Check current TIS semester state

```python
from sustech_survival.sso import TISAuth
auth = TISAuth()
auth.ensure()
r = auth.session.post("https://tis.sustech.edu.cn/Xsxk/queryXkdqXnxq",
    data={"p_xn": "", "p_xq": ""},
    headers={"X-Requested-With": "XMLHttpRequest"}, timeout=15)
d = r.json()
print(d["p_dqxn"], d["p_dqxq"])  # e.g. "2025-2026", "3" = Summer 2026
```

## Code reference

- `sustech_survival.selectcourse.selectcourse.SelectCourseClient.search_personal()`
- `sustech_survival.webui.blueprints.tis.api_courses()`
- Web UI: `tis.html` — `populateRoundSelect()` function

## Personal-mode filter params: send CODES, not display names (verified 2026-07-07)

The `/api/tis/courses?mode=personal` endpoint's filter params hit TIS
servers that expect **TIS internal codes**, NOT the display names that
appear in the dropdown UI. Sending the display name gives 0 results
silently. Verified one-by-one against `p_kkyx=020020` vs
`p_kkyx=材料科学与工程系`:

| Param | Display name (DOESN'T work) | Code (works) | Source |
|---|---|---|---|
| `p_kkyx` (college) | `材料科学与工程系` returns 0 | `020020` returns 20 | TIS dropdown shows `020020/材料科学与工程系`; the code is what the API expects |
| `p_skyy` (language) | `英文`/`双语` returns 0 | `2` = 英文, `3` = 双语 | Verified by trial; `1`=中文 assumed |
| `p_xiaoqu` (campus) | `一期校区` returns 0 | `1` returns all (no-op filter — only 1 campus exists) | — |
| `p_kclb` (category) | `专业选修课` returns 0 | unknown codes | NCES scraper doesn't expose `kclbdm` — would need a new `/api/tis/info` field |
| `p_skjs` (teacher) | `王海鸥` returns 4 (works!) | name form works | TIS does substring match on teacher |
| `p_gjz` (keyword) | (any string works) | — | substring match |

`/api/tis/info` only returns the display names (colleges, languages,
categories). The college dropdown IS exposed as `[(code, name), ...]`
because the catalog data carries `kkyx` + `kkyxmc`. The other filter
dropdowns only have names — need a code lookup at the webui level.

**The webui fix** for personal mode: maintain a `COLLEGE_MAP = {name → code}`
client-side, populated from `d.colleges` (which IS `[(code, name), ...]`).
For language: `LANGUAGE_MAP = {'中文': '1', '英文': '2', '双语': '3'}`
hardcoded (3 values, no TIS API to discover codes from). For category:
unfixable without exposing `kclbdm` in `/api/tis/info`.

**Campus mode (search_campus) doesn't have this bug** — the catalog
filtering is done client-side (in `selectcourse.py:search_campus`),
substring-matching the display name. Only the personal-mode call to
`Xsxk/queryKxrw` is affected.

**Why this only matters when personal-mode works**: The user's TIS
account has selection rounds ACTIVE for 2026-2027 Fall (`jg=1`),
so `search_personal` reaches TIS and the code-vs-name distinction
actually fires. When rounds are closed (`jg=-1, 操作失败`), the bug
is invisible — TIS rejects everything before the filter check.

## xkfsdm code-name mapping: populate from TIS, never hardcode (verified 2026-07-07)

The `xkgzszList` (selection rounds config in `/api/tis/course-types`
or `queryYxkc`) maps `xkfsdm` (code) → `xkfsmc` (display name). The
webui's Type dropdown shows the Chinese name to the user; when picked,
the JS sends the corresponding code. **DO NOT hardcode** a code →
name mapping — always populate from `/api/tis/course-types` so the
mapping stays correct even when TIS renames codes.

Verified mapping (read from live TIS via `/api/tis/course-types`):
- `bxxk` → 通识必修选课
- `xxxk` → 通识选修选课
- **`kzyxk` → 培养方案内课程** (in-你的培养方案)
- `zynknjxk` → 非培养方案内课程 (out-of-plan courses, e.g. 任意选修)
- `cxxk` → 重修选课

Verified by running `xkfsdm=kzyxk&college=020020` (20 MSE courses)
vs `xkfsdm=zynknjxk&college=020020` (3 MSE courses). The user's
claim "MSE + 培养方案内课程 gives nothing" was the wrong question —
it's the OPPOSITE of what they expected: 培养方案内课程 should
give MORE courses (including ones taught by other departments
that MSE students have to take), but the filter was hitting the
"courses by 开课=MSE intersect plan=any" set, which TIS returns as
20 for MSE plan courses vs 3 for non-plan MSE courses.

**Lesson** (skippable next time): when the user provides a saved
HTML page (`南方科技大学教学管理与服务平台_files.zip` in this case)
that documents a UI they're debugging, READ IT FIRST before guessing.
The dropdown values in the actual page DOM (`<li class="ivu-select-item">
培养方案内课程</li>`) are display labels; the `xkfsdm` in the
surrounding data is what TIS expects. I previously remembered a
mapping from a hand-grep that turned out to be inverted relative to
the actual UI labeling.


