# SPA JS-Bundle Walk Recipe — when curl + guess won't work

> **🚫 DO NOT BRUTE-PROBE ENDPOINTS. 🚫** The user has stressed this
> multiple times ("I can't stress that more", 2026-06-28). If you
> find yourself writing a list of `for ep in candidates: sess.post(ep)`
> to test guessed URL paths — STOP. That's exactly the anti-pattern.
> Endpoints live in hashed JS bundles; read the bundle, follow the
> chain from the parent component to its child to the endpoint it
> POSTs to. The endpoints ARE there. Your job is to find them, not
> guess them. See the worked case studies below (选课 2026-06-19,
> cdkb 2026-06-28) for what "follow the chain" actually looks like.

> **When to use this.** A web app's endpoints are hidden in a hashed
> JS bundle, the menu HTML doesn't link to them, and you can't DevTools
> the live site. Brute-probing guessed paths returns 404 for every
> candidate. The endpoints ARE there — you just need to read the
> bundle source.
>
> This recipe was developed 2026-06-19 to crack the TIS 选课 write-side
> (add course / drop course) after a brute-probe failed. It was
> re-validated 2026-06-28 when the same approach cracked the TIS
> 场地课表 endpoint (`cdkb/querycdkbList`) that exposes live room
> occupancy (incl. borrowings 借用). It's generally applicable to
> any Vue/React SPA with hashed bundle names.

## TL;DR

1. **Log in via SSO/CAS.** Save the session cookies.
2. **Find the page that loads the action you want.** For TIS, the
   catalog page `/Xsxk/query/1` loads the `xsxk-<hash>.js` bundle;
   the home page doesn't. Curl a few candidate pages and `grep` for
   `inco.component.<name>` / `<bundle_keyword>`.
3. **Extract the bundle URL** from the page HTML:
   `grep -oE '/pub/<path>/<bundle>-[a-f0-9]+\.js' page.html`
4. **Download with `Referer` + session cookies.** Bare `curl` gets
   `HTTP 403 Forbidden` (Tengine blocks un-referred JS). Use Python's
   `requests.Session` with the cookies from step 1 and `Referer` set
   to the page URL.
5. **Grep the bundle for endpoint paths** + **method bodies**:
   ```bash
   grep -oE '"[A-Z][A-Za-z]+/[A-Za-z_]+"' bundle.js | sort -u
   grep -B 1 -A 30 '<method_name>:function' bundle.js
   ```
6. **Look for the form/payload object.** In TIS it's called
   `queryform: { ... }` — a 40-key object that defines every field
   the write-side expects. Other SPAs may call it `payload`, `body`,
   `formData`, etc.
7. **If a component uses a CHILD component, follow the chain.** The
   dialog component will instantiate a child component
   (`<inco-i-changdikebiao>`) that has its own bundle. That child's
   bundle is where the **actual data endpoint** lives (e.g.
   `cdkb/querycdkbList`).
8. **Document everything** in a per-system reference file.

## Concrete example — TIS 选课 write-side (2026-06-19)

### Step 1: Capture the session

```python
import json, re, requests
from pathlib import Path

sess_data = json.loads(Path(".../tis/session.json").read_text())
sess = requests.Session()
for k, v in sess_data["cookies"].items():
    sess.cookies.set(k, v, domain="tis.sustech.edu.cn")
sess.headers["User-Agent"] = "Mozilla/5.0 ..."
```

(TIS already had a session.json from a prior login. The point: reuse
the same Session object, not a fresh request, so cookies carry over.)

### Step 2: Find the right page

```bash
# Fetch candidates, look for "选课" / "select course" markers
for path in / /student_index /Xsxktz/initMenu /Xsxk/query/1; do
    curl -b cookies -s "https://tis.sustech.edu.cn$path" -o "$path.html"
    grep -c "xsxk\|XuanKe\|选课" "$path.html"  # 0, 0, 29, ...
done

# /Xsxk/query/1 wins with 29 hits + the Xsxk/query URL pattern
```

The home page (`/`, 13 KB) has only 4 script tags. `/student_index`
(70 KB) is a Vue app for the student dashboard. The catalog page
(`/Xsxk/query/1`, 130 KB) is where the action buttons live.

### Step 3: Extract bundle URLs

```bash
grep -oE 'src="[^"]+\.js"' /Xsxk/query/1.html | sort -u
```

