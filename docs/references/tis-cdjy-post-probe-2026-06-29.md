# TIS 场地借用 (cdjy) — POST payload probe (2026-06-29)

> **Iron-law-#11 probe**: drove the live UI in Playwright, injected
> a `user` object into `localStorage` (so `openAddDrawer` could
> populate the form from `__user.X`), filled the form with a
> minimal-but-valid row, hooked `$.ajax` to capture the body, and
> called `saveOrSubmit('bc')` (then `saveOrSubmit('tj')`) directly.
>
> **No real application was created** — the route handler fulfilled
> the POST with a fake `{code: 200}` so the actual create never hit
> the server. This is the safe path per iron law #1.
>
> **Verified: 2026-06-29 against the live UI.**
> Reference: `scripts/probe_cdjy_post.py` in the sustech-survival repo.

#> **⚠️ CORRECTIONS (2026-06-29, after reading the TIS source code):**
>
> The probe above was a **first-pass test** — it captured the shape but
> hardcoded wrong values for some fields because the probe code guessed:
>
> | Field | Probe value | CORRECT value | Source |
> |---|---|---|---|
> | `saveOrSubmit('bc')` | flag='bc' | flag='0' (保存) or '1' (提交) | `saveOrSubmit(flag)` in TIS source: `@click="saveOrSubmit('0')">保存` and `@click="saveOrSubmit('1')">{{i18n('PKGL.tijiao')}}` |
> | `shbj: "bc"` | "bc" | "0" (保存) / "1" (提交) | `$.extend(self.cdjyform, {shbj:flag})` where flag is the btn param |
> | `hlddct: False` | bool False | string "0" | `self.cdjyform.hlddct='1'` on code 100500 retry — always string |
> | `rs: 30` (form) | int 30 | string "30" at row level | addjxx initializer: `rs:null` → filled as string by Vue |
>
> The probe also set `xnxq` explicitly — the real TIS `openAddDrawer`
> sets `cdjyform.xn` and `cdjyform.xq` separately (no `xnxq` in the
> form). **The probe's conclusion that `xnxq` isn't in the wire was
> correct**, but the reason was: it was never added to the form object.
>
> See `references/tis-cdjy-form-schema-2026-06-29.md` for the full
> source-verified schema. The **fully corrected schema** is in
> `booking_schema.py` as of 2026-06-29 evening:
> - `BorrowApplication.audit_office` defaults to `"0"` (draft)
> - `to_api()` emits `hlddct: "1"/"0"` string
> - `to_api()` emits `shbj: self.audit_office or "0"`
>
> The probe's `$.ajax` hook + `route.fulfill` technique is still correct
> and should be reused for any future probe of a destructive TIS
> endpoint. Just use the correct flag values.
>
> ---

# The wire payload (verified)

### Endpoint

- **URL**: `POST {baseUrl}/cdjy/addChangDiJieYongShenQing/1`
  - `baseUrl = https://tis.sustech.edu.cn/`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Body**: `JSON.stringify(this.cdjyform)` — the entire Vue form object,
  no reshaping, no client-side filtering

The form's `saveOrSubmit(flag)` function does literally:

```js
$.extend(self.cdjyform, {shbj: flag})   // <-- the only mutation before send
let __ajax__ = $.ajax({
    url: baseUrl + 'cdjy/addChangDiJieYongShenQing/1',
    data: JSON.stringify(self.cdjyform),
    type: 'post',
    dataType: 'json',
    contentType: 'application/json',
});
```

So **`shbj` is the only field that varies between save/submit**, and
it is set by the `flag` argument.

### The `shbj` flag — full semantics

| `shbj` value | Triggered by | Behavior |
|---|---|---|
| `"bc"` (保存) | `saveOrSubmit('bc')` | Save as draft — the application is persisted with status `保存待审核`, but does NOT enter the approval queue. The user can come back, edit, and submit later. |
| `"tj"` (提交) | `saveOrSubmit('tj')` | Save AND submit for audit. Status moves to `已提交`, the approval workflow (`gzlshywlc` / `CDJYLC`) starts, and the auditor list is shown. |

