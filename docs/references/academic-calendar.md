# SUSTech 校历 (academic calendar)


## SUSTech 校历 (academic calendar) — required for real calendar dates

Anything that maps `xn/xq/slot.weeks` to actual dates — .ics export,
"no class this week" badges on the weekly grid, exam-week banners — needs
the official 校历 data, NOT `xn/xq` math. Source repo:
`github.com/dumixthestpd/sustech-calendar` (user-maintained).

**Online is the canonical source, not the local copy.** The GitHub raw URL
(`https://raw.githubusercontent.com/dumixthestpd/sustech-calendar/main/{year}/`)
is treated as the server — every user, including CI, reads from the same
URL. The local repo at `~/Documents/sustech-calendar/{year}/` is for
editing the JSON in progress; after local edits are verified against the
校历 PDF (see below), push them to GitHub so everyone sees the update.
`AcademicCalendar.load()` defaults to `online=True`; pass
`online=False` only when iterating on local JSON edits. (User 2026-07-09
voice memo — explicit reversal of the prior "local canonical" rule.)

**SUSTech regulation facts (user 2026-07-08, verified against PDF 2026-07-09):**
- **National Day week IS a teaching week.** TIS's `slot.weeks` includes
  it; the counter still +1; classes really run that week. Do NOT exclude
  week 8 of fall term from calendar generation.
- **Midterm weeks (`midterm.equivalent_weeks`) do NOT cancel classes.**
  The label 不停课 means "no change to class schedule during midterms."
  These weeks should NOT be filtered out.
- **Final weeks (`final.equivalent_weeks`) DO cancel regular classes.**
  Skip events in those weeks.
- **Compensatory days (`compensatories[]`) are 补课** (makeup-class days) —
  NOT 补班 (which is the general HR/calendar term for compensatory
  *work* day). 补课 is a Saturday or Sunday designated as a teaching day
  to replace a class that was flushed by a holiday. Events on flushed
  dates get **transferred** to the matching compensatory date. Events
  with no matching compensatory are **dropped** ("flushed forever").
  Class name `Compensatory` in code matches the JSON field; docstrings
  use 补课 as the Chinese term. (User 2026-07-09 voice memo.)

The two-step ICS export rule (fill all events on natural dates, then
transfer-or-drop) is in `references/sustech-calendar-data-source.md`.
The compensatory day theory ("上单周周一的课"), the `midterm` vs
`final` naming gotcha, and the local-vs-remote rule are all in that
reference.

### 🚫 Trust the source PDF, not the derived JSON (user 2026-07-09)

The local `~/Documents/sustech-calendar/` JSON is derived from the
official 校历 PDF at
`https://www.sustech.edu.cn/uploads/files/2025/11/25155108_33786.pdf`
(landing: `https://www.sustech.edu.cn/zh/academic-calendar.html`).
The JSON can drift from the PDF — bugs in the JSON, missing entries,
misleading field names. **Always verify against the PDF before
trusting any calendar fact, especially week counts.**

### One bug found + one false alarm on 2026-07-09

**Real bug:**
- Spring `extra_breaks: ["2026-04-04"]` was spurious; Apr 4 is a Saturday and the PDF does not say "No classes" for it. Removed.

**False alarm (and the lesson):**
- I initially thought spring finals was missing week 18 — I "fixed"
  `[16, 17]` → `[16, 17, 18]` and committed. The user caught it:
  spring is 17 weeks, not 18. The 18 came from including 招生周
  (admissions week, a SEPARATE grid row) as a teaching week.
- Reverted. JSON was actually correct all along.

### 🚫 Don't trust `web_extract` for PDF grid layouts (the trap)

`web_extract` runs an LLM summarizer that flattens PDF grid layouts into
flowing prose. In the process it can:
- Merge adjacent rows (`第17周` 复习考试周 + `招生周` → "18 weeks").
- Drop the visual distinction between regular weeks, exam weeks, and
  admin weeks.
- Mislead you into "fixing" data that was actually correct.

**Use `pdftotext -layout` to preserve the grid:**
```bash
pdftotext -layout /Users/dumix/Documents/sustech-calendar/2026/academic-calendar-2026.pdf -
```
Then count grid rows (第N周 + 复习考试周 / 期中考试周 / 招生周) and verify
the sum. The row label is the source of truth, not the surrounding prose.

### Field-name pitfall

`midterm.equivalent_weeks` and `final.equivalent_weeks` read as "no class
these weeks", but only `final` actually cancels classes (midterm is
不停课). Both names are kept in the repo for downstream-compat reasons but
downstream code MUST read
`references/sustech-calendar-pdf-mapping-2026-07-09.md` before trusting
the field semantics. The doc also lists which PDF events are intentionally
NOT in the JSON (退补选课暨导师指导周, 重大活动 — informational,
non-class-canceling) so future agents don't re-add them.

### Methodology when auditing calendar facts

