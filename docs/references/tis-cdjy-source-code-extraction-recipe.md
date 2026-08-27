# TIS cdjy — Source-code extraction recipe (requests + regex)

> **What this is.** A cheaper alternative to the Playwright wire-payload
> probe (`tis-cdjy-post-probe-2026-06-29.md`). Instead of driving a
> browser, you:
> 1. Fetch the TIS page HTML via `requests` (live session)
> 2. Regex-extract the Vue component's inline JavaScript
> 3. Read the `data()`, `methods`, and `addjxx()`/`saveOrSubmit()` functions
>    directly from source
>
> **Why this matters.** The Playwright probe captures the *wire shape*
> (what the browser actually POSTs). This technique captures the *source
> code* (what the Vue component *thinks* it will POST — the initializer
> values, the flag semantics, the validation logic, the error handling).
> They differ in surprising ways, as discovered 2026-06-29:
>
> | Aspect | Playwright probe (wire) | Source-code extraction (truth) |
> |---|---|---|
> | `saveOrSubmit('bc')` | "bc" | '0' (draft) / '1' (submit) |
> | `shbj` | "bc" | "0" / "1" |
> | `hlddct` | `false` (bool) | `'1'`/`'0'` (string) — set on code 100500 retry |
> | row fields | 25 (guessed) | 28 (from `addjxx()`) |
>
> **Use this FIRST** to get the correct field names, defaults, and flag
> semantics. Then use the Playwright probe to verify the wire shape
> matches what the source says.

## Prerequisites

- A live TIS session (CAS-authed `requests.Session`)
- Python stdlib: `re`, `json`

## Step 1: Fetch the page

```python
from sustech_survival.sso import TISAuth
auth = TISAuth()
ok, reason = auth.ensure()
sess = auth.requests_session

r = sess.get("https://tis.sustech.edu.cn/cdjy/query/1/sq", timeout=30)
html = r.text
# ~170K chars for the cdjy page
```

**Gotcha:** The page's inline Vue component is NOT in a separate hashed
JS bundle — it's embedded in the `<script>` tags of the HTML itself.
This is why regex works directly on the page source and bundle-walking
finds nothing (`search_files` for `inco-*.js` returns 0 hits).

## Step 2: Extract `data()` block

```python
data_match = re.search(
    r"data\s*\(\s*\)\s*\{\s*return\s*\{(.+?)\n\s*\}\s*\}",
    html, re.DOTALL
)
```

This reveals all reactive state: `zysfkyd: '2'`, `sfjtjs: '2'`,
`curr_ksrq: null`, `curr_jsrq: null`, `sfblcd: i18n(...)`, etc.

## Step 3: Extract `addjxx()` row initializer

```python
addjxx_match = re.search(r"addjxx:function\s*\([^)]*\)\s*\{", html)
```

Then walk braces to capture the full function body. The function
returns a literal object with **exactly 28 keys**:

```javascript
var jyxx={
    xuhhao:xuh, ksrq:'', jsrq:'', rs:null, jyyy:'', zc:'',
    qsjsz:'', xqj:'', ksjc:'', jsjc:'', jyxq:'', sfsysb:'1',
    jyjs:'', cddm:'', cdmc:'', xn:'', xq:'', xiaoqu:'',
    sqr:'', sqrdh:'', syr:'', syrdh:'', sqrdw:'', sqrdwdh:'',
    shjs:'', shyj:'', zysfkyd:'2', sfjtjs:'2'
}
```

## Step 4: Extract `saveOrSubmit()` — key findings

```python
sos_match = re.search(r"saveOrSubmit:function\s*\([^)]*\)\s*\{", html)
```

Inside `saveOrSubmit(flag)`:

1. **flag = button param**: `'0'` for 保存 button, `'1'` for 提交 button
   ```html
   @click="saveOrSubmit('0')">保存
   @click="saveOrSubmit('1')">{{i18n('PKGL.tijiao')}}
   ```

2. **shbj is set via** `$.extend(self.cdjyform, {shbj: flag})`
   So `shbj` in the wire = `'0'` or `'1'`, matching the button.

3. **URL is fixed**: `baseUrl + 'cdjy/addChangDiJieYongShenQing/1'`
   No branching on the flag.

4. **Body =** `JSON.stringify(self.cdjyform)`

