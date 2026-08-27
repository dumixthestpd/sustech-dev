# TIS 场地借用 (cdjy module) — Full endpoint map (2026-06-28)

> **🚨 SUPERSEDED 2026-06-29 by `references/tis-cdjy-post-probe-2026-06-29.md`.**
> This file's `cdjyform` shape is now confirmed by a Playwright probe
> against the live UI — 35 form-level keys, 25 per-row keys, 3 per-slot
> keys. The wire body is `JSON.stringify(this.cdjyform)` POSTed to
> `cdjy/addChangDiJieYongShenQing/1`, with `shbj='bc'/'tj'` being
> the ONLY difference between save and submit.
>
> **For the verified wire shape, READ THE PROBE REFERENCE FIRST.**
> This file is preserved for historical provenance of the endpoint
> discovery (the URL prefix hunt that found `cdjy` in the first place).

> **Status: ⚠️ ENDPOINT MAP ONLY — module NOT YET BUILT.** All write
> endpoints are real (verified 2026-06-28 by driving the live UI). Do
> NOT call write endpoints from this skill until a `sustech_survival.cdjy`
> module is implemented AND a destructive-flow audit (per iron law #1
> in `sustech-architecture/SKILL.md`) is in place.

## How this was found (the lesson that prompted this file)

A previous brute-probe concluded "TIS does NOT have a student-facing
classroom booking endpoint." That conclusion was wrong. The user pushed
back: "tis supports classroom booking as well. you should dig into it
more," then "walk into the ui interface and try again." The fix:

1. **Stop brute-probing URL paths.** TIS is a SPA. Menu items are
   loaded dynamically via the `/user/mk` + `/user/getMknodeMore`
   APIs — they are NOT visible in any page's static HTML.
2. **Drive the actual UI.** Drive Playwright through the student
   portal (`/student_index`), capture the menu API calls, then
   expand each top-level node to enumerate every menu item.
3. **Find the menu item "场地借用申请" → URL `/cdjy/query/1/sq`**.
   The key was discovering that `cdjy` (场地借) is the prefix —
   brute-probes had tried `cdsq`, `cdyy`, `jsjy`, `jssq`, all wrong.

Full discovery recipe in `references/tis-spa-menu-discovery-2026-06-28.md`.

## Page

`GET https://tis.sustech.edu.cn/cdjy/query/1/sq` (申请 mode, `flag='sq'`)
`GET https://tis.sustech.edu.cn/cdjy/query/1/sh` (审核 mode, `flag='sh'`)

