# TIS "what week is today" — dead-end brute-probe + working heuristic

> **Session context.** 2026-06-28, while closing the `_infer_current_week()`
> TODO in `classroom/live.py`. The naive placeholder (returns 1) needed to
> become a real inference. **TIS does NOT expose a "current week" endpoint
> to student sessions** — every plausible candidate returns empty `{}` or
> 404. This file captures the full dead-end probe list so future sessions
> don't re-walk it, plus the heuristic that DOES work.

## TL;DR — the heuristic

```python
# In classroom/live.py:current_week(xn, xq, today=None)
from sustech_survival.context import ACADEMIC_CALENDARS

# 1. Look up (xn, xq) in ACADEMIC_CALENDARS via reverse-mapping
#    label "2026 Spring" → xn="2025-2026" + xq="2"
# 2. Round semester_start UP to the next Monday (TIS week 1 anchor)
# 3. If today < anchor: return 1 (partial first week, classes have started)
# 4. Else: week = (today - anchor).days // 7 + 1
# 5. If today is in spring_break: snap to week of break START
```

**The single non-obvious rule:** for a Tuesday-start semester (e.g.
Spring 2026 with `semester_start = Tue Feb 24`), TIS week 1 starts on
the **NEXT** Monday (Mar 2), not the preceding one. The partial Mon-Sun
week before it (Tue Feb 24 - Sun Mar 1) is "week 0" / pre-class. The
borrowings distribution for YJ-123 confirms this: weeks 1-17, no week 0,
today (Sun Jun 28) is the LAST day of week 17.

## TL;DR — the dead-end endpoints

All brute-probed 2026-06-28 against the live TIS server with a valid
student CAS session. **None of these expose a week→date mapping.** Don't
re-walk:

| Endpoint | Status | Response |
|---|---|---|
| `component/queryRlZcSj` | 200 | `{"content": {}}` — empty |
| `cdkb/queryRlZcSj` | 404 | Spring 404 |
| `Xsxk/getCurrentWeek` | 404 | Spring 404 |
| `xsxk/getCurrentWeek` | 404 | Spring 404 |
| `component/getCurrentWeek` | 404 | Spring 404 |
| `component/dqzc` | 404 | Spring 404 |
| `component/queryDqZc` | 404 | Spring 404 |
| `component/getXnxqSj` | 404 | Spring 404 |
| `XkBcj/getXnxqCalendar` | 404 | Spring 404 |
| `kbcj/queryDqZc` | 404 | Spring 404 |
| `cdkb/queryCdCalendar` | 404 | Spring 404 |
| `cdkb/queryXnxqCdjy` | 404 | Spring 404 |
| `cdkb/dqZc` | 404 | Spring 404 |
| `component/dqKxrq` | 404 | Spring 404 |
| `component/queryKxrq` | 404 | Spring 404 |
| `component/dq_xnxq_kxrq` | 404 | Spring 404 |
| `Xsxktz/queryXnxqCdjy` | 404 | Spring 404 |
| `teacher/venueBooking` | 404 | Spring 404 |
| `component/queryXnxqCdjy2` | 404 | Spring 404 |
| `component/xnxqCdjy` | 404 | Spring 404 |
| `component/queryCdjy` | 404 | Spring 404 |
| `component/queryXqCdlb` | 404 | Spring 404 |
| `component/queryXnxqRl` | 404 | Spring 404 |
| `component/queryXnxqSj` | 404 | Spring 404 |
| `component/dq_xnxq_cdjy` | 404 | Spring 404 |
| `XkBcjAction/getXnxqCalendar` | 404 | Spring 404 |

**Note on `component/queryXnxqCdjy`** (the one that returns 200): it
returns the semester metadata list, NOT a week→date mapping. Fields
like `xnxq`, `rwxnxq`, `xqs`, `zc` are all NULL on the public catalog
API. The body looks like:

