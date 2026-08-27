# TIS 场地借用 (cdjy) — Vue component source code analysis (2026-06-29)

> **Source:** `GET https://tis.sustech.edu.cn/cdjy/query/1/sq` via authenticated
> TIS `requests.Session`. Functions extracted via brace-level regex matching
> on the inline Vue component embedded in the page HTML.
>
> **Key finding:** The earlier Playwright wire probe (`saveOrSubmit('bc')`) used
> an injected value — the real TIS UI uses `saveOrSubmit('0')` (保存/draft)
> and `saveOrSubmit('1')` (提交/submit). The difference matters because the
> serialized `cdjyform.shbj` matches the flag argument: `'0'` or `'1'`.

## `addjxx()` — Row initializer (28 keys)

```js
addjxx:function() {
    var xuh
    if (this.cdjyform.cdjymxlist.length == 0) {
        xuh = 1
    } else {
        xuh = parseInt(this.cdjyform.cdjymxlist[
            this.cdjyform.cdjymxlist.length - 1
        ].xuhhao) + 1
    }
    var jyxx = {
        xuhhao: xuh,
        ksrq: '',      // start date YYYY-MM-DD
        jsrq: '',      // end date YYYY-MM-DD
        rs: null,      // per-row headcount (null = empty/not-set)
        jyyy: '',      // per-row purpose
        zc: '',        // week pattern (bitmask or single week)
        qsjsz: '',     // start-end weeks
        xqj: '',       // weekday 1-7
        ksjc: '',      // start period 1-12
        jsjc: '',      // end period 1-12
        jyxq: '',      // semester key (xn+xq concatenated)
        sfsysb: '1',   // use equipment (binary: '1'=yes, '0'=no)
        jyjs: '',      // borrow end (timestamp/empty)
        cddm: '',      // room code
        cdmc: '',      // room display name
        xn: '',        // academic year (copied from form)
        xq: '',        // semester code (copied from form)
        xiaoqu: '',    // campus (copied from form)
        sqr: '',       // per-row applicant name override
        sqrdh: '',     // per-row applicant phone override
        syr: '',       // per-row user name override
        syrdh: '',     // per-row user phone override
        sqrdw: '',     // per-row applicant dept override
        sqrdwdh: '',   // per-row applicant dept code override
        shjs: '',      // auditor role code
        shyj: '',      // audit opinion
        zysfkyd: '2',  // movable-seats filter (TriState: '0'/'1'/'2')
        sfjtjs: '2',   // tiered-room filter (TriState: '0'/'1'/'2')
    }
    // Async init of sfsysb default from setting
    this.$$$P('CDJY_SETTING.show.'+this.pylx_str+'.sfsysb_def', '1', (result)=>{
        jyxx.sfsysb = result
    })
    this.cdjyform.cdjymxlist.push(jyxx)
}
```

**28 key-value pairs** (including `xuhhao`). Note no `sfblcd` or `jtsjlist`
at the row level — those are handled differently (form-level jtsjlist is
populated from `cdjyform.cdjymxlist.filter(e => e.xqj && e.ksjc && e.jsjc)`).

## `saveOrSubmit(flag)` — Function body

