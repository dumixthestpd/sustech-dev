# TIS SPA menu discovery — the technique brute-probe CAN'T find (2026-06-28)

## The lesson

If your task is "does TIS have feature X?" or "where in the TIS UI
is feature X?", and X is not visible in any page's static HTML, you
are about to fail. Stop, drive the UI, and read the menu API.

**Anti-pattern:** `for ep in guessed_candidates: sess.get(ep)` —
relies on guessing URL prefixes. Misses any feature whose path
doesn't match your guesses.

**Correct pattern:** drive the actual student portal in a real
browser, capture the menu API calls, enumerate every menu item by
its category code (`qxdm`), then walk to the URL the menu item
points to.

## The recipe (works on `tis.sustech.edu.cn`)

### Step 1 — Drive the UI

```python
from playwright.sync_api import sync_playwright
import requests, re
from sustech_survival.classroom.live import _tis_login
from sustech_survival.sso import Authorizer

creds = Authorizer()
uname, pw = creds.read_creds()

# Headless CAS login → cookies
sess = requests.Session()
sess.headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
r = sess.get("https://cas.sustech.edu.cn/cas/login", params={"service": "https://tis.sustech.edu.cn/cas"}, timeout=30)
m = re.search(r'name="execution" value="([^"]+)"', r.text)
exec_token = m.group(1)
r = sess.post("https://cas.sustech.edu.cn/cas/login", params={"service": "https://tis.sustech.edu.cn/cas"},
              data={"username": uname, "password": pw, "execution": exec_token,
                    "_eventId": "submit", "submit": ""},
              allow_redirects=False, timeout=30)
ticket_url = r.headers.get('Location', '')
sess.get(ticket_url, allow_redirects=True, timeout=30)

# Inject into Playwright
pw_cookies = [
    {"name": c.name, "value": c.value, "domain": c.domain or "tis.sustech.edu.cn", "path": c.path or "/"}
    for c in sess.cookies
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    context.add_cookies(pw_cookies)
    page = context.new_page()

    # IMPORTANT: TIS has heavy JS polling. `networkidle` will hang.
    # Use `commit` and sleep instead.
    page.goto("https://tis.sustech.edu.cn/student_index",
              timeout=60000, wait_until="commit")
    time.sleep(15)  # let SPA + i18n load

    # The menu is now rendered. Capture visible text.
    print(page.inner_text("body"))
```

### Step 2 — Fetch the menu tree via the right API

The student menu lives behind two endpoints, both POST:

```python
sess.headers['X-Requested-With'] = 'XMLHttpRequest'
sess.headers['RoleCode'] = '00'

# Top-level categories (4 total for undergrad)
r = sess.post("https://tis.sustech.edu.cn/user/mk", data={})
top = r.json()  # list of {qxdm, qxmc, qxmc_en, icon, ...}

# Children for one category (POST with mkdm[] as a LIST parameter)
r = sess.post("https://tis.sustech.edu.cn/user/getMknodeMore",
              data={'mkdm[]': qxdm})
# Returns: {<qxdm>: [{qxdm, fqxdm, qxmc, url, ...}, ...]}
```

**Gotcha #1 — `mkdm[]` is a Spring `@RequestParam List<String>`.**
You MUST send it as a repeated parameter (form data), not a single
JSON array. `requests.post(data={'mkdm[]': qxdm})` works because
`requests` serializes that one-key dict as `mkdm[]=002`. To send
multiple: `data=[('mkdm[]', '002'), ('mkdm[]', '102'), ...]`.

**Gotcha #2 — the parameter name is `mkdm[]` not `mkdm`.** Without
the `[]`, the server returns `Required request parameter 'mkdm[]'
for method parameter type List is not present`.

**Gotcha #3 — the response is a dict keyed by `qxdm`, not a list.**
Top-level `/user/mk` returns a list, but children
`/user/getMknodeMore` returns `{qxdm: [items]}` so it can answer
multiple parents in one call.

### Step 3 — Walk recursively if needed

```python
def walk(qxdm, depth=0):
    r = sess.post("https://tis.sustech.edu.cn/user/getMknodeMore",
                  data={'mkdm[]': qxdm})
    items = r.json().get(qxdm, [])
    for item in items:
        print('  ' * depth + f"[{item['qxdm']:8s}] {item['qxmc']:30s} → {item.get('url', '')}")
        # If it has children (qxdm starts with the parent's qxdm prefix),
        # recurse — but BEWARE infinite loops on cycles.
```

### The 4 top-level categories for undergrad student (verified 2026-06-28)

