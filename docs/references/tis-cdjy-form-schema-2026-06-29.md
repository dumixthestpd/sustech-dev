# TIS 场地借用 (cdjy) — Live form schema (2026-06-29)

> **The form-level vs row-level split is the key new finding.**
> Verified against the live UI on 2026-06-29 by reading the page HTML
> inline JS (the cdjy Vue component is embedded in the page, not in
> a separate hashed bundle — so **regex-over-page** is the discovery
> method, not bundle-walking).
>
> **Source-code extraction (2026-06-29 evening):** after the wire probe
> (which guessed wrong flag values), we went back and extracted the
> actual Vue component source via regex-over-page. Key findings:
> - `saveOrSubmit(flag)` where flag='0' (保存) or '1' (提交) — NOT 'bc'/'tj'
> - `hlddct` is `'1'` string on code 100500 retry, not bool
> - `addjxx()` initializes exactly 28 row keys (inline JS)
> - `copyData()` just sets `addDrawer.shbj=flag` + adds `jhdh` for updates
> - `updateOrSubmit()` uses same body shape but POSTs to Put/1
> - `openAddDrawer()` reads `__user` from `localStorage.getItem('user')`
> - The `/user/me` endpoint returns the same user data as `localStorage`

## How to find the schema (don't repeat the failed approaches)

The TIS cdjy Vue component is **embedded inline** in the page HTML —
not in a hashed JS bundle. Both attempts at bundle walking fail:

- `search_files` for `inco-*.js` in the page HTML → 0 hits.
- `re.findall(r'src="[^"]+\.js"', page)` → 96 generic JS bundles
  (jquery, vue, iview, etc.) but **none specific to cdjy**.

The right approach: read the page HTML and regex over it. The Vue
component's `data()` block declares all state, and the inline
template strings contain the field names in `v-model` / `:prop`
directives.

```python
page = sess.get("https://tis.sustech.edu.cn/cdjy/query/1/sq").text

# form-level assignments
form_fields = re.findall(r"cdjyform\.([a-zA-Z_]\w*)\s*=\s*([^,;\n}{]+)", page)

# data() declarations
data_body = re.search(r"data\s*\(\s*\)\s*\{\s*return\s*\{(.+?)\n\s*\}\s*\}", page, re.DOTALL)

# row-level (cdjymxlist[] sub-fields)
addjxx = re.search(r"addjxx:function\s*\([^)]*\)\s*\{(.+?)\n\s*\}", page, re.DOTALL)
```

## Form-level schema (`cdjyform.X`)

Auto-filled from `__user.*` on open. **User-editable in the "Demand" panel.**

| TIS API key | Source / auto-fill | Meaning | Verified |
|---|---|---|---|
| `id` | — | Server id (empty on new) | ✓ |
| `xn`, `xq` | `queryform.xn/xq` | Semester (form-wide) | ✓ |
| `xnxw` | empty | 新/续 (new/continued) | ✓ |
| `xhxgsj` | empty | Last-modified timestamp | ✓ |
| `zhxgr` | empty | Last modifier | ✓ |
| `sqr` | `__user.xm` | 申请人 (applicant name) | ✓ |
| `sqr_en` | `__user.xm_en` | applicant name EN | ✓ |
| `sqrdh` | `__user.lxdh \|\| ''` | 申请人电话 (applicant phone) | ✓ |
| `sqrzgh` | `__user.yhdm` | 申请人职工号 (applicant employee id) | ✓ |
| `sqrdw` | `__user.bmmc \|\| ''` | 申请单位 (applicant dept name) | ✓ |
| `sqrdw_en` | `__user.bmmc_en \|\| ''` | dept name EN | ✓ |
| `sqrdwdh` | empty (also at row) | dept phone/code | ✓ |
| `syr` | `__user.xm` | 使用人 (user name) | ✓ |
| `syrdh` | `__user.lxdh \|\| ''` | 使用人电话 (user phone) | ✓ |
| `syrzgh` | `__user.yhdm` | 使用人职工号 (user employee id) | ✓ |
| `syrdwdm` | `__user.bmdm \|\| ''` | 使用人单位代码 (user dept code) | ✓ |
| `hlddct` | `false` | 忽略地点冲突 (ignore location conflict) | ✓ |
| `shbj`, `shyj` | server | audit flag + opinion | ✓ |
| `cdjymxlist[]` | `[]` | Detail rows | ✓ |
| `cdjymlist[]` | `[]` | Alternate list (legacy?) | ✓ |
| `jtsjlist[]` | derived | Flattened time slots from cdjymxlist | ✓ |

## Form-level filter booleans (for the room-search modal)

These live in the Vue component's `data()` block and are passed as
**filters** to the room-search modal `<inco-i-select-jiaoshi-modal-hgd>`.
They are NOT in `cdjyform` — they're separate component state.

| TIS key | Default | Encoding | Meaning |
|---|---|---|---|
| `zysfkyd` | `'2'` | `'1'`=是 / `'0'`=否 / `'2'`=不限制 | 座椅可移动 (movable seats) |
| `sfjtjs` | `'2'` | `'1'`=是 / `'0'`=否 / `'2'`=不限制 | 阶梯教室 (tiered room) |
| `sfsysb` | (per-row only) | `'1'`=是 / `'0'`=否 | 是否使用设备 (use equipment) |
| `sfblcd` | `i18n('PKGL.CDJY.BLCD')` | `'1'`=是 | 保留多个场地 (allow multiple rooms) |
| `sfkxcd` | `'1'` | bool | 是否可选场地 (whether room-selectable) |
| `sfkxzc` | `'1'` | bool | 是否可选周次 (whether week-selectable) |
| `sfwhxnxw` | `'0'` | bool | 是否维护新旧位 (whether new/continued field) |
| `sfxzshjs` | `'0'` | bool | 是否选择审核角色 (whether auditor-role selectable) |