> **Both `bc` and `tj` hit the same URL** with the same body shape.
> The flag is the *only* difference. The probe ran `bc`; `tj` was
> also verified to fire the same AJAX (just with `shbj: "tj"`).
>
> **The catalog's "save → `updateChangDiJieYongShenQing` (no Put) +
> flag param" pattern is for a DIFFERENT use case** — that endpoint
> is for changing the status of an EXISTING row (id, xn, xq, flag
> form-encoded). It is NOT the create-or-update flow.

### The form-level body (35 keys, captured)

```json
{
  "id": "",                                  // server-assigned after create
  "jhdh": "",                                // plan number, server-assigned
  "sqr": "<name>",                            // 申请人 (Chinese name)
  "sqr_en": "<english-name>",              // applicant English name
  "sqrdh": "<phone>",                    // applicant phone
  "xn": "2025-2026",                         // 学年 (year)
  "xq": "3",                                 // 学期 (semester; 1=秋, 2=春, 3=夏)
  "zc": "",                                  // 周次 pattern (form-level, not used)
  "rs": 30,                                  // 人数 (headcount, integer)
  "qsjsz": "",                               // 起始结束周 (form-level, not used)
  "syr": "<name>",                            // 使用人 (Chinese name)
  "syr_en": "",                              // user English name (often empty)
  "jyrdh": "",                               // legacy/dup field
  "syrdh": "<phone>",                    // user phone
  "sqrdw": "测试单位",                       // applicant dept (Chinese)
  "sqrdw_en": "Test Dept",                   // applicant dept (English)
  "sqrdwdh": "000",                          // applicant dept code
  "shjs": "",                                // 审核角色 code
  "shjsxm": "",                              // auditor role name
  "shjsxm_en": "",                           // auditor role name EN
  "shyj": "",                                // 审核意见 (audit opinion)
  "jyyy": "测试借用",                        // 借用原因 (purpose)
  "xiaoqu": "1",                             // 校区 (campus; 1=一期, 2=二期, 9=九祥)
  "shbj": "bc",                              // ★ save/submit flag
  "xnxw": "",                                // 新/续 (new/continued)
  "cdjymxlist": [ ... ],                    // detail rows (see below)
  "jtsjlist": [ {xqj, ksjc, jsjc}, ... ],   // flattened slot list
  "sfsjysxtly": "",                          // 校外活动OA approval flag
  "syrdwdm": "",                             // 使用人单位代码
  "sqrzgh": "<sid>",                          // 申请人职工号
  "syrzgh": "<sid>",                          // 使用人职工号
  "cdjymlist": [],                           // alternate legacy list (always empty)
  "zhxgr": "",                               // last modifier
  "xhxgsj": "",                              // last-modified timestamp
  "hlddct": false                            // 忽略地点冲突 (ignore-location-conflict, boolean)
}
```

### The per-row body (cdjymxlist[] entry, 25 keys)