Returns ~99 unique JS URLs. The relevant ones are in
`/pub/xkgl/xsxk/`. Key bundles:
- `/pub/xkgl/xsxk/xsxk-e9251afcd0ca4995004098e91ec476b0.js` (67 KB) — main module
- `/pub/xkgl/xsxk/xsxkColumn-c98e09b686bab8b199abb341bd210e71.js` (29 KB)
- `/js/Action-fc44de15a884c8d5cf62ea2fa3c6ded8.js` (14 KB) — generic action helper
- `/component/inco-ui-1.0.0-817f8d27bcd958366877d629d5a89fc6.js` (1.8 KB)

### Step 4: Download (needs Referer + cookies)

```python
sess.headers["Referer"] = "https://tis.sustech.edu.cn/Xsxk/query/1"
for b in bundles:
    r = sess.get(f"https://tis.sustech.edu.cn{b}", timeout=30)
    # 200 OK; without Referer, Tengine returns 403 Forbidden
    Path("/tmp/xsxk_bundles/").mkdir(exist_ok=True).joinpath(Path(b).name).write_bytes(r.content)
```

**Why bare `curl` fails:** Tengine checks the `Referer` header and
returns `HTTP 403 Forbidden` for cross-origin or un-referred JS
requests. The `requests.Session` from step 1 already has the CAS
cookies, so just set `Referer` to the page URL and it works.

### Step 5: Grep for endpoints + methods

```bash
# Endpoints — quoted strings
grep -oE '"Xsxk/[A-Za-z_]+"' xsxk.js | sort -u
# → 18 hits: addXuanke, tuike, addGouwuche, delGouwuche, queryKxrw, ...

# Method bodies — the actual handlers
grep -B 1 -A 30 'add_xuanke:function' xsxk.js
# → reveals: var url = baseUrl + 'Xsxk/addXuanke'; $.post(url, self.queryform, ...)

# Payload shape — the queryform object
grep -A 30 'queryform:{' xsxk.js
# → 40-key dict with p_xn, p_xq, p_id, p_xktjz, p_sfhlctkc, ...
```

### Step 6: Verify by reading the response handler

```js
// From xsxk.js — what the client does after a successful add
$.post(url, self.queryform, function(res){
    if(res.jg=='1'){
        self.$Message.success({content: res.message, ...});
        self.query();   // refresh the data
    } else {
        self.$Message.error({content: res.message, ...});
    }
})
```

This tells you:
- The response shape: `{jg, message, ...}` — at minimum these two fields
- `jg='1'` = success, anything else = failure (TIS uses `'0'`, `'-1'`)
- After success, the client refreshes — same query you used to load
  the list will show the new state

## Case study #2 — TIS 场地课表 via didian → changdikebiao chain (2026-06-28)

This is the **follow-the-chain** pattern. The 选择场地 dialog is a
search dialog, not a booking dialog. But it RENDERS a schedule grid
in the bottom panel — and THAT grid is a child component with its
own bundle, and THAT bundle is where the per-room live schedule
endpoint lives.

### Step 1: Find the dialog component

Walk all 99 scripts on `/Xsxk/query/1` and grep for the dialog
keywords. `inco.component.didian` (地点 = place/venue) hits:
- `场地×8` (venue)
- `选择场地×2` (select venue)
- `座位×13` (seat)
- `人数×1` (people count)
- `jslx×7` (room type)

The bundle is 30 KB and defines a Vue component
`inco-i-select-didian-modal` with title "选择场地" — this is the
search dialog.

### Step 2: Find the form params

The dialog has a `query()` method that calls
`baseUrl + 'component/queryDiDian'` with form data. The form
includes `sysj` (a list of time-slot dicts), `zws` (seat count),
`jslx` (room type), `xiaoqu` (campus), etc. The bundle also has a
comment block documenting the `sysj` shape:
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

**This is the key insight the bundle gives us:** the `zc` field is
a 34-char week bitmask (NOT a single week number), and `xq` inside
`sysj[]` is a weekday (NOT semester). The top-level `xq` field is
the semester — there's a name collision.

### Step 3: Call the endpoint and verify

The endpoint:
```
POST https://tis.sustech.edu.cn/component/queryDiDian
Body: {pylx, pageNum, pageSize, xn, xq, hlct, ..., sysj[0].zc, sysj[0].xq, ...}
Header: RoleCode: '00'   (any value; server only checks presence)
```