```json
[
  {"xn":"2027-2028","xq":"1","xnmc":"2027","xqmc":"秋季",
   "kyf":"1","sfdqxq":"0","xnxq":null,"rwxnxq":null,"xqs":null,"zc":null},
  {"xn":"2026-2027","xq":"1","xnmc":"2026","xqmc":"秋季",...},
  {"xn":"2025-2026","xq":"2","xnmc":"2026","xqmc":"春季",
   "kyf":"1","sfdqxq":"1","xnxq":null,"rwxnxq":null,"xqs":null,"zc":null},
  ...
]
```

**The only useful field here is `sfdqxq="1"`** — that marks the current
semester. Use it to pick `(xn, xq)` from the list when you don't
already know it (alternative to `component/dq_xnxq`).

## Why brute-probing was the wrong move (and is always the wrong move)

Per `references/spa-js-bundle-walk-recipe.md`: SPA endpoints live in
hashed JS bundles, not at guessed URL paths. The recipe is:

1. Find the page that has the feature (Xsxk/query/1 for selectcourse,
   the personal schedule page, etc.).
2. Walk the JS bundles for that page.
3. Grep for endpoints + queryform/payload shapes.

The `queryRlZcSj` empty-{} response MIGHT be readable from a teacher
or admin bundle — but we don't have those credentials, so it's a
dead end for student sessions either way. If a future session needs
this for an admin/teacher role, the path forward is "find the page
that displays the calendar widget, walk its bundle" — not brute-probing.

## The heuristic in detail — and how to verify it

### What `ACADEMIC_CALENDARS` provides

In `sustech_survival/context/__init__.py`:

```python
ACADEMIC_CALENDARS = {
    "2026 Spring": {
        "semester_start": "2026-02-24",      # Tue — first class day
        "spring_break":  ("2026-04-04", "2026-04-12"),
        "semester_end":   "2026-06-28",
        "summer_start":   "2026-06-29",
    },
    "2025 Fall": {
        "semester_start": "2025-09-01",      # Mon — already a Monday
        "spring_break": None,
        "semester_end":   "2025-12-28",
        "summer_start":   "2025-12-29",
    },
}
```

Reverse-map: `xn="2025-2026" + xq="1"` → `"2025 Fall"`, `xq="2"` →
`"2026 Spring"`. There is no Summer entry yet (xq="3").

### TIS week numbering — the convention

TIS weeks are Mon-Sun and are numbered from the **first FULL Mon-Sun
week that follows `semester_start`**. Implications:

- **Mon-start semester** (Fall 2025, `semester_start=Mon Sep 1`):
  TIS week 1 = Mon Sep 1 - Sun Sep 7. Anchor = `semester_start`.
- **Tue/any-other-start semester** (Spring 2026, `semester_start=Tue Feb 24`):
  TIS week 1 = Mon Mar 2 - Sun Mar 8. Anchor = next Monday after
  `semester_start`. The days Tue Feb 24 - Sun Mar 1 are "week 0"
  (pre-class / orientation / registration).

### The full formula

```python
def current_week(xn, xq, today=None):
    # 1. Reverse-map (xn, xq) → ACADEMIC_CALENDARS entry
    # 2. Get semester_start, semester_end
    # 3. If today not in [semester_start, semester_end]: return None
    # 4. anchor = _first_full_week_start(semester_start)  # round UP to next Mon
    # 5. If today < anchor: return 1  # partial first week
    # 6. If today in spring_break: snap to break-start week
    # 7. return (today - anchor).days // 7 + 1
```

### Empirical verification (the gold standard)

The borrowings distribution in `cdkb/querycdkbList` is the ground
truth. For a heavily-used room (YJ-123 verified 2026-06-28):

```python
from collections import Counter
from sustech_survival.classroom.live import parse_sksj, parse_key
entries = client.query_room("YJ-123", xn="2025-2026", xq="2")
week_counter = Counter()
for e in entries:
    k = parse_key(e["KEY"])
    s = parse_sksj(e["SKSJ"], e.get("SKSJ_EN", ""))
    if k and s and s["type"] == "borrowing":
        for w in s["weeks"] or []:
            week_counter[w] += 1
# Result 2026-06-28:
#   Week  1: 8 borrowings, Week  2: 4, ..., Week 17: 30, NO week 18
#   → today is in week 17, last day of semester
```