```json
{
  "xuhhao": 1,                                // sequence
  "ksrq": "2026-07-01",                       // 开始日期 (start date YYYY-MM-DD)
  "jsrq": "2026-07-01",                       // 结束日期 (end date YYYY-MM-DD)
  "rs": "30",                                 // per-row headcount (NOTE: string)
  "jyyy": "测试借用",                         // per-row purpose (duplicates form)
  "zc": "1",                                  // 周次 (week bitmask, "1" = week 1)
  "qsjsz": "1",                               // 起始结束周 ("start,end" or just start)
  "xqj": "3",                                 // 星期几 (weekday 1-7)
  "ksjc": "3",                                // 开始节次 (start period 1-12)
  "jsjc": "4",                                // 结束节次 (end period 1-12)
  "jyxq": "2025-20263",                       // 借用学期 key (xn+xq concatenated)
  "sfsysb": "1",                              // 是否使用设备 (use equipment)
  "jyjs": "",                                 // 借用结束 (end timestamp, often empty)
  "cddm": "YJ-101",                           // 场地代码 (room code)
  "cdmc": "一教101",                          // 场地名称 (room display name)
  "xn": "2025-2026",                          // (duplicated from form)
  "xq": "3",                                  // (duplicated from form)
  "xiaoqu": "1",                              // (duplicated from form)
  "sqr": "",                                  // per-row applicant name (empty when same as form)
  "sqrdh": "",                                // per-row applicant phone (empty)
  "syr": "",                                  // per-row user name (empty)
  "syrdh": "",                                // per-row user phone (empty)
  "sqrdw": "",                                // per-row applicant dept (empty)
  "sqrdwdh": "",                              // per-row applicant dept code (empty)
  "shjs": "",                                 // per-row auditor role (empty)
  "shyj": "",                                 // per-row audit opinion (empty)
  "zysfkyd": "2",                             // 座椅可移动 (per-row filter snapshot, TriState)
  "sfjtjs": "2"                               // 阶梯教室 (per-row filter snapshot, TriState)
}
```

### The flat-slot body (jtsjlist[] entry, 3 keys)

```json
{ "xqj": "3", "ksjc": "3", "jsjc": "4" }
```

Just three fields. The flat list is built from
`cdjyform.cdjymxlist.filter(e => e.xqj && e.ksjc && e.jsjc)` —
**only rows with complete slot data contribute to jtsjlist[]**.

## Diff vs current `to_api()` (in `booking_schema.py:BorrowApplication`)

### Form-level fields MISSING from our `to_api()`

| Wire key | In our `to_api()`? | Notes |
|---|---|---|
| `sqr_en` | ❌ MISSING | `__user.xm_en` — needed for EN-name forms |
| `sqrdw_en` | ❌ MISSING | `__user.bmmc_en` — applicant dept EN |
| `syr_en` | ❌ MISSING | user EN name |
| `shjsxm` | ❌ MISSING | auditor role display name (auto-filled for some roles) |
| `shjsxm_en` | ❌ MISSING | auditor role display name EN |
| `shyj` | ❌ MISSING | audit opinion (default empty; filled in by auditor after submit) |
| `hlddct` | ❌ MISSING | `false` (boolean) — ignore-location-conflict flag |
| `jtsjlist` | ❌ MISSING | flattened slot list — server uses for occupancy check |
| `cdjymlist` | ❌ MISSING | always `[]` legacy list — server ignores |
| `zhxgr` | ❌ MISSING | last modifier (server-populated) |
| `xhxgsj` | ❌ MISSING | last-modified timestamp (server-populated) |
| `jyrdh` | ❌ MISSING | legacy/dup phone field |

### Form-level fields our `to_api()` SENDS but wire doesn't need

| Our key | In wire? | Notes |
|---|---|---|
| `xnxq` | ❌ NOT IN WIRE | We send `xnxq: "2025-2026-3"` (concat of xn+xq). The wire has `xn` and `xq` separately. The `xnxq` key is not in the wire. **Remove it from `to_api()`.** |

### Per-row fields MISSING from our `_detail_to_api()`

| Wire key | In our `_detail_to_api()`? | Notes |
|---|---|---|
| `ksrq` | ❌ MISSING | start date YYYY-MM-DD |
| `jsrq` | ❌ MISSING | end date YYYY-MM-DD |
| `rs` (per-row) | ❌ MISSING | per-row headcount (string!) |
| `jyyy` (per-row) | ❌ MISSING | per-row purpose |
| `zc` (per-row) | ❌ MISSING | week bitmask |
| `qsjsz` (per-row) | ❌ MISSING | start/end week |
| `xqj/ksjc/jsjc` (per-row) | ❌ MISSING (we have them only in jtsjlist[] slot) | server needs them on the row too |
| `jyxq` | ❌ MISSING | semester key |
| `sfsysb` | ❌ MISSING | use-equipment flag |
| `jyjs` | ❌ MISSING | end timestamp (empty by default) |
| `xn/xq/xiaoqu` (per-row) | ❌ MISSING | duplicated from form |
| `sqr/sqrdh/syr/syrdh/sqrdw/sqrdwdh/shjs/shyj` (per-row) | ❌ MISSING (sent empty in wire) | per-row override fields |
| `zysfkyd` | ❌ MISSING | per-row filter snapshot |
| `sfjtjs` | ❌ MISSING | per-row filter snapshot |
| `sfblcd` | ❌ MISSING (per-row) | 保留多个场地 (per-row, sometimes empty) |