Returns the full 421-room inventory (一期校区) with capacity, building,
and per-room configuration bitmask (`kxzc`).

**But:** `kxzc` is the room's *configuration* (which periods it's open
for), not live occupancy. So we still don't have TA-booking data.

### Step 4: Follow the chain to the child component

The dialog renders a schedule grid in its footer using:
```html
<inco-i-changdikebiao v-if="kebiaoisshow" :xn="sysj[0].xn" :xq="sysj[0].xq"
                       :cddm="cddm" :sj="sysj"></inco-i-changdikebiao>
```

`inco-i-changdikebiao` is a CHILD component in a SEPARATE bundle:
`/component/inco/inco.component.changdikebiao-...js` (the
`inco-i-changdikebiao` component — same name prefix as the kebiao
schedule display).

### Step 5: Read the child component's bundle

`changdikebiao` makes ONE POST call in its `mounted()`:
```js
$.post(baseUrl + 'cdkb/querycdkbList',
       {cddm: this.cddm, xn: this.xn, xq: this.xq},
       function (res) { ... })
```

**This is the per-room live schedule endpoint.** It returns the
actual schedule entries (registered courses + borrowings 借用) for
one room. The dialog passes the user-selected `cddm` to this
component, which fetches the schedule.

### Step 6: Test the endpoint

```
POST https://tis.sustech.edu.cn/cdkb/querycdkbList
Body: {cddm: 'YJ-123', xn: '2025-2026', xq: '2'}
Header: RoleCode: '00'
```

Returns 106 entries for 一教123: 77 borrowings (with borrower name
+ phone in the SKSJ text) + 26 registered courses + 3 other
metadata entries. The SKSJ text format is:
- Borrowings: `【借用】[<week>]\n使用人:<borrower>\n联系电话:<phone>`
- Courses: `【本/研/研本】COURSE_NAME[TEACHER][GROUP][N周][J1-J2节]`

The KEY field is `xq{W}_jc{P}` (weekday + period). The XB field is
a sequence number. The SKSJ text contains the actual week(s).

### The lesson

> **Don't stop at the first endpoint you find.** When a component
> uses a child component, the child usually has the more specific
> data endpoint. `didian` (search dialog) only knows how to find
> rooms; `changdikebiao` (schedule grid) knows how to fetch the
> schedule for a specific room. Two endpoints, two different data
> shapes, both necessary for "live occupancy."

## What NOT to do

(Each of these is something I got wrong in earlier sessions.)

1. **🚫 Don't brute-probe endpoints. Don't write a list of guessed
   URL paths and POST to each one.** TIS returns 404 (or empty
   body, or Spring "endpoint not found" envelope) for paths it
   doesn't serve, which tells you nothing. I burned a session trying
   `/XkBcjAction/saveXkBcj`, `/xsxk/saveXk`, `/xkxt/queryKxList`
   and ~27 other guesses — all 404, no info. Same mistake in 2026-06-28
   when I brute-probed `/cdyy/save`, `/cdsq/add`, `/roomApply/save`,
   `/component/saveChangdi`, etc. **Read the bundle. Follow the
   chain. Find the actual endpoint that the JS code uses.**

2. **Don't claim "the write side is locked behind Vue" as the
   answer.** It's a partial observation, not a conclusion. The
   endpoints ARE there — they're just inside a JS bundle you haven't
   read yet.

3. **Don't treat a component name as the endpoint.** "XkBcjAction"
   was a breadcrumb from an earlier probe. The actual module is
   `xsxk`; the action methods are `add_xuanke` and `tuike`. Component
   names are HINTS to which bundle to download, not the answer.

4. **Don't claim a reference file exists when it doesn't.** I
   wrote a selectcourse commit message that pointed to
   `references/tis-api.md` for the open question — that file didn't
   exist at the time. Either write the doc first or remove the
   reference.

5. **Don't forget the session cookies.** Even within the same host,
   a fresh `requests.get()` call with just a URL gets 403 on the
   bundle (no JSESSIONID, no route cookie). Reuse the Session that
   did the CAS login.