Verified 2026-06-28. Page HTML is 169 KB with 90 JS bundles (much
larger than `Xsxk/query/1`'s 93). The help text says
"教室借用管理咨询电话：88011966" and "校外活动申请场地需要OA呈批" —
off-campus activities need separate OA approval.

## Endpoint map (verified 2026-06-28 by reading the page HTML/JS)

### Write endpoints (POST, all need TIS CAS + `RoleCode: '00'`)

| Endpoint | Body | Returns | Notes |
|---|---|---|---|
| `cdjy/addChangDiJieYongShenQing/1` | JSON = full `cdjyform` (see below) | `{content: <full cdjyform with server-assigned id, jhdh, etc.>}` | The create call. Sends the entire form as JSON. Same URL is hit by `saveOrSubmit('bc')` (保存) AND `saveOrSubmit('tj')` (提交) — `shbj` flag is the only difference. |
| `cdjy/updateChangDiJieYongShenQingPut/1` | JSON = full `cdjyform` | same as create | **The edit-from-drawer flow** (used by `updateOrSubmit(flag)`). Verified 2026-06-29 — catalog originally missed this endpoint. Body shape is identical to `addChangDiJieYongShenQing/1`. |
| `cdjy/updateChangDiJieYongShenQing` | `{id, xn, xq, flag}` (form-encoded) | `{content: <full cdjyform>}` | Status change on EXISTING row (not full edit). Form-encoded, NOT JSON. |
| `cdjy/deleteChangDiJieYongShenQing` | `{id}` (form-encoded) | refreshes list | Deletes one application (releases the room). |
| `cdjy/deletesqmx` | `{id}` (detail row id, form-encoded) | refreshes list | Deletes one detail row inside an application. |
| `cdjy/submitChangDiJieYongShenQing` | `{id}` (form-encoded) | info toast + refresh progress | Submits the saved application for approval. (The `saveOrSubmit('tj')` path on the create side already submits; this endpoint is the submit for already-saved drafts.) |
| `cdjy/revokeChangDiJieYongShenQing` | (not probed) | refreshes list | Withdraw / revoke a submitted application. |
| `cdjy/verifyChangDiJieYongShenQing` / `...Put` / `...Batch` | (not probed, teacher-side) | (varies) | Audit / verify actions. Teacher-side only. |

### Read endpoints

| Endpoint | Body | Returns |
|---|---|---|
| `cdjy/queryChangDiJieYong/1` | (depends on `queryform`) | paged list of my applications |
| `cdjy/yzkg` | `{xn, xq}` | `"0"` if NOT eligible, anything else if OK |
| `cdjy/shztlist` | `{ywdm: 'CDJYLC'}` | list of audit statuses |
| `cdjy/queryShywlcDqjdbsfzhjd` | (form params) | current approval node info |
| `cdjy/queryChangDiZhanYongShiJian` | JSON body `{cddm, ...}` | `{content: <occupancy info>}` — POST with JSON content-type |
| `cdjy/queryzcbykssjjssj` | `{xn, xq, zc}` | week start/end datetime |
| `cdjy/queryJrjtrq` | (none) | today's date |
| `cdjy/queryKgzt` | (none) | room enabled status flag |
| `cdjy/queryjtsj` | (form params) | specific time slots |
| `gzlshywlc/queryShywlcShck` | `{ywlcslid: <id>, ywlcdm: 'CDJYLC'}` | approval workflow node audit trail |

## `cdjyform` data shape (verified 2026-06-28 from page JS)

```javascript
{
  id: '',                  // Server-assigned after first save.
  jhdh: '',                // 计划单号 (plan number). Likely auto-generated.
  sqr: '',                 // 申请人 (applicant name).
  sqr_en: '',
  sqrdh: '',               // 申请人电话 (applicant phone).
  xn: '',                  // 学年 (e.g. "2025-2026").
  xq: '',                  // 学期 ("1" / "2" / "3").
  zc: '',                  // 周次 (week, comma-separated like "1,2,3").
  rs: 0,                   // 人数 (people count, int).
  qsjsz: '',               // 起始结束周 (start/end week string — "1" or "1-15").
  syr: '',                 // 使用人 (responsible person / borrower).
  syr_en: '',
  jyrdh: '',               // 使用人电话 (borrower phone).
  syrdh: null,
  sqrdw: '',               // 申请单位 (applicant's dept, like "材料科学与工程系").
  sqrdw_en: '',
  sqrdwdh: '',
  shjs: '',                // 审核角色 (audit role — system-filled).
  shjsxm: '',              // 审核人姓名 (auditor name — system-filled).
  shjsxm_en: '',
  shyj: '',                // 审核意见 (audit opinion — system-filled).
  jyyy: '',                // 借用原因 / 用途 (purpose — REQUIRED for student submission).
  xiaoqu: '',              // 校区 (campus code).
  shbj: '',                // 审核标记 (audit flag — system-managed).
  xnxw: null,
  cdjymxlist: [],          // 场地借用明细 — list of (room × time) detail rows.
  jtsjlist: [],            // 具体时间 — list of time slots.
  sfsjysxtly: '',          // 是否实际使用校团委楼 (??? — likely internal flag).
  syrdwdm: '',             // 使用人单位代码 (dept code).
  sqrzgh: '',              // 申请人职工号 (applicant employee ID, = student ID).
  syrzgh: ''               // 使用人职工号 (borrower employee ID).
}
```

### Sub-structures (not yet reverse-engineered)

- **`cdjymxlist[]`** — list of detail rows, each probably has `{cddm,
  cdmc, xuhhao, ...}`. Needs UI walk to confirm exact shape.
- **`jtsjlist[]`** — list of time slots. Needs UI walk.

These are inferred from the form labels on the page (which I confirmed
exist but did not yet click through). Don't ship code calling these
without driving the UI to fill the form once and inspecting the POST
body.

## Permission gate

Before opening the add form, the page calls `cdjy/yzkg`:

```javascript
add: function () {
    var self = this;
    if (self.school == 'SCHOOL_HRB_HLJDX') {  // not SUSTech
        $.post(baseUrl + 'cdjy/yzkg', {xn, xq}, function (res) {
            if (res == "0") {
                self.$Message.warning({content: "您未在可场地借用申请表中", ...});
            } else {
                self.openAddDrawer();
            }
        });
    } else {
        self.openAddDrawer();  // SUSTech — straight to form
    }
}
```

So SUSTech students can apply directly. The warning
"您未在可场地借用申请表中" (you are not in the eligible venue-borrowing
applicant list) is for 哈理工 (HRB HLJDX) only. Verify with the actual
response — `cdjy/yzkg` returning `"0"` for SUSTech would mean a
different list-checking system.

## Relationship to other modules

- **NOT the ehall `booking.sustech.edu.cn` system.** That one covers
  35 书院/活动 venues. This covers all 421 教学楼 classrooms.
- **Adjacent to `cdkb/querycdkbList` (live occupancy read).** The
  `cdjy/queryChangDiZhanYongShiJian` endpoint appears to be the
  WRITE-aware variant of the same `cdkb` table — it tells you if a
  proposed slot conflicts with existing bookings or fixed schedules.
- **Approval workflow uses generic `gzlshywlc` (工作流审核) service.**
  Same `ywlc` workflow engine as other TIS approval flows (评教,
  退课申请, etc.). The workflow code is `CDJYLC`.

## What's still missing to ship a `cdjy` module

**Resolved 2026-06-29 by `references/tis-cdjy-post-probe-2026-06-29.md`:**
1. ~~Drive the UI through the full add form to capture `cdjymxlist[]`
   and `jtsjlist[]` exact shapes~~ ✓ Captured — 25 row keys, 3 slot keys.
2. ~~Confirm whether `jhdh` is auto-generated or user input~~ ✓ Server-assigned (empty on POST).

**Still open:**
1. **Server-side required-field validation** — which fields are
   REQUIRED vs OPTIONAL. The probe sent a full form; a decrementing-
   field probe (remove one field at a time and observe success/failure)
   would nail this down.
2. **Map the audit workflow chain**: who are the approvers (辅导员?
   书院? 教务处?), how many nodes, can a student see the chain.
3. **Iron law #1 audit**: this is a destructive flow on a graded
   (approval-tracked) target. Even though it's not a graded
   assignment, the workflow is institutional and a botched submit
   creates a real paper trail. `dry_run=True` by default; explicit
   confirmation required for the live POST.
4. **`updateOrSubmit` (edit-from-drawer) probe**: the
   `cdjy/updateChangDiJieYongShenQingPut/1` endpoint was confirmed
   to exist and to take the same body shape, but its exact response
   shape and the difference from `addChangDiJieYongShenQing/1` was
   not exercised end-to-end.

## Field-name clarifications (SUPERSEDED 2026-06-29 — see new file)

**This section is superseded by `references/tis-cdjy-form-schema-2026-06-29.md`,
which has the complete verified schema.** The earlier corrections here
were the 2026-06-29 trigger but are now incomplete — they missed:
- `hlddct` (ignore-location-conflict) — form-level boolean
- `sfblcd` (保留多个场地) — form-level boolean
- `sfsysb` (是否使用设备) — per-row, default `'1'`
- `sfjysy` (modal hardcoded flag) — `<inco-i-select-jiaoshi-modal-hgd>` prop
- The **date-based time model** (`ksrq`/`jsrq`) — wire is dates, not weeks
- The **form-level vs row-level filter snapshot** distinction
- The full `addjxx()` row initializer with all per-row fields

**For any cdjy schema work after 2026-06-29, READ THE NEW REFERENCE FIRST.**
The text below is preserved for historical provenance only.

---

The 2026-06-28 reference got the **search-step fields right** (the
endpoint exists, the field names are real) but the **UI-vs-API
distinction wrong** — corrected by the user 2026-06-29. If a future
agent sees the original 2026-06-28 wording without this section,
they will reproduce the same wrong-shape failure mode.

### Room search step (phase 3 of the TIS UI flow)

The TIS UI flow has 4 phases (per the user, 2026-06-29):

1. **Demand** (locked in first): semester, campus, headcount, the
   4 person fields (applicant name/phone, user name/phone),
   using-dept, and the 3 room-feature flags below.
2. **Schedule** (multi-ticket): date → weeks+weekday, time of day
   → period-OR-clock, which days.
3. **Place**: the system returns available rooms. **This step is
   not under `/cdjy/*` — it's a separate dialog that calls
   `POST /component/queryDiDian`.** Full recipe in
   `references/tis-didian-room-search-2026-06-28.md`.
4. **Reason**: free text → `jyyy`.

### The 3 room-feature fields (the user-corrected part)

| UI label (what the user sees) | TIS API key | Type | Semantics |
|---|---|---|---|
| 阶梯教室 | **`sfjtjs`** | TriState (不限制/是/否) | whether the room is tiered. Independent room attribute. |
| 座位可移动 | **`zysfkyd`** | TriState (不限制/是/否) | whether the room's seats are movable. Independent room attribute. |
| 是否使用多媒体设备 | **TBD — needs live probe** | **binary on/off** | whether the BOOKER will use the room's multimedia equipment. **NOT a room category filter.** A room can have multimedia but the booker can say "I'm not using it." |
| 场地类别 (room category) | **`cdlb`** | enum (多媒体教室 / 计算机房 / 实验室 / 讨论型教室 / 体育馆 / etc.) | dropdown of room types. **Separate from the multimedia flag** — they are NOT the same thing. |

**The accuracy trap** (the user explicitly called this out):
"this accuracy gives me a feeling that all those are wrong" — when
one field name is wrong, the user loses trust in all of them. The
failure mode that produced this:

1. The 2026-06-28 catalog + this reference correctly list
   `sfjtjs` / `zysfkyd` / `cdlb` for the room-search step.
2. A 2026-06-29 design proposal mapped `cdlb` to "whether the
   booker uses multimedia" — wrong, `cdlb` is the room category
   dropdown, and the media flag is a separate binary field whose
   TIS key is not yet documented in this reference.
3. The user pointed out that the media field is **not** a room
   category, it is a **per-application** on/off the booker
   toggles in the demand step.

**What the catalog does NOT yet have**: the TIS key for
`是否使用多媒体设备`. To find it, drive the live UI and inspect
the `cdjyform` payload (not `queryDiDian`) — this binary
field belongs to the application form, not the room-catalog
query. **Mark this `unverified — needs live probe` per iron
law #11** before any code touches it.

### Iron law #11 reminder

Per iron law #11 in `sustech-architecture/SKILL.md`: before
proposing any new schema field for a SUSTech system, you MUST
read this catalog + cross-check the existing `*_schema.py`. The
catalog often lists fields the code didn't yet expose. If the
catalog has no entry for what you need, mark it `unverified —
needs live probe` and STOP. Do NOT propose guessed field names.

The 2026-06-29 failure mode (proposed `Demand` with `media` /
`tiered` / `movable_seats` TriStates) was the prompt for iron
law #11. The corrected field names above are the catalog's
real spellings — use them.