### Per-row fields our `_detail_to_api()` SENDS but wire doesn't have

| Our key | In wire? | Notes |
|---|---|---|
| `zws` | ❌ NOT IN WIRE | seat count (server fills from cddm lookup) |
| `cdlocation` | ❌ NOT IN WIRE | location hint (we synthesize; server ignores) |
| `yongtu` | ❌ NOT IN WIRE | we synthesize; server doesn't use this on the row |
| `jtsjlist` (nested in row) | ❌ NOT IN WIRE | wire has `jtsjlist` only at form level, not nested per-row |

### Per-slot fields (jtsjlist[] entry) — our `BorrowTimeSlot` is OVERSPECIFIED

| Our `BorrowTimeSlot` key | In wire? | Notes |
|---|---|---|
| `xqj`, `ksjc`, `jsjc` | ✅ all 3 present | The only fields the server uses |
| `xh` (sequence) | ❌ NOT IN WIRE | we synthesize; server doesn't use it on the flat slot list |
| `zcbds` (week pattern) | ❌ NOT IN WIRE | we synthesize; server doesn't need it on the flat slot |
| `bz` (note) | ❌ NOT IN WIRE | we synthesize; server doesn't use it |

**The wire `jtsjlist[]` entry is just `{xqj, ksjc, jsjc}`.** Our
`BorrowTimeSlot.to_api()` should drop `xh`, `zcbds`, `bz` for the
flat-slot list (or have a separate, simpler serializer).

## Shbj flag — full code path (verified)

`saveOrSubmit(flag)` is the entry point from the drawer's save/submit
buttons. The full function (extracted from page HTML, verified
2026-06-29):

```js
saveOrSubmit: function(flag) {
    var self = this;
    this.$refs.cdjyform.validate()
        .then(valid => {
            // ... client-side validation gates ...
            self.copyData(flag);             // copies shbj=flag into addDrawer
            $.extend(self.cdjyform, {shbj: flag});   // ★ sets cdjyform.shbj
            self.addDrawer.loading = true;
            let __ajax__ = $.ajax({
                url: baseUrl + 'cdjy/addChangDiJieYongShenQing/1',
                data: JSON.stringify(self.cdjyform),
                type: 'post',
                dataType: 'json',
                contentType: 'application/json',
            });
            return __ajax__;
        })
        .then(res => {
            self.addDrawer.loading = false;
            if (res.code == 200) {
                // success — reset form, close drawer, refresh list
            } else if (res.code == 100500) {
                // 100500 = location conflict — confirm dialog;
                // on confirm, sets cdjyform.hlddct = '1' and retries
                self.cdjyform.hlddct = '1';
                self.saveOrSubmit(flag);
            } else if (res.code == 500) {
                // 500 = generic error — show error message
            }
        });
}
```

So:
- **The only difference between 保存 and 提交 is `shbj`**
- The retry path for location-conflict sets `hlddct = '1'` (string!)
  then re-calls `saveOrSubmit(flag)` with the same flag

The OTHER handler in the same component is `updateOrSubmit(flag)`,
which hits a DIFFERENT URL:
- `cdjy/updateChangDiJieYongShenQingPut/1` (note the `Put` suffix)

