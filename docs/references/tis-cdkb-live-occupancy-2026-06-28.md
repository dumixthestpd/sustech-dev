# TIS 场地课表 (cdkb/querycdkbList) — Live room schedule discovery walkthrough

> **Session context.** 2026-06-28, while investigating the
> "TA bookings are invisible" hypothesis from
> `sustech-dev/SKILL.md` §2. User said: "TIS tells you all, if you
> fill in the expected number of people and the time, you can click
> search and there is a button for you to click on called 选择场地
> and it shows the window after you click. then the search is kind
> of like the search in courses. after you classify what type of
> facility you want, it shows the corresponding rooms and places
> available." After the initial brute-probe failed, the user
> followed up: "do not guess endpoints. i can't stress that more.
> live occupancy probably is the equivalent of converting the
> current time to a tis acceptable format and search for available
> rooms. continue building." This document captures the corrected
> approach.

## TL;DR

The TIS room-search dialog (选择场地) loads the `inco.component.didian`
bundle. That bundle's parent dialog uses a CHILD component
(`inco-i-changdikebiao`) to render the schedule grid. The child
component's `mounted()` hook POSTs to `cdkb/querycdkbList` — and that
endpoint returns BOTH registered courses AND ad-hoc borrowings
(借用) with borrower name + phone. This is the per-room live schedule
data source that the previous "TA bookings invisible" hypothesis
incorrectly ruled out.

**Pattern:** when a component uses a child component, the child
usually has the more specific data endpoint. Don't stop at the
parent's endpoint.

## What was previously wrong

The dead-end note from 2026-06-15 (in `ehall-booking-venue-2026-06-15.md`)
claimed:

> "TIS does NOT have a venue/场地预约 API reachable from a student
> session (brute-probed /student/venue*, /student/apply*, /student/room*,
> /student/classroom*, plus Spring-style controller paths — all 404).
> The user may be conflating TIS with ehall. Do not re-walk this
> dead end."

And the architectural notes from 2026-06-28 had:

> **Hypothesis for 教学楼 ad-hoc booking:** the backend is likely a
> server not exposed to the public internet — possibly campus-internal
> only, possibly admin-role-gated. We are unlikely to get direct
> backend access without an insider (教务处 / 教学调度 staff) or a TA
> test account.

**Both wrong.** The data IS in TIS, in the `cdkb` (场地课表) table.
It's not admin-gated, not internal — it just lives behind a Vue
component that isn't loaded on the standard student pages.

## The corrected walkthrough

### Step 1: Follow the user's hint literally

User said "TIS tells you all" with a specific UI flow:
1. Fill in number of people + time
2. Click "查询" (search)
3. A dialog opens with title "选择场地"
4. After filtering by facility type, available rooms show up

So the action lives in a dialog, not on the main catalog page. Find
the dialog component.

### Step 2: Find the dialog component

The dialog is on the `/Xsxk/query/1` page (selectcourse). Walk all
99 JS bundles loaded by that page and grep for the keywords from
the user's hint:

```bash
cd ~/.openclaw/code/sustech_survival
python3 -c "
import sys, json, re; sys.path.insert(0, 'src')
import requests
from sustech_survival.sso import UA
# ... (load TIS session cookies) ...
r = requests.get('https://tis.sustech.edu.cn/Xsxk/query/1', ...)
scripts = sorted(set(re.findall(r'src=\"([^\"]*\.js[^\"]*)\"', r.text)))
# download each and grep for venue keywords
for s in scripts:
    if not s.startswith('/'): continue
    bundle = requests.get(f'https://tis.sustech.edu.cn{s}',
                          headers={'Referer': '.../Xsxk/query/1'}).text
    if any(kw in bundle for kw in ['选择场地', '场地类别', 'jslx', '座位']):
        print(s)
"
```

Output:
```
/component/inco/inco.component.didian-3aebf9cf5bcb3e5f3d601411e4e67d5a.js
```

### Step 3: Read the dialog bundle

Save the bundle:
```bash
curl -s 'https://tis.sustech.edu.cn/component/inco/inco.component.didian-3aebf9cf5bcb3e5f3d601411e4e67d5a.js' \
     -H 'Referer: https://tis.sustech.edu.cn/Xsxk/query/1' \
     -b /tmp/tis-cookies.txt \
     -o /tmp/didian_bundle.js
```

Grep for endpoints:
```bash
grep -oE 'baseUrl\s*\+\s*["\047]([^"\047]+)["\047]' /tmp/didian_bundle.js | sort -u
```