Use this technique to verify any future semester's heuristic:
- Count borrowings per week for a busy room.
- The maximum week = the last week of teaching.
- If today is in that week (and it's the last day of semester per
  `ACADEMIC_CALENDARS.semester_end`), the heuristic is correct.

## The 三教 (LH3-*) mystery — not blocking

While verifying via borrowings, noticed that 三教 rooms (LH3-XXX codes,
56 rooms in the `queryDiDian` inventory) return **0** cdkb entries.
Same for `Xsxktz/queryRwxxcxList` — no 三教 slots in the public catalog.

| Building | Code prefix | cdkb entries | Catalog slots |
|---|---|---:|---:|
| 一教 | `YJ-XXX` | 53-117 | yes |
| 智华楼 | `ZH-XXX` | 134-151 | yes |
| 三教 | `LH3-XXX` | **0** | **0** |
| 工学院 | `GC-XXX` | 0 | few |

Likely explanations: (a) renovation / out of service this semester,
(b) schedule only kept on teacher/admin side, (c) different internal
code we haven't discovered. **Treat as "no data available to students"
in the SKILL.md known-limitations.** Don't waste a future session
trying to discover a different code unless we get a teacher-side hint.

## What this means for the `classroom` module

- `live.current_week(xn, xq)` works for Spring 2026 + Fall 2025
  (the entries currently in `ACADEMIC_CALENDARS`). Returns `None`
  for unknown semesters, before semester_start, after semester_end.
- `classroom now <room>` now produces a real week number in its
  output header (e.g. `week 17, weekday=7 周日, period 5`) instead
  of the previous `week 1` placeholder.
- To extend to future semesters, add an entry to `ACADEMIC_CALENDARS`
  in `sustech_survival/context/__init__.py` with `semester_start`
  (first class day) + `semester_end` + optional `spring_break`.

## Lessons learned

1. **Don't brute-probe for hidden endpoints** — read the JS bundle.
   Even when a feature seems "obviously should be available," if
   20+ candidates are all dead, it's not a brute-probe problem,
   it's a "this endpoint doesn't exist for this role" problem.
2. **Verify heuristics empirically** with the data you DO have.
   The borrowings distribution revealed the TIS week numbering
   convention; no amount of guessing would have produced it.
3. **The "obvious" heuristic** (`(today - semester_start).days // 7 + 1`)
   is OFF BY ONE for non-Monday-start semesters. The fix (round
   semester_start UP to the next Monday) is small but the discovery
   of WHY it's needed only came from the borrowings check.
4. **ACADEMIC_CALENDARS is the source of truth** for the heuristic.
   To extend to new semesters, edit `context/__init__.py`. The
   existing `get_academic_info()` there also computes the week but
   has the off-by-one bug — not used by `live.current_week`.

## See also

- `references/spa-js-bundle-walk-recipe.md` — the recipe that
  should have been used instead of brute-probing.
- `references/tis-cdkb-live-occupancy-2026-06-28.md` — sister
  walkthrough for the per-room schedule endpoint that we used to
  verify the week convention via borrowings distribution.
- `references/tis-didian-room-search-2026-06-28.md` — the
  `queryDiDian` walkthrough; explains the room inventory used
  for the 三教 verification.
- `sustech-dev/SKILL.md` §4 — the broader investigation plan,
  TODO #4 marked done with the round-UP rationale.
- `sustech/classroom/SKILL.md` — user-facing docs for `classroom now`
  and the `current_week()` helper.
- `src/sustech_survival/classroom/live.py:current_week` — the
  implementation (with full docstring).
- `src/test/test_classroom_live.py:TestCurrentWeek` — 9 offline
  tests covering the round-UP rule, partial first week, spring
  break snap, out-of-window, unknown semester, Fall start.