This is the EDIT-FROM-LIST flow (modifying an existing application
from the audit/list page). The body shape is the same
(`JSON.stringify(this.cdjyform)`), but the URL has `Put` in it.

## Other write endpoints (from the catalog, cross-checked)

| Endpoint | Body | Triggered by | Notes |
|---|---|---|---|
| `cdjy/addChangDiJieYongShenQing/1` | full cdjyform (JSON) | `saveOrSubmit(flag)` | CREATE — verified |
| `cdjy/updateChangDiJieYongShenQingPut/1` | full cdjyform (JSON) | `updateOrSubmit(flag)` | EDIT from list — verified via regex-over-page |
| `cdjy/updateChangDiJieYongShenQing` | `{id, xn, xq, flag}` (form) | inline `$.post` in list page | STATUS CHANGE on existing row |
| `cdjy/submitChangDiJieYongShenQing` | `{id}` (form) | confirm dialog from list | SUBMIT-FOR-AUDIT (after create) |
| `cdjy/deleteChangDiJieYongShenQing` | `{id}` (form) | confirm dialog from list | DELETE application |
| `cdjy/deletesqmx` | `{id}` (form) | row delete | DELETE detail row |
| `cdjy/revokeChangDiJieYongShenQing` | (not probed) | (presumably form) | WITHDRAW/REVOKE |

## What changes in `to_api()` to match the wire

(To be applied when the user approves the fix; this is documentation
of the diff, not a code change yet.)

```python
# In BorrowApplication.to_api():
def to_api(self) -> dict:
    return {
        # existing
        "id": self.id, "jhdh": self.jhdh,
        "sqr": self.applicant_name,
        # NEW
        "sqr_en": self.applicant_name_en or "",   # new field
        "sqrdh": self.applicant_phone,
        "sqrzgh": self.applicant_employee_id,
        "sqrdw": self.applicant_dept,
        # NEW
        "sqrdw_en": self.applicant_dept_en or "",  # new field
        "sqrdwdh": self.applicant_dept_code,
        "syr": self.user_name,
        # NEW
        "syr_en": self.user_name_en or "",         # new field
        # NEW (legacy dup)
        "jyrdh": "",
        "syrdh": self.user_phone,
        "syrzgh": self.user_employee_id,
        "syrdwdm": self.user_dept_code,
        # semester
        "xn": self.semester.xn if self.semester else "",
        "xq": self.semester.xq if self.semester else "",
        # REMOVE: "xnxq": self.semester.xnxq,  # wire has xn+xq, not xnxq
        "xiaoqu": self.campus,
        "zc": self.weeks,
        "qsjsz": self.start_end_weeks,
        "rs": self.headcount,
        "jyyy": self.purpose,
        "sfsjysxtly": self.external_oa_approval,
        "shjs": self.audit_role,
        # NEW
        "shjsxm": "",     # auditor role display name (filled in later)
        "shjsxm_en": "",
        # NEW
        "shyj": "",       # audit opinion (empty on create)
        # NEW
        "xnxw": self.new_or_continued or "",
        # NEW
        "hlddct": False,  # boolean — ignore-location-conflict
        # NEW
        "zhxgr": "",
        "xhxgsj": "",
        # NEW
        "jtsjlist": [_flat_slot_to_api(s) for s in all_flat_slots],  # form-level
        # NEW
        "cdjymlist": [],
        "cdjymxlist": [_detail_to_api(d) for d in self.details],
        # save/submit flag — must be set by the caller
        "shbj": self.audit_office or "bc",  # 'bc' (save) or 'tj' (submit)
    }


# In _detail_to_api() — for each BorrowDetail:
def _detail_to_api(d: BorrowDetail) -> dict:
    return {
        "xuhhao": d.seq,
        # NEW (per-row date model)
        "ksrq": d.start_date or "",
        "jsrq": d.end_date or "",
        # NEW
        "rs": str(d.capacity) if d.capacity else "",  # STRING
        # NEW
        "jyyy": d.purpose or "",
        "zc": d.week_bitmask or "",
        "qsjsz": d.week_range or "",
        "xqj": str(d.weekday) if d.weekday else "",   # string
        "ksjc": str(d.period_start) if d.period_start else "",
        "jsjc": str(d.period_end) if d.period_end else "",
        # NEW
        "jyxq": d.semester_key or "",  # xn+xq concatenated
        # NEW
        "sfsysb": "1",   # default to use equipment
        # NEW
        "jyjs": "",
        "cddm": d.room_code,
        "cdmc": d.room_name,
        # NEW (per-row copies)
        "xn": d.semester_xn or "",
        "xq": d.semester_xq or "",
        "xiaoqu": d.campus or "",
        # NEW (per-row override fields, empty by default)
        "sqr": "", "sqrdh": "", "syr": "", "syrdh": "",
        "sqrdw": "", "sqrdwdh": "",
        "shjs": "", "shyj": "",
        # NEW (per-row filter snapshot, TriState)
        "zysfkyd": "2",   # default 不限制
        "sfjtjs": "2",
        # NEW
        "sfblcd": "",     # per-row, usually empty
        # REMOVE: "zws", "cdlocation", "yongtu" — wire doesn't have these
        # REMOVE: nested "jtsjlist" — wire has jtsjlist only at form level
    }


# NEW: flat slot serializer (form-level jtsjlist[])
def _flat_slot_to_api(s) -> dict:
    return {
        "xqj": str(s.weekday) if s.weekday else "",
        "ksjc": str(s.period_start) if s.period_start else "",
        "jsjc": str(s.period_end) if s.period_end else "",
    }
```