6. **Don't conclude "no data exists" before trying the right time
   format.** If the API takes a `sysj` list, you must send it as
   a proper `sysj[0].zc` indexed binding, NOT as a JSON string.
   Spring will reject a JSON-stringified list with a confusing
   "typeMismatch" error and you'll think the endpoint is dead. The
   shape is in the bundle, READ IT.

7. **Don't stop at the first endpoint you find when the data
   doesn't match the question.** A search dialog's endpoint gives
   you search results, not live occupancy. A child component
   inside the dialog is the one with the data you actually need.

## What the resulting module looks like

For TIS specifically, the pattern became:

```python
class EnrollmentError(RuntimeError):
    """Raised when TIS rejects a write-side enrollment action."""
    def __init__(self, jg, message, *, endpoint, rwh): ...

def _build_queryform(self, *, rwh=None, xktjz=None, ...):
    """Mirror the 40-key queryform object from the bundle."""
    return {"p_pylx": ..., "p_xktjz": xktjz, "p_id": rwh, ...}

def _post_xsxk(self, endpoint, payload, *, dry_run, rwh):
    if dry_run:
        return {"dry_run": True, "would_post": payload, ...}
    sess = self._login_for_write()
    r = sess.post(endpoint, data=payload, timeout=30)
    res = r.json()
    if str(res.get("jg")) != "1":
        raise EnrollmentError(res.get("jg"), res.get("message"),
                              endpoint=endpoint, rwh=rwh)
    return res

def add_course(self, rwh, *, dry_run=True, ...):
    payload = self._build_queryform(rwh=rwh, xktjz="gwctjzyx", ...)
    return self._post_xsxk(TIS_ADD_XUANKE_URL, payload,
                           dry_run=dry_run, rwh=rwh)
```

Three principles that came out of the bundle walk:
- **Default to `dry_run=True`** on any state-mutating method
- **Mirror the form object literally** — don't second-guess field
  names or omit "unused" ones. TIS may validate them server-side
  even if the UI doesn't set them.
- **Test the dry-run path thoroughly**, mock-test the real-call
  path. The user will fire the real call themselves with `--no-dry-run`.

## Reusability for other SUSTech systems

This same recipe applies to:
- **PMS (cloud print)** — non-CAS auth, but the same SPA-bundle
  pattern. `pms/pms.py` already uses a session-aware custom auth.
- **ehall sub-apps** — see `references/ehall-booking-venue-2026-06-15.md`
  for the booking-venue sub-app, which has a CAS+token handshake
  plus bundle-walked action endpoints.
- **TIS 场地课表 (cdkb)** — see `references/tis-cdkb-live-occupancy-2026-06-28.md`
  for the cdkb/querycdkbList walkthrough using the
  didian → changdikebiao chain.
- **RSC, WoS, CNKI, NCES** — these are external platforms, not
  SUSTech-hosted SPAs. The recipe doesn't apply.
- **Any future SUSTech sub-app** that loads a hashed JS bundle.

## 🆕 Live wire-payload probe recipe (2026-06-29)

> **When to use this.** You already know the endpoint (via the
> recipe above) and want to capture the EXACT body the browser
> sends, **without making the destructive real call**.
> Per iron law #1, write-side endpoints (e.g. `cdjy/add...`)
> are destructive and need dry-run by default. This recipe lets
> you capture the wire shape from the live UI and reply with a
> fake success — no real application is created.

The static analysis (regex-over-page) tells you what the form
*would* send. The Playwright probe tells you what it *actually*
sends. They differ — and the diff is what matters.

### Steps

1. **Load session via TISAuth** (handles CAS + cookies).

2. **Open the page in Playwright**, inject the right `localStorage`
   if needed (TIS often reads `user` from `localStorage.getItem('user')`
   in `openAddDrawer`/similar). The Vue app reads user data from
   localStorage, not from a runtime global.

3. **Click the "add" button to open the drawer** (Vue drawer
   only mounts when opened). Wait for `addDrawer.cdjyshow === true`.

4. **Walk the Vue tree to find the right instance**. The page has
   1000+ Vue components; only one has `saveOrSubmit` /
   `cdjyform` / etc. Search by `el.__vue__.$options.methods`.

5. **Fill the form via direct Vue mutation** (bypasses the UI
   dropdowns which would take a long time). The Vue instance is
   just a plain object; you can write to `inst.cdjyform.X` and
   `inst.cdjyform.cdjymxlist[0].Y` directly.

