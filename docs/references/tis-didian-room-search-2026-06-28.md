# TIS 选择场地 / queryDiDian — full walkthrough (2026-06-28)

> Session-specific detail. The endpoint catalog entry in `SKILL.md`
> has the high-level summary; this file is the **reproduction recipe
> + technique bank** for any future agent doing the same kind of
> SPA-bundle walk on a TIS sub-page.

## Trigger

User hint: "TIS tells you all, if you fill in the expected number of
people and the time, you can click search and there is a button for
you to click on called 选择场地 and it shows the window after you
click. then the search is kind of like the search in courses. after
you classify what type of facility you want, it shows the
corresponding rooms and places available."

Translation: there's a search/select dialog embedded in TIS — not a
separate system. Same `Xsxk/query/1` page that loads the selectcourse
write side also loads the 选课排课 room-search dialog.

## Walk steps (the recipe)

1. **Find the right page.** TIS main (`/authentication/main`, 148KB)
   has 24 scripts, none with venue/room. `/student_index` (70KB) has
   19 links, no venue. **`/Xsxk/query/1` (130KB)** has 101 scripts —
   the dense Vue SPA where the action buttons live. This is the same
   page where `selectcourse` write side was found
   (2026-06-19). Both features (catalog browse + room search) load
   on the same page because they're both part of the
   选课排课 (course scheduling) flow.

2. **Find the right bundle.** Grep all 99 inco.component bundles on
   the page for venue-related keywords:
   ```python
   for s in scripts:
       if not s.startswith('/'): continue
       bundle = sess.get(BASE + s, headers={'Referer': REFERER}).text
       if '场地' in bundle and '座位' in bundle and '选择场地' in bundle:
           print(s)
   # → /component/inco/inco.component.didian-3aebf9cf5bcb3e5f3d601411e4e67d5a.js
   ```
   The Vue component is `inco-i-select-didian-modal` (选择地点模态框
   = Select Venue Modal). Title: "选择场地". 30KB, has 34-char
   `kxzc` bitmask logic.

3. **Extract endpoints.** Grep for `baseUrl + 'path'` patterns:
   ```python
   re.findall(r'baseUrl\s*\+\s*["\']([^"\']+)["\']', bundle)
   ```
   Found 4 endpoints in didian + 1 in cdlb + 1 in xnxq:
   - `cdkb/querycdkbList` — venue schedule (per cddm)
   - `component/queryDiDian` — **the room-search endpoint**
   - `component/queryTeacherDefValue` — teacher default
   - `component/queryXiaoqu?pylx=` — campus lookup
   - `component/queryCdlb` — venue categories
   - `component/queryXnxqCdjy` — academic year/semester for cdjy

4. **Download with `Referer` + session cookies** (Tengine blocks
   bare curl with 403). Reuse the Session that did the CAS login —
   `JSESSIONID` + `route` are required.

5. **Brute-probe write-side endpoints.** Walk all 99 bundles for
   `add|save|submit|book|reserve|apply|cdyy|cdba|cdtj` → found
   ZERO. The dialog is search-only.

## Technique: Spring binding for `List<Map>` via indexed params

The endpoint accepts a `sysj` list (使用时间 = usage-time slots).
**Naive** JSON-string binding fails with Spring
`Failed to convert property value of type 'java.lang.String' to
required type 'java.util.List'`. The fix is Spring's indexed-access
binding syntax:

```python
# NOT this (Spring refuses — single string can't convert to List<Map>):
params = [('sysj', '[{"zc":"1","xq":"1","jc":"3-4"}]')]

# This works (Spring's array binding):
params = [
    ('sysj[0].zc', '1'),
    ('sysj[0].xq', '1'),
    ('sysj[0].jc', '3-4'),
    # Add sysj[1]... for more slots
]
```

Generalization: any Spring backend with a `List<MyObject>` request
param takes `param[0].fieldA=...&param[0].fieldB=...` form
encoding, NOT a JSON-string-of-list. Same pattern for `Map` fields:
`param[0].subfield=value`. This shows up on TIS, ehall, and any
other Spring + Vue/jQuery stack at SUSTech.

## Technique: TIS `RoleCode` header (any value works)