| qxdm | qxmc | qxmc_en | Has "借用/申请/教室/场地/预约"? |
|---|---|---|---|
| 002 | 业务查询 | Academic Information | No |
| **102** | **业务办理** | **Academic Services** | **Yes — has 场地借用申请** |
| 007 | 选课业务 | Course Registration | No |
| 16 | 大学生创新训练计划 | Undergraduate Innovation Research Program | No |

13 items live under 102. The interesting one for venue booking:

```
[10267   ] 校外学分认定申请 → /jljh/xwxfrd/...
[102008  ] 成果收集申请 → /cgsj/...
...
[1020009991] 校外学分认定（辅修）
[1020088] 场地借用申请 → /cdjy/query/1/sq      ← THE BOOKING PAGE
[102...  ] 预毕业证明打印申请
...
```

Other items in 102 include 评教任务, 保研申请, 学籍异动, 选专业申请,
辅修专业申请 — all student-facing academic services.

## i18n bundles — where the Chinese labels come from

Once you find a menu item (e.g. `场地借用申请`), the page labels
(e.g. `添加场地借用`, `学年学期`, `审核状态`) come from i18n
bundles. To read all of them without driving the UI:

```python
bundles = ['messages', 'messages2', 'ksgl', 'xwgl', 'pkgl', 'xkgl',
           'cxcy', 'cjgl', 'jljh', 'jsfz', 'zzz', 'bysj', 'jsgl', 'pyfa']

for b in bundles:
    r = sess.get(f"https://tis.sustech.edu.cn/{b}_zh_CN.properties?_=1")
    if r.status_code == 200:
        # Chinese is Unicode-escaped: \u501F\u7528 = 借用
        text = r.text.encode('utf-8').decode('unicode_escape')
        # search for keywords...
```

URL pattern is **`/<bundle>.properties`** (NOT `/messages/<bundle>`).
Bundles that are JS-rendered via jQuery.i18n.properties; `_zh_CN`
suffix is the Chinese variant. Bundle prefixes map to menu sections:
- `ksgl` = 考试管理 (exam management)
- `xwgl` = 学位管理 (degree management)
- `pkgl` = 排课管理 (course scheduling)
- `xkgl` = 选课管理 (course selection)
- `cxcy` = 创新创业 (innovation/entrepreneurship)
- `cjgl` = 成绩管理 (grade management)
- `jljh` = 教学计划 (teaching plan)
- `jsfz` = 教师发展 (teacher development)
- `zzz` = 自助 (self-service)
- `bysj` = 毕业设计 (graduation project)
- `jsgl` = 教室管理 (classroom management — probably teacher-side)
- `pyfa` = 培养方案 (training program)

Note: `cdjy` does NOT have its own i18n bundle. Its labels are
probably inline in the page HTML / loaded from a per-page component
bundle.

## Why brute-probing missed `cdjy`

The brute-probe that found "no TIS booking endpoint" tried these
prefixes:
- `cdsq` (场地申请)
- `cdyy` (场地预约)
- `jsjy` (教室借用)
- `jssq` (教室申请)

But TIS uses **`cdjy`** (场地借 — venue borrow). `jy` = 借 (borrow),
not `sq` (apply) or `yy` (reserve). The reason the user got it right:
they actually USE the system; we just guessed prefixes.

## When to apply this recipe

ANY time you need to find a feature that:
- Doesn't appear in any page's static HTML
- Has a Chinese UI label but no obvious URL mapping
- Is mentioned in conversation but not in any catalog you have

If you find yourself writing `for url in [guess1, guess2, ...]:
sess.get(url)` — STOP. Drive the UI first.

## Pitfalls / gotchas

- **TIS never goes idle.** Playwright `wait_until="networkidle"` will
  hang for 60s+ because the SPA polls. Use `wait_until="commit"` and
  `time.sleep(15-20)` instead.
- **CAS SSL handshake sometimes times out.** Use retries:
  `for attempt in range(3): try... except: time.sleep(2)`.
- **Cookie domain.** When injecting into Playwright, set the cookie
  domain to `tis.sustech.edu.cn` (NOT `cas.sustech.edu.cn` — the CAS
  cookies won't help TIS).
- **RoleCode header is required for menu APIs.** `sess.headers['RoleCode'] = '00'`.
  Without it, you get Spring 415 or empty responses.
- **The menu changes per role.** This recipe shows the undergrad
  student menu. Teacher / admin / grad-student menus will be
  different — different `/user/mk` response, different child sets.
  Always drive the UI as the target role, not assume.