6. **Bypass client-side validation** by patching
   `inst.$refs.cdjyform.validate = () => Promise.resolve(true)`.
   TIS uses iview's Form.validate which is async-Promise; the
   saveOrSubmit path will otherwise fail before reaching AJAX.

7. **Hook `$.ajax` BEFORE calling saveOrSubmit**. Patch
   `window.$.ajax` to record the URL/contentType/data into a
   global. The form's saveOrSubmit chains `.then(res => {...})`
   so you can't just call it sync and read the result — the
   AJAX fires inside the Promise chain.

8. **Call `inst.saveOrSubmit('bc')` directly** (bypasses the
   button click which would need real DOM interactions).

9. **Wait for `addDrawer.loading` to flip false** (means the
   AJAX completed). The captured body is in the hook global.

10. **Also patch `page.route()` with `route.fulfill` returning
    a fake success** so even if the AJAX reaches the network,
    no real write hits the server. **Critical for destructive
    endpoints** like cdjy.

### Key gotchas learned

- **iview Form.validate() returns a Promise** — replace it with
  `() => Promise.resolve(true)`, NOT a callback-style function.
  Using `function(cb) { cb(true); }` throws "cb is not a function"
  because the calling code is `validate().then(...)`.
- **The form's `__user` is read from `localStorage`**, not from
  a runtime variable. You must inject it manually before
  clicking the "add" button.
- **Vue component tree is huge (1000+ components)** — find the
  one with the right methods (`saveOrSubmit`, `updateOrSubmit`,
  `addjxx`, `copyData`), not just any with `__vue__`.
- **AJAX is wrapped in Promise chains** — by the time
  `inst.saveOrSubmit()` returns, the AJAX is in flight but the
  response hasn't come back. Wait on `addDrawer.loading` to flip
  false.
- **Destructive endpoints (cdjy, etc.) MUST use `route.fulfill`
  to short-circuit** — even with form validation bypassed, a real
  POST creates a real application. Use the fake-fulfill pattern.

### Reusable script

`~/.openclaw/code/sustech_survival/scripts/probe_cdjy_post.py` is
the worked example for the TIS 场地借用 create flow. It captures
the wire body, writes it to `/tmp/cdjy_post_payload.json`, and
saves a drawer screenshot to `/tmp/cdjy_debug.png` for visual
verification. Adapt the selectors and method-name filters for
other TIS modules.

### Companion doc

`references/tis-cdjy-post-probe-2026-06-29.md` is the full write-up
of the cdjy probe — including the 35/25/3 key breakdown, the
`shbj: 'bc' vs 'tj'` semantics, and the full code-change diff
to make `to_api()` match the wire.

For each, the recipe is the same: log in → find the right page →
download the bundle with `Referer` + cookies → grep for endpoints +
methods + form objects. The endpoint names will differ; the
discovery process won't.

## Files

- `references/tis-didian-room-search-2026-06-28.md` — sister walkthrough
  for the room-search discovery (the parent dialog's endpoint).
- `references/tis-cdkb-live-occupancy-2026-06-28.md` — sister walkthrough
  for the per-room live schedule discovery (the child component's
  endpoint). Includes the schedule entry shape, the SKSJ text format
  for 借用 vs 课程, the Spring `RoleCode` header, and the
  `sysj[0].zc` bitmask gotcha.
- `references/selectcourse-write-side-2026-06-19.md` — TIS-specific
  walkthrough with the exact bundle hash + method bodies (sister
  to the case studies above).
- `references/ehall-booking-venue-2026-06-15.md` — sister walkthrough
  for the ehall 场地预约 sub-app (different auth, same pattern).
- `src/sustech_survival/selectcourse/selectcourse.py` — the wrapped
  write-side code (4 methods, all `dry_run=True` default).
- `src/test/test_selectcourse_write.py` — 19 offline tests for the
  write-side (queryform shape, dry-run no-network, real-call mock,
  EnrollmentError attributes).
- `src/sustech_survival/classroom/live.py` — the cdkb integration
  (`LiveOccupancyClient`, `RoomScheduleEntry`, `parse_sksj`,
  `parse_key`, `current_semester`, `current_weekday_and_period`).
- `src/test/test_classroom_live.py` — 32 offline tests (parsers,
  RoomScheduleEntry, mocked client, `@pytest.mark.live` for
  live-server runs).