```js
saveOrSubmit:function (flag) {
    var self = this
    this.$refs.cdjyform.validate()
        .then(valid =>{
            // Validation: every row must have xqj, ksjc, jsjc
            var wap = this.cdjyform.cdjymxlist.find(
                e=>!e.xqj || !e.ksjc || !e.jsjc
            )
            if(wap) return Promise.reject({content:'借用时间未选择！'})

            if (!valid) return Promise.reject({content:'申请信息填写不完整'})

            // Audit-role check (student role only)
            if (self.systemProperty.role.xs == self.G_JSDM) {
                if (self.sfxzshjs == '1') {
                    if (!(self.cdjyform['shjsxm'])) {
                        return Promise.reject({content:'请选择审核教师'})
                    }
                }
            }

            // Week/room validation (only when sfzhjd == '1')
            if (self.sfzhjd == '1') {
                // __LEN = rows without cddm
                // __ZCLEN = rows without zc or zc==0
            }

            // Date range validation: each row's ksrq/jsrq must be within rlsjd
            var exist_not_use_date = self.cdjyform.cdjymxlist.filter((ele) => {
                let find_index = this.rlsjd.findIndex(kysj=>{
                    return ele.ksrq >= kysj.ksrq && ele.jsrq <= kysj.jsrq
                })
                return find_index != -1
            })
            if (exist_not_use_date.length == 0) {
                return Promise.reject({content:"时间超出可使用范围"})
            }

            // Submit-specific check: rows without cddm are rejected
            if(__LEN > 0 && (flag == '1' || flag == '9')) {
                return Promise.reject({content:"没有指定场地"})
            }

            // ★ KEY: copyData(flag) then set shbj
            self.copyData(flag)
            $.extend(self.cdjyform, {shbj: flag})
            self.addDrawer.loading = true

            let __ajax__ = $.ajax({
                url: baseUrl + 'cdjy/addChangDiJieYongShenQing/1',
                data: JSON.stringify(self.cdjyform),
                type: "post",
                dataType: "json",
                contentType: "application/json"
            })
            return __ajax__;
        })
        .then(res=>{
            self.addDrawer.loading = false
            if (res.code == 200) {
                // Success: reset form, close drawer, refresh list
            } else if (res.code == 100500) {
                // ★ LOCATION CONFLICT: show confirm dialog
                // On confirm: hlddct = '1' (string!) and retry
                self.cdjyform.hlddct = '1'
                self.saveOrSubmit(flag)
            } else if (res.code == 500) {
                // Generic error
            }
        })
        .catch((e)=>{ self.$Message.error(e) })
}
```

**Key facts:**
- Save button calls `saveOrSubmit('0')`, submit calls `saveOrSubmit('1')`
- `shbj` is SET by `$.extend(cdjyform, {shbj: flag})` — so the wire value
  equals the flag argument (`'0'` or `'1'`)
- `copyData(flag)` sets `addDrawer.shbj = flag` and for updates appends
  `jhdh` to each row
- `hlddct` is `'1'` (string) on retry, not `true` (boolean)
- `jtsjlist` is NOT built in saveOrSubmit — it's built earlier by the
  component when the time-slot modal fires

## `copyData(flag)`

```js
copyData:function (flag) {
    var base = {shbj: flag}
    var self = this
    $.extend(this.addDrawer, base)
    if (this.addDrawer.id) {
        this.cdjyform.cdjymxlist.forEach(function (e) {
            $.extend(e, {jhdh: self.addDrawer.id})
        })
    }
}
```

Simple — copies `shbj=flag` into `addDrawer` (UI state), and on updates
appends `jhdh` to each detail row.

## `openAddDrawer()` — Form initialization

```js
openAddDrawer: function() {
    var self = this
    self.jsdm = self.G_JSDM
    self.$refs.cdjyform.resetFields()
    for (k in self.cdjyform) {
        if (typeof self.cdjyform[k] != 'object') {
            self.cdjyform[k] = ''
        }
    }

    this.$nextTick(function () {
        // Check approval node status
        $.post(baseUrl+'cdjy/queryShywlcDqjdbsfzhjd', {id:''}, function (res) {
            self.sfzhjd = res

            // Read user from localStorage
            var __user = JSON.parse(localStorage.getItem('user'))

            self.addDrawer.flag = 'add'
            self.addDrawer.id = ''
            self.cdjyform.xn = self.queryform.xn
            self.cdjyform.xq = self.queryform.xq
            self.cdjyform.sqr = __user.xm                // applicant name
            self.cdjyform.sqrzgh = __user.yhdm             // employee id
            self.cdjyform.syrzgh = __user.yhdm             // user employee id

            // syr is conditional on i18n flag
            if (i18n('PKGL.CDJY.SQRXZSFJY') == '1' && ...) {
                self.cdjyform.syr = __user.xm
            }

            self.cdjyform.sqr_en = __user.xm_en || __user.xm
            self.cdjyform.sqrdw = __user.bmmc || ''
            // ... more fields from __user
        })
    })
}
```