5. **Validation (client-side, before POST):**
   - Every row must have `xqj`, `ksjc`, `jsjc` — else reject
   - Form `$refs.cdjyform.validate()` must pass — else reject
   - For student role, if `sfxzshjs='1'`, `shjsxm` must be set
   - At least one row must have `ksrq/jsrq` within `rlsjd[]` range
   - If `sfzhjd='1'`: all rows must have `zc` (week); rows without `cddm` = error on submit ('1')
   - On submit ('1'), empty `cddm` rows are rejected ("没有指定场地")

6. **Error handling:**
   - `code == 200` → success (close drawer, refresh list)
   - `code == 100500` → location conflict → show modal → if user OK, set `hlddct='1'` (STRING) and retry
   - `code == 500` → show error message

## Step 5: Extract `openAddDrawer()` — how fields are auto-filled

```python
oad_match = re.search(r"openAddDrawer:\s*function\s*\([^)]*\)\s*\{", html)
```

Key auto-fill logic:

```javascript
var __user = JSON.parse(localStorage.getItem('user'))
self.cdjyform.xn = self.queryform.xn
self.cdjyform.xq = self.queryform.xq
self.cdjyform.sqr = __user.xm
self.cdjyform.sqrzgh = __user.yhdm
self.cdjyform.syrzgh = __user.yhdm
self.cdjyform.syr = __user.xm  // conditional on i18n flag
self.cdjyform.sqr_en = __user.xm_en != null && __user.xm_en != '' ? __user.xm_en : __user.xm
self.cdjyform.sqrdw = __user.bmmc || ''
```

The `__user` object comes from `localStorage.getItem('user')` which was
populated earlier by `$.post(baseUrl+'user/me', ...)`.

## Step 6: Extract `copyData()` — what it actually does

```javascript
copyData: function(flag) {
    var base = {shbj: flag}
    var self = this
    $.extend(this.addDrawer, base)
    if (this.addDrawer.id) {
        this.cdjyform.cdjymxlist.forEach(function(e) {
            $.extend(e, {jhdh: self.addDrawer.id})
        })
    }
}
```

Just sets `addDrawer.shbj = flag` and, for updates, adds `jhdh` to each
row. **Does NOT copy form-level fields into per-row fields** — that's
handled by the template binding before saveOrSubmit is called.

## Step 7: Extract `updateOrSubmit()` — the edit path

Same body shape as `saveOrSubmit()` but POSTs to:
```
cdjy/updateChangDiJieYongShenQingPut/1
```

Flag values: `'9'` (确认修改/confirm edit), `'0'` (保存/save),
`'1'` (提交/submit).

## Corrected field values (2026-06-29)

| Field | Playwright probe said | Source code says | Fix |
|---|---|---|---|
| `shbj` (save) | `"bc"` | `"0"` | `audit_office="0"` |
| `shbj` (submit) | `"tj"` | `"1"` | `audit_office="1"` |
| `hlddct` | `false` (bool) | `"1"` / `"0"` (string) | `to_api`: `"1" if ... else "0"` |
| `row fields` | ~25 | 28 (addjxx has 28) | Match `addjxx()` exactly |
| form-level `rs` | int 30 | int (from template) | OK — form rs is int, row rs is string |

## When to use this vs the Playwright probe

| Technique | Captures | Best for | Cost |
|---|---|---|---|
| Source-code extraction | Source defaults, flag semantics, validation logic, error paths | FIRST pass — get field names right | ~10s (requests + regex) |
| Playwright wire probe | Actual POST body, per-row duplication, string-vs-int | VERIFYING the wire shape matches source | ~30s (browser + route intercept) |

**Always do both** for a new destructive TIS endpoint. Source first to
get the shape right, then wire-probe to catch any serialization quirks
(Vue computed properties, reactive getters, `$.extend` mutations).

## See also

- `tis-cdjy-post-probe-2026-06-29.md` — the wire-payload probe (Playwright)
- `tis-cdjy-form-schema-2026-06-29.md` — the regex-over-page field extraction
- `spa-js-bundle-walk-recipe.md` — the bundle-walking approach (for pages with hashed JS)
- `tis-spa-menu-discovery-2026-06-28.md` — finding hidden TIS features via menu API