Output:
```
baseUrl + cdkb/querycdkbList              # <-- the per-room schedule endpoint
baseUrl + component/queryDiDian          # the search endpoint
baseUrl + component/queryTeacherDefValue
baseUrl + component/queryXiaoqu?pylx=
```

**Found 4 endpoints, not 1.** The `cdkb/querycdkbList` was buried
in the chain but I almost missed it because I was focused on the
`component/queryDiDian` (the search) endpoint.

### Step 4: Read the schedule grid component

`didian` (the dialog) renders a schedule grid in its footer:
```html
<inco-i-changdikebiao v-if="kebiaoisshow"
                       :xn="sysj[0].xn" :xq="sysj[0].xq"
                       :cddm="cddm" :sj="sysj"></inco-i-changdikebiao>
```

`inco-i-changdikebiao` is a SEPARATE component. The schedule data
endpoint (`cdkb/querycdkbList`) is called from this CHILD
component's `mounted()`:

```js
mounted: function() {
    var self = this;
    $.post(baseUrl + 'cdkb/querycdkbList',
           {cddm: this.cddm, xn: this.xn, xq: this.xq},
           function (res) { ... self.sksjdata = res; ... });
}
```

### Step 5: Test the endpoint

```python
url = 'https://tis.sustech.edu.cn/cdkb/querycdkbList'
r = sess.post(url, data={'cddm': 'YJ-123', 'xn': '2025-2026', 'xq': '2'},
              headers={'RoleCode': '00'}, timeout=30)
data = r.json()
# data is a list of schedule entries:
# [
#   {"KCDM": "jy",
#    "SKSJ": "【借用】[<week>]\n使用人:<borrower>\n联系电话:<phone>",
#    "SKSJ_EN": "招生活动",
#    "XB": 19,
#    "KEY": "xq7_jc6"},
#   ...
# ]
```

**106 entries for YJ-123 (一教123) in Spring 2026:**
- 77 borrowings (借用) — recruitment events, robot-club meetings,
  weekend class pre-locks, holiday make-up bookings
- 26 registered courses
- 3 metadata entries (room info, etc.)

**This is the live occupancy data.** The user's hypothesis was wrong:
TA bookings, study groups, recruitment events are all in TIS, in
the `cdkb` table, accessible to student sessions.

### Step 6: Parse the data

The schedule entry shape is documented in the
`classroom/live.py:RoomScheduleEntry` dataclass. Key fields:
- `KEY` — `xq{W}_jc{P}` (weekday + period slot in the grid)
- `SKSJ` — Chinese schedule text. Two formats:
  - Borrowings: `【借用】[<week>]\n使用人:<borrower>\n联系电话:<phone>`
  - Courses: `【本/研/研本】COURSE_NAME[TEACHER][GROUP][N周][J1-J2节]`
- `SKSJ_EN` — purpose / description (Chinese or English)
- `XB` — internal sequence number
- `KCDM` — course code, or `'jy'` for 借用

The week(s) are encoded in the SKSJ text as `[N周]`,
`[N1-N2周]`, or `[N1,N2,...周]`. Parse with a regex.

## The `sysj` shape — the gotcha that was biting us

The didian bundle's `query()` method passes a `sysj` parameter to
the API. From the comment in the bundle:

```js
/*
* [
*  {
*   xn:'2017-2018',
*   xq:'1',
*   xqj:'1',
*   ksjc:'1',
*   jsjc:'2',
*   zc:'11111111111111110000000000000000'
*  }
* ]
* */
```

`sysj` is a LIST OF DICTS, each with:
- `xn` — academic year
- `xq` — weekday (1-7) — **NOT semester, despite the same name**
- `xqj` — also weekday (duplicate field, may be vestigial)
- `ksjc` — start period (1-12)
- `jsjc` — end period (1-12)
- `zc` — **34-char week bitmask**, NOT a single week number

**Gotcha:** Spring binds this as `sysj[0].xc`, `sysj[0].xq`, etc.
NOT as a JSON-stringified list. If you POST
`sysj=[{"zc":"1"}]` as a single string, Spring returns:
```
{"code":200,"msg":"org.springframework.validation.BeanPropertyBindingResult: 1 errors
Field error in object 'diDianPage' on field 'sysj': rejected value [[{...}]];
codes [typeMismatch.diDianPage.sysj,typeMismatch.sysj,typeMismatch.java.util.List,...]; ..."}
```