## `updateOrSubmit(flag)` — Same logic, different URL

```js
updateOrSubmit:function (flag) {
    var self = this
    this.copyData(flag)
    $.extend(this.cdjyform, {shbj: flag})
    // Same date validation as saveOrSubmit
    this.$refs.cdjyform.validate((valid) => {
        $.ajax({
            url: baseUrl + 'cdjy/updateChangDiJieYongShenQingPut/1',
            // ★ NOTE: different URL (with "Put" suffix)
            data: JSON.stringify(this.cdjyform),
            type: "post",
            ...
        })
    })
}
```

## `data()` block — Key initial values

| Key | Initial value | Meaning |
|---|---|---|
| `zysfkyd` | `'2'` | 座椅可移动 (movable seats filter, 不限制) |
| `sfjtjs` | `'2'` | 阶梯教室 (tiered room filter, 不限制) |
| `sfblcd` | `i18n('PKGL.CDJY.BLCD')` | 保留多个场地 (multiple rooms) |
| `sfkxcd` | `'1'` | 是否可选场地 (room-selectable) |
| `sfkxzc` | `'1'` | 是否可选周次 (week-selectable) |
| `sfwhxnxw` | `'0'` | 是否维护新旧位 (new/continued field) |
| `sfxzshjs` | `'0'` | 是否选择审核角色 (auditor-role selectable) |
| `apsyenablezc` | 34-char bitmask all '1' | Week availability |
| `curr_ksrq` | `null` | Current date picker start |
| `curr_jsrq` | `null` | Current date picker end |
| `KGZT` | `1` | Room status toggle |
| `pylx` | `'1'` | Training type (1=undergrad) |
| `selectSksjShow` | `false` | Time-slot modal toggle |
| `selectJiaoShiModal` | `false` | Room-search modal toggle |
| `rlsjd` | `[]` | 日历时间段 (calendar periods) |
| `cdzyxqjc` | `[]` | Per-room occupancy cache |
| `weeks` | `['','一','二','三','四','五','六','日']` | Weekday display names |

## Corrected shbj semantics

| `shbj` value | Meaning | Button text | Function call |
|---|---|---|---|
| `'0'` | 保存 (save as draft) | 保存 | `saveOrSubmit('0')` |
| `'1'` | 提交 (submit for audit) | 提交申请 | `saveOrSubmit('1')` |
| `'9'` | 确认修改 (confirm edit) | 确认修改 | `updateOrSubmit('9')` |

**The probe script used `saveOrSubmit('bc')` which was wrong.** The
probe's intention was correct (verify the wire shape), but it injected
`'bc'` as a test value — that's not what the real TIS sends. Fix the
probe to use `saveOrSubmit('0')` for 保存 or `saveOrSubmit('1')` for 提交.

## `hlddct` retry path

When the server returns `code: 100500` (location conflict):

1. A confirm dialog appears: "场地已被占用，是否忽略冲突继续申请？"
2. User clicks OK → `cdjyform.hlddct = '1'` (STRING) is set
3. `saveOrSubmit(flag)` is called again with the SAME flag
4. The retried POST includes `hlddct: '1'` instead of `hlddct: false`

## See also

- `tis-cdjy-post-probe-2026-06-29.md` — the Playwright wire payload capture
  (contains the `'bc'`/`'tj'` values that are wrong — this reference supersedes)
- `tis-cdjy-form-schema-2026-06-29.md` — regex-over-page field map
- `tis-cdjy-venue-borrowing-2026-06-28.md` — full endpoint catalog