The endpoint returns `Required request header 'RoleCode' for method
parameter type String is not present` if the header is missing.
Verified: any non-empty string (`'00'`, `'xs'`, `'<sid>',
`'student'`, `''`) produces a successful response. The server
checks **presence**, not value. (TIS's main page sets
`var RoleCode='00'` as the default global. The
`data-rolecode` iframe attribute is the per-user override path,
but the catalog endpoints don't actually validate against it.)

**Practical:** always send `headers={'RoleCode': '00'}` on TIS
endpoints that complain. Don't waste time trying to discover the
"correct" RoleCode.

## Pitfall: TIS `pageSize` cap = 100 (not 500)

Other TIS endpoints (`Xsxktz/queryRwxxcxList`) accept pageSize=500.
`queryDiDian` does **NOT** — Spring returns HTTP 200 with
**empty body** at pageSize ≥ ~150. Confirmed: pageSize=200 returns
0 bytes; pageSize=100 returns 50/421 rooms per page; total fetch
across 9 pages works. This is silently a TIS feature
(throttling) but only some endpoints have it. **If a TIS endpoint
returns 200 + empty body, halve the pageSize and retry.**

## Pitfall: TIS empty body = rate-limited OR session timed

Multiple times during the probe, an endpoint that worked 30s ago
suddenly returned 200 + 0 bytes. Two causes:
1. **pageSize too large** (above) — halve it.
2. **Session timed out / rate-limited** — re-login via CAS
   (hand-rolled `_tis_login()` to bypass the py3.12
   `LegacyAdapter` urllib3 bug) and add a 1-3s sleep between
   pages. The CAS login refreshes JSESSIONID + route cookies,
   and the empty-body error goes away.

## The endpoint (canonical)

```
POST https://tis.sustech.edu.cn/component/queryDiDian
Headers:
  Cookie: JSESSIONID=...; route=...; TGC=...
  RoleCode: 00  (any non-empty value; server only checks presence)
  Content-Type: application/x-www-form-urlencoded
  X-Requested-With: XMLHttpRequest
Body (form-encoded):
  sysj[0].zc=1           # week 1-18
  sysj[0].xq=2           # weekday 1-7
  sysj[0].jc=3-4         # period string "1-12" or "3-4"
  sysj[0].xn=2025-2026   # optional
  sysj[0].xq=2           # NOTE: same name as weekday — Spring binds by position
  xn=2025-2026
  xq=2
  pylx=1                 # 1=undergrad, 2=grad, 3=both
  xiaoqu=1               # 1=一期, 2=二期, 9=九祥
  jxl=                   # building code (empty=any)
  jslx=                  # venue category (empty=any)
  lc=                    # floor (empty=any)
  kkyx=                  # department (empty=any)
  key=                   # keyword (empty=any)
  zws=0                  # required seat count
  kszws=0                # required exam seat count
  sfjtjs=2               # 阶梯教室: 2=any, 1=yes, 0=no
  zysfkyd=2              # 座椅可移动: 2=any, 1=yes, 0=no
  hlct=0                 # 忽略冲突: 0=no, 1=yes
  hltyxct=0              # 允许同院系时间冲突: 0=no, 1=yes
  sybm=                  # 使用部门
  mxid=[]                # array of related IDs
  ttbkid=                # teaching task book ID
  bjrs=0                 # 不计人数: 0/1
  sfxsyxzws=0
  yqzws=0
  yqkszws=0
  yxzws=0
  yxkszws=0
  pageNum=1
  pageSize=100           # MAX 100
```

**Minimal payload that returns 421 rooms** (verified):

```python
params = [
    ('sysj[0].zc', '1'),
    ('sysj[0].xn', '2025-2026'),
    ('sysj[0].xq', '2'),
    ('xn', '2025-2026'),
    ('xq', '2'),
    ('pylx', '1'),
    ('hlct', '0'),
    ('hltyxct', '0'),
    ('sfjtjs', '2'),
    ('zysfkyd', '2'),
    ('jslx', ''),
    ('xiaoqu', '1'),
    ('lc', ''),
    ('kkyx', ''),
    ('key', ''),
    ('sybm', ''),
    ('mxid', '[]'),
    ('sfxsyxzws', '0'),
    ('yqzws', '0'),
    ('yqkszws', '0'),
    ('yxzws', '0'),
    ('yxkszws', '0'),
    ('bjrs', '0'),
    ('zws', '0'),
    ('kszws', '0'),
    ('pageNum', '1'),
    ('pageSize', '100'),
]
```

**Reduced payloads return empty 200** (Spring binding requires
explicit values for fields that the dialog passes). If you see
empty body, the payload is too thin — pad it.

## Response shape (real example)

```json
{
  "total": 421,
  "list": [{
    "dm": "LH1-107", "mc": "一教107", "mcEn": null,
    "lhdm": "01", "xiaoqu": "1", "lc": "1",
    "cdlb": "02", "lbmc": "多媒体教室",
    "zws": "165", "kszws": "0",
    "sfjtjs": "0", "zysfkyd": "0",
    "kxzc": "1111111111111111111111111111111111",
    "kgzt": "1", "sfct": "0",
    "jxlmc": "一教", "xiaoqumc": "一期校区",
    "sfljkc": "0", "ssyzx": null, "syzx": null,
    "tplj": "/upload/cdshow/LH1-107.jpg"
  }, ...]
}
```

## What `kxzc` ACTUALLY means (this is the trap)

`kxzc` is a 34-char string of `0`/`1` chars. **It is NOT live
occupancy.** It is the room's *configuration* — which periods the
room is configured to be open for. A room with no evening hours
has `kxzc=1111111111111111111100000000000000` (last 16 = closed).

The dialog's client-side JS:
```js
ee.kxzc = (BigInt('0b'+kxzcfw) & BigInt('0b'+ee.kxzc)).toString(2)
ee.qsjsz = $qsjsz(ee.kxzc.padStart(34, 0))
```
ANDs the room's `kxzc` with the user's filter (`kxzcfw`, default
all 1s), then calls `$qsjsz` (起始教室计算) to figure out which
periods are available. **Then** the user schedule is overlaid
client-side from the user's own `xszykb` data.

**Therefore**: the API does NOT return live occupancy. `sfct`
(=是否冲突, "has conflict") is also a client-side computation,
**not** a server flag. If a future agent assumes `sfct=1` means
"this room is taken right now," they'll be wrong. It's "this
room conflicts with the querying user's existing schedule," which
for a query with no specific user context is always 0.

## What we found that's useful

| Finding | Value |
|---|---|
| Full SUSTech room inventory (一期校区) | **421 rooms** |
| 教学楼 with classrooms | 一教 74, 三教 56, 智华楼 56, 工学院 42, 理学院 26, 二教 2, … |
| 房间类别 | 171 实验室, 154 多媒体教室, 26 讨论型教室, 22 计算机房, 16 其他, sports facilities |
| Booking WRITE endpoint | **NONE.** The dialog is search-only. |
| `kxzc` = live occupancy? | NO. It's the room's open-period config. |

## Reusable patterns for other TIS sub-pages

- **Page discovery:** start with `/Xsxk/query/1` (130KB, 101 scripts)
  if the feature involves scheduling, rooms, courses, or teachers.
  Start with `/authentication/main` (148KB, 24 scripts) for global
  UI. Start with `/student_index` (70KB) for student-dashboard stuff.
- **Bundle walk:** `grep -lE '(venue|room|场所|venue|classroom|cd|js)'`
  on all `/component/inco/*.js` bundles; the chosen bundle will have
  the keyword density of the feature (e.g. didian has 8× 场地 +
  13× 座位 + 2× 选择场地).
- **Endpoint extraction:** `re.findall(r'baseUrl\s*\+\s*["\']([^"\']+)["\']', bundle)`
  catches the canonical pattern. `re.findall(r'\.post\(["\']([^"\']+)["\']', bundle)`
  catches inline URL strings.
- **Form shape:** `re.findall(r'param\.(\w+)', bundle)` and
  `re.findall(r'v-model="param\.(\w+)"', bundle)` give the field
  list. `re.findall(r'@click="(\w+)"', bundle)` gives the action
  methods whose bodies are in the same file.

## Connections to other sustech-dev catalog entries

- Same family of TIS-read endpoints as `queryRwxxcxList` (course
  catalog) and `queryKbjg` (period timing). All three are TIS
  course-scheduling read endpoints that work via the same
  TIS-CAS + JSESSIONID + route cookie + `RoleCode: 00` pattern.
- The `selectcourse` write side (`Xsxk/addXuanke`,
  `Xsxk/tuike`) was found the same way on the same page — see
  `references/selectcourse-write-side-2026-06-19.md` in the
  legacy shim skill. Walking `/Xsxk/query/1` bundles is now a
  **proven recipe** for finding TIS endpoints hidden from the
  menu HTML.