**Encoding nuance (verified):**
- **Filter state at form level**: TriState `'1'`/`'0'`/`'2'`.
  `'2'` is "不限制" (no restriction, default).
- **Snapshot value at row level**: Binary `'1'` or `'0'`.
  Templates only check `=='1'` and `=='0'` for display.
- **`sfsysb` (use equipment)** has NO form-level filter state — it's
  only ever a per-row field. Default `'1'` (yes). The user's mental
  model "use media" maps here.

## Room-search modal binding (verified)

```html
<inco-i-select-jiaoshi-modal-hgd
    :show.sync="selectJiaoShiModal"
    :enablezc.sync="apsyenablezc"
    sfjysy="1"
    :szhlct="false"
    :zysfkyd="zysfkyd"
    :sfjtjs="sfjtjs"
    :yqzws="cdjyform.rs"
    ...
></inco-i-select-jiaoshi-modal-hgd>
```

- `sfjysy="1"` — hardcoded flag inside the modal (purpose: 是否有实验;
  not user-editable from outside)
- `szhlct` — ignore-location-conflict prop (boolean)
- `zysfkyd`, `sfjtjs` — bound to form-level filter state
- `yqzws="cdjyform.rs"` — require-min-seats = headcount

The modal's backing endpoint is `POST /component/queryDiDian`
(verified earlier; recipe in
`references/tis-didian-room-search-2026-06-28.md`).

## Detail-row schema (`cdjymxlist[].X`)

Verified from `addjxx():function` (the function that initializes a new
detail row when the user clicks "add").

| TIS key | Default | Meaning |
|---|---|---|
| `xuhhao` | `auto` | Sequence within the application |
| `ksrq` | `''` | 开始日期 (start date, `YYYY-MM-DD`) |
| `jsrq` | `''` | 结束日期 (end date, `YYYY-MM-DD`) |
| `rs` | `null` | 人数 (headcount, per-row; usually same as form-level) |
| `jyyy` | `''` | 借用原因 (purpose, per-row; usually same as form-level) |
| `zc` | `''` | 周次 (week pattern, e.g. `"1,3,5,7"`) |
| `qsjsz` | `''` | 起始结束周 (`"start_week,end_week"`) |
| `xqj` | `''` | 星期几 (weekday, 1-7) |
| `ksjc` | `''` | 开始节次 (start period, 1-12) |
| `jsjc` | `''` | 结束节次 (end period, 1-12) |
| `jyxq` | `''` | 借用学期 (semester key) |
| `xn`, `xq`, `xiaoqu` | copied | Same as form-level |
| `sqr`, `sqrdh`, `syr`, `syrdh`, `sqrdw`, `sqrdwdh` | copied | Same as form-level |
| `sfsysb` | `'1'` | 是否使用设备 (use equipment) |
| `zysfkyd` | `'2'` | 座椅可移动 filter (filter-state value) |
| `sfjtjs` | `'2'` | 阶梯教室 filter |
| `sfblcd` | empty | 保留多个场地 |
| `cddm`, `cdmc` | empty | 场地代码 / 场地名称 (room code/name) |
| `jyjs` | empty | 借用结束 (borrow end — possibly date) |
| `xs` | empty | 学时 / 学生数 (? — unclear, single ref) |
| `shjs`, `shyj` | empty | Audit fields |

**KEY NEW FINDING (vs the existing schema in
`booking_schema.py:BorrowDetail`):**

- `ksrq`, `jsrq` — actual dates, NOT weeks. The user's mental model
  "weeks+weekdays" maps to this in the UI but the wire format is dates.
  (Conversion happens via the `queryzc` state — `curr_ksrq`/`curr_jsrq`
  initialized from the user's picked date range.)
- `sfsysb`, `zysfkyd`, `sfjtjs`, `sfblcd` — per-row filter snapshot.
  The current `BorrowDetail` doesn't have these.
- `sfwhxnxw`, `sfxzshjs`, `sfkxcd`, `sfkxzc` — UI-level flags, NOT
  sent to the API.

## Form-wide state (data() block) — UI-level only (not sent)

These live in `data()` but are NOT part of the wire payload — they're
UI-only state that drives what the modal shows.

- `apsyenablezc`: `String(Array(34).fill("1").join("")+"")` — week
  bitmask, 34 chars of "1" (all weeks). Sent as `:enablezc.sync`.
- `curr_ksrq`, `curr_jsrq` — date range currently being picked.
- `selectzc: { jsrq, ksrq, mxid, xuhhao }` — selected time-slot row.
- `cdzyxqjc: []` — 场地占用学期节次 (cached occupancy for the room).
- `rlsjd: []` — 日历时间段 (calendar periods from server).
- `mxid: []`, `current_mxid` — current detail-row id tracking.
- `KGZT: 1` — toggle state.
- `weeks: [,'一','二','三','四','五','六','日']` — weekday name list.

## What still needs verification

- The exact POST body for `cdjy/addChangDiJieYongShenQing/1`. Need to
  drive the UI through the full add → save flow with Playwright,
  intercept the network, and confirm the wire payload matches the
  schema above. Currently inferred from the data() block + addjxx()
  initializer.
- The submit-vs-save flag semantics (`shbj`): `updateOrSubmit(flag)`
  toggles between `'bc'` (保存) and `'tj'` (提交)? Need UI walk.
- The exact filter-mode API call: when the user clicks the modal
  "search" button, what does TIS POST? Suspected
  `component/queryDiDian` (room-search endpoint from the catalog).
  Confirm by intercepting network during modal use.