1. `pdftotext -layout <local-pdf> -` to read the grid (NOT `web_extract`)
2. Count grid rows per phase (春季学期 / 期中考试周 / 复习考试周 / 招生周)
3. Diff every JSON field against the corresponding grid row
4. Verify day-of-week with `python3 -c "from datetime import date; print(date(YYYY, M, D).strftime('%A'))"` —
   Saturdays have no regular classes, so any "extra_break" on a Saturday
   is suspect (probably a bug like the Apr 4 case)
5. Commit fixes to the local repo (it's ahead of GitHub remote, push
   separately when the user asks)

The full PDF→JSON field-by-field mapping (every JSON field traced to
its PDF grid-row source) is in
`references/sustech-calendar-pdf-mapping-2026-07-09.md`. Read this
before working with the calendar.

### Calendar module API conventions (`sustech_survival.calendar`)

The calendar package is the canonical answer to "what date does this
(week, weekday) fall on?" and "when do classes run during a comp day?".
Module path is `sustech_survival.calendar` (NOT `sustech_survival.cal`,
NOT `sustech_survival.semester` — that's the legacy TIS-code translator).

Full API + design rules + compensatory algorithm + ICS endpoint +
Authorizer API state + CLI mounting pattern are in
`references/calendar-architecture-2026-07-11.md`. Read that file
when working on the calendar module, ICS export, auth code, or
adding a new subcommand to the unified `sustech` dispatcher.

- **`ClassTime`** — the enrolled class entity: `weeks: tuple[int, ...]`,
  `weekday: int` (0=Mon..6=Sun), `periods: tuple[int, ...]`, plus
  metadata `title: str = ""`, `teacher: str = ""`, `room: str = ""`.
  A `ClassTime` IS the enrolled class — pattern + identity together.
- **`Compensatory`** — `date: date`, `week_type: Literal["odd","even"]`,
  `workday: Literal["Monday",..,"Sunday"]`. Class name matches JSON
  field `compensatories[]`. **Never use plain `str` for `workday`** —
  use the `Literal` type so IDE autocomplete and type-checkers catch
  typos.
- **`Holiday`** — `name`, `start`, `end`.
- **`Day`** — no `DayKind` enum. Bool methods only:
  `is_holiday()`, `is_compensatory()`, `is_extra_break()`,
  `is_final()`, `is_midterm()`, `is_weekend()`, `is_teaching_day()`,
  `has_class()`. Has a `.schedule: list[ClassTime]` property and
  human-readable `__str__`. Use `class Day` (not `DayInfo`).
- **`Semester.fill(class_time) -> bool`** — registers an enrolled
  class. Returns `False` if duplicate or if no dates could be computed.
- **`Semester.dates(class_time) -> list[date]`** — actual meeting dates
  for the class (with compensatory transfer applied). Singular input,
  no plural mismatch in the name.
- **`AcademicCalendar`** — `spring: Semester`, `fall: Semester`,
  `summer: Optional[Semester]`. `summer` is `None` when the JSON has
  only `start`/`end` (no `teaching_start`); build it only if the
  payload has the full structure. `load(year, level="undergraduate",
  online=True)` — online is the default and the canonical path.
- **`date in semester`** via `__contains__` (checks `sign_in ≤ d ≤ final_end`).
- **No `DayKind` enum, no `Schedule` dataclass** — both were tried
  and rejected. `Day` uses bool methods; the fill result is the
  semester's `classes` list, not a returned dataclass.
- **No Chinese in code, comments, docstrings, or variable names.**
  English only. If a Chinese term is the correct domain name (e.g.
  补课), put it in a docstring comment the first time and never
  mention the wrong name (补班) again.

**Compensatory transfer algorithm** (the core correctness rule):

```
for each compensatory day in compensatories:
    find the nearest holiday that flushed its (week_type, workday)
    pull the schedule from that holiday
fill in the compensatory day with those classes
after all compensatory are filled:
    REMOVE all holiday schedules (classes that weren't transferred are cancelled)
```

The wrong version (per-flush reverse, "for each flushed holiday find
the compensatory") runs the lookup more than necessary and is harder
to reason about. The correct version is per-comp: for each
compensatory day, find the holiday it replaces. (User 2026-07-09
voice memo.)

**Week numbering is Monday-anchored**: week 1 starts on the Monday
on or before `teaching_start`, even if teaching actually begins
mid-week (e.g. Wed). `date_of(week, weekday)` and `week_of(date)`
must use the same anchor — they disagree otherwise and tests
silently go wrong. `is_in_semester` uses `sign_in ≤ d ≤ final_end`,
which correctly excludes pre-orientation dates that fall in
"week 1" by the Monday anchor.

**Midterm weeks DO NOT cancel classes** (不停课). **Final weeks DO.**
The `Day` predicates reflect this: `is_final()` → no class;
`is_midterm()` → class continues.

### Holiday detection gotcha (encountered 2026-07-09)

The local JSON's `spring_semester.extra_breaks` field had a spurious
`"2026-04-04"` entry. April 4 is a Saturday — Saturday is never a
"no class" school day. Always sanity-check `extra_breaks` entries
against `date(y,m,d).weekday()` and remove any that fall on
Sat/Sun.

### TIS enrolled endpoint — slot dedup + field semantics (added 2026-08-09)

`my_courses()` returns N raw rows per rwh (one per lecture / lab / tutorial
/ 校区 / parity). Many of those rows describe the **same time slot**. If you
don't dedupe, `buildPackedItems` splits the course into N thin columns
instead of one full-width block. The user explicitly preferred the fix to
live in the **shared** `sectionsToBlocks` (not in an enrolled-specific
branch): *"shouldn't course grid display be uniformly coded and reused to
avoid logic concerns?"*

Three field semantics that the parser gets wrong if it trusts the names:

- `JSJC` = **end period (inclusive)**, NOT a count. With `KSJC=7, JSJC=8`
  the slot is periods 7-8, not 8 periods.
- `KEY`'s `jc<N>` = **class-block index on that day**, NOT period number.
- `ZC[i]=1` = week `i+1` is active. Position 0 is week 1, not pre-semester.

Full reproduction recipe + the canonical dedup key pattern +
before/after verification are in
`references/tis-enrolled-slot-dedup-and-field-semantics-2026-08-09.md`.

### TIS bid panel — locked-enrolled (added 2026-08-09, extended 2026-08-10)

When `IGNORE_TIS_ENROLLED` is off, the bid panel shows the user's
TIS-enrolled courses as **editable** bid boxes (🔒 badge + "Already
enrolled" note, but bid input works). Two bid stores coexist:
`PICKED_BIDS` for picks, `EXISTING_BIDS` for locked-enrolled rwhs the
user hasn't picked here. Five renderers/controllers all need
locked-enrolled branches (`bidShouldShow`, `renderBidPanel`,
`updateBidTotals`, `bidTotal`, `submitBids`, `loadEnrolled.then`),
plus the four edit handlers (`startBidEdit` / `onBidEditInput` /
`onBidEditKey` / `onBidEditBlur`) need `_bidRead` / `_bidWrite`
helpers to route reads/writes to the right store.

**The most common bug:** "locked" means the COURSE is locked
(can't be dropped / replaced by the solver), NOT the bid. TIS's
`updXkxsByyx` endpoint accepts bid updates on already-enrolled
sections. Refusing to expose the edit input silently drops bid
changes the user made. **User pushback (verbatim):** *"when i click
on the card of enrolled course i cannot change its bid wtf"*.

**The second most common bug:** `bidShouldShow()` requires picks
to be non-empty. Flipping the toggle off with zero picks leaves
the entire bid step blank — looks like the fix didn't work.
**User pushback (verbatim):** *"i don't see the fix. the bid panel
don't show my courses"*.

**The third (most insidious) bug:** the drag-to-transfer overlay
(`showTransferOverlay`) was the one bid-panel operation I missed
when building the multi-store helpers. The other handlers got
updated; this one still did raw `PICKED[srcRwh]` lookups, so any
drag involving a locked-enrolled box silently failed. **User
pushback (verbatim):** *"i cannot apply re-assigning bid from one
course to another if the course is enrolled in tis. why do they
have to behave differently?? you are obviously not reasonably
reusing and count how many wheels you rebuild"*.

The fix: a third helper `getCourseByRwh(rwh) = PICKED[rwh] ||
ENROLLED_DATA[rwh] || null` so all six bid-panel operations route
through the same lookup + read/write pair. The principle: **when
adding parallel-store support to a UI feature, factor the
difference into helpers at the FIRST branch, then audit every
other call site in the same file with `grep -n 'PICKED\['
src/.../tis.js` and `grep -n 'PICKED_BIDS\[' src/.../tis.js` to
find raw accesses that still bypass the helpers.** This bit me
because I shipped 5 commits that gradually updated call sites I
remembered, then a 6th commit caught the remaining hole. Don't
ship the helpers without a follow-up grep audit. Full cascade +
the wheel-rebuilding lesson + the audit recipe are in
`references/tis-bid-panel-locked-enrolled-2026-08-09.md`.

### One bug + one false alarm encountered 2026-07-09

**Real bug:** spring `extra_breaks: ["2026-04-04"]` was spurious;
Apr 4 is a Saturday and the PDF does not say "No classes" for it.
Removed.

**False alarm:** I initially thought spring finals was missing week
18 — I "fixed" `[16, 17]` → `[16, 17, 18]` and committed. The user
caught it: spring is 17 weeks, not 18. The 18 came from including
招生周 (admissions week, a SEPARATE grid row) as a teaching week.
Reverted. JSON was actually correct all along.