The fix: use Spring's indexed-access form:
```python
params = [
    ('sysj[0].zc', '1111111111111111111111111111111111'),  # all weeks
    ('sysj[0].xn', '2025-2026'),
    ('sysj[0].xq', '2'),
    # ... other params
]
```

**This is what was blocking earlier attempts to call
`queryDiDian`:** the brute-probe tests sent wrong params, got
`typeMismatch` errors, and concluded the endpoint was rate-limited
or had a different shape. The shape is in the bundle — read it.

## Other endpoints in the same dialog

- `POST /component/queryCdlb` — 场地类别 (venue categories) — single
  dict, not paginated. Returns the dropdown options for `jslx`
  filter (多媒体教室, 实验室, 讨论型教室, 计算机房, 体育馆, etc.).
- `POST /component/queryXiaoqu?pylx=N` — 校区 (campuses) — returns
  the campus list filtered by training type. `pylx=1` (undergrad)
  returns 一期校区 + 二期校区 + 九祥校区.
- `POST /component/dq_xnxq` — current academic year + semester.
  Returns `{XN: '2025-2026', XQ: '2'}`.

## Room codes — what works and what doesn't

Verified by querying the per-room schedule with various codes
(2026-06-28, Spring 2026, 一期校区):

| Building | Code prefix | cdkb entries |
|---|---|---:|
| 一教 | `YJ-XXX` | 53-117 (varies by room) |
| 智华楼 | `ZH-XXX` | 134-151 |
| 三教 | `LH3-XXX` | **0** (not in cdkb) |
| 工学院 | `GC-XXX` | 0 |
| 理学院 | `LX-XXX` | 0 |
| 商学院 | `SS-XXX` | 0 |

**三教 rooms return 0 entries.** Either (a) the schedule isn't
populated for those rooms this semester, or (b) they use a
different internal code. Not yet investigated.

## What this means for the `classroom` module

- **Read side:** complete — `queryDiDian` gives all 421 rooms.
- **Live occupancy side:** complete — `cdkb/querycdkbList` per
  room gives the actual schedule (courses + borrowings) for
  any (week, weekday, period).
- **Implementation:** `src/sustech_survival/classroom/live.py` —
  `LiveOccupancyClient`, `RoomScheduleEntry`, `parse_sksj`,
  `parse_key`, `current_semester`, `current_weekday_and_period`.
  Wired into `ClassroomOccupancy` via `live_entries_for_name`,
  `live_occupancy`, `live_occupancy_at`,
  `live_rooms_occupied_at`, `live_rooms_free_at`.
- **Tests:** `src/test/test_classroom_live.py` — 32 offline tests
  (parsers, dataclass, mocked client) + `@pytest.mark.live`
  for actual server runs. All 32 offline + 34 existing
  schema tests pass.

## Lessons learned

1. **Don't stop at the first endpoint you find.** When a component
   uses a child component, the child usually has the more
   specific data endpoint.

2. **The bundle is the source of truth for param shapes.** Spring
   binding quirks (indexed access, name collisions between
   top-level and nested fields, list-of-dict vs flat dict) are
   all visible in the bundle source. Don't guess.

3. **User hints are usually right.** When the user said "TIS tells
   you all" with a specific UI flow, that was a direct pointer to
   the dialog. Initial attempts to brute-probe or read the wrong
   bundle were off-target. Following the hint led to the right
   bundle in one step.

4. **The dead-end note was wrong.** A 2026-06-15 reference said
   "TIS does NOT have a venue/场地预约 API reachable from a
   student session." That was based on a brute-probe of guessed
   paths. The endpoints ARE there, just behind a dialog. The
   new walkthrough supersedes the dead-end note for the
   教学楼 case.

## See also

- `references/spa-js-bundle-walk-recipe.md` — the recipe this
  walkthrough followed. Includes the "follow the chain" pattern
  and the "don't brute-probe" anti-pattern.
- `references/tis-didian-room-search-2026-06-28.md` — sister
  walkthrough for the parent dialog's endpoint
  (`queryDiDian`). That endpoint is the SEARCH side; this
  document is the LIVE SCHEDULE side.
- `sustech-dev/SKILL.md` §4 — the broader investigation plan and
  resolution.
- `sustech/classroom/SKILL.md` — the user-facing docs for the
  classroom module, with the live CLI commands.
- `src/sustech_survival/classroom/live.py` — the implementation.
- `src/test/test_classroom_live.py` — the tests.