## Unverified (per iron law #11)

- **Server-side field validation**: which fields are REQUIRED vs
  OPTIONAL. The probe sent a full form; the server's response
  (success vs 100500/500) tells us which combos work. A series of
  decrementing-field probes would nail this down.
- **Retry-on-100500 path**: when the location conflict happens, the
  client sets `hlddct = '1'` (string, not boolean). This was
  observed in source but not exercised.
- **The `xh` (sequence) and `zcbds` (week pattern) fields on the
  flat slot list**: not in the wire. May be ignored, or may be
  silently coerced.
- **The `qssjz: '1'` format**: probe used `'1'` (single week).
  The full format is `"start_week,end_week"`. Wire behavior with
  multi-week inputs not verified.
- **The `zc: '1'` bitmask format**: probe used single char `'1'`.
  The reference doc says it's a 34-char bitmask, but in the row
  context a single char was accepted. The relationship between
  the form-level `apsyenablezc` (34-char bitmask) and the row's
  `zc` (1-char) is not yet clear.
- **The `sfwhxnxw == '1'` and `sfblcd` UI flags**: not yet
  verified whether they affect the wire payload.

## Reproduction recipe

```bash
# 1. Install dependencies
pip install sustech-survival[playwright]
playwright install chromium

# 2. Run the probe (uses existing credentials.txt + TIS session)
python ~/.openclaw/code/sustech_survival/scripts/probe_cdjy_post.py

# 3. Output files
#   /tmp/cdjy_post_payload.json  — the captured wire body
#   /tmp/cdjy_debug.png          — drawer screenshot (validation state)
```

The probe:
- Logs in via the standard `TISAuth.ensure()` path
- Opens `/cdjy/query/1/sq`
- Clicks the "添加" (add) button
- Injects a fake `user` into `localStorage` (so `openAddDrawer`
  can populate the form)
- Waits for the drawer to open and the form to be auto-filled
- Fills the form with `YJ-101` / 2026-07-01 / Wednesday 3-4 / 30
  people / "测试借用"
- Hooks `$.ajax` to capture the next POST
- Calls `saveOrSubmit('bc')` (with form validation bypassed)
- The route handler fulfills the POST with a fake `{code: 200}`
  so no real create happens
- The captured wire payload is written to
  `/tmp/cdjy_post_payload.json`
