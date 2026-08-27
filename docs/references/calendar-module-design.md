# Calendar module design — `sustech_survival.calendar`

> Reference doc for `sustech_survival/calendar.py`. Read this before
> touching anything that maps `xn/xq/slot.weeks` to actual dates.

## Why this module exists

Anything that converts a TIS class pattern (week bitmap + weekday +
periods) into actual calendar dates MUST go through this module, not
ad-hoc arithmetic like `teaching_start + 7 * (week - 1) + weekday`.
The ad-hoc version silently breaks on:

- Mid-semester teaching start (week 1 doesn't begin on a Monday)
- Compensatory days (补课) that REPLACE flushed holiday dates
- Midterm weeks (don't cancel classes — 不停课)
- Final weeks (do cancel classes)
- Extra breaks (校运会, sports day, etc.)

## Public API (locked-in design — don't add new enums or dataclasses)

```python
from sustech_survival.calendar import (
    AcademicCalendar, Semester, Day, ClassTime,
    Compensatory, Holiday,
    Weekday, Parity, CalendarError,
)

cal = AcademicCalendar.load(2026, level="undergraduate")  # online by default
sem = cal.spring                                       # or .fall / .summer

ct = ClassTime(
    weeks=(1, 3, 5, 7, 9, 11, 13, 15),
    weekday=0,                                         # 0=Mon..6=Sun
    periods=(1, 2),
    title="MSE202  材料科学",
    teacher="张老师",
    room="Y1-101",
)

ok: bool = sem.fill(ct)                                # True on add, False on dup / no-dates
dates: list[date] = sem.dates(ct)                     # actual meeting dates (with 补课 transfer)
day: Day = sem.day(date(2026, 3, 15))                 # Day with bool predicates
classes_today: list[ClassTime] = day.schedule          # which classes meet today
```

### Type conventions

- **`workday: Literal['Monday'..'Sunday']`** — never `str`. The `Literal`
  type gives IDE autocomplete and lets type-checkers catch typos.
- **`week_type: Literal['odd', 'even']`** — same reason.
- **`Day` predicates are bool methods** — no `DayKind` enum + `.kind`
  field. `Day.is_holiday()` / `is_compensatory()` / `is_extra_break()`
  / `is_final()` / `is_midterm()` / `is_weekend()` / `is_teaching_day()`
  / `has_class()`. The enums we tried all became awkward (predicates
  that should compose turn into `DayKind.X in {...}`; `Day.__str__`
  has to switch on the enum, etc.).
- **No `Schedule` dataclass** — `fill` returns `bool` and the
  computed dates live on the semester via `sem.dates(ct)`. Returning
  a Schedule object just to expose `(natural, actual, transfers)`
  makes the API wider without paying for itself.

### `AcademicCalendar.summer`

The online JSON's `summer_semester` block is **minimal** — it has only
`start` and `end`, not the full semester structure (`teaching_start`,
`sign_in`, `total_teaching_weeks`, midterm/final blocks,
compensatories). Treat it as `None` unless the payload has
`teaching_start`:

```python
summer_payload = sem_payload.get("summer_semester")
if summer_payload and "teaching_start" in summer_payload:
    summer = Semester.from_payload(summer_payload, level)
else:
    summer = None
```

When summer exists (offline, with full payload), the same Semester
API applies — fill / dates / day work identically.

## Compensatory transfer algorithm (the core correctness rule)

The right algorithm is **per-comp, not per-flush**. For each
compensatory day, find the holiday it replaces and pull the schedule
from there. After all compensatory are filled, REMOVE all holiday
schedules.

```python
def full_semester_schedule(semester, courses):
    # Step 1: natural dates (regular teaching)
    meetings = []
    for course in courses:
        for week in course.weeks:
            d = semester.date_of(week, course.weekday)
            if semester.classify(d) == "teaching":
                meetings.append((course, d))

    # Step 2: per-comp transfer (the CORRECT direction)
    for comp in semester.compensatories:
        flushed = find_nearest_holiday_for(comp, semester)
        if flushed is None: continue
        for course in courses:
            if course_matches(flushed, course, semester):
                meetings.append((course, comp.date))

    # Step 3: remove all holiday schedules
    meetings = [(c, d) for c, d in meetings if not is_holiday(d, semester)]
    return meetings
```

The WRONG algorithm — per-flush reverse (find the compensatory for
each holiday) — runs the lookup for every holiday instead of every
compensatory, and double-counts classes that should only be cancelled:

```python
# DON'T DO THIS
for flushed_date in holiday_dates:
    comp = find_compensatory_for(flushed_date, semester)
    if comp:
        transfer_to(comp)
    else:
        drop(flushed_date)
```

`find_nearest_holiday_for(comp)` and `find_compensatory_for(date)` are
inverse operations — choose the one whose input is the smaller set.
Compensatories are sparse (a handful per semester); holidays are denser.
Per-comp is cheaper.

## Week numbering — Monday-anchored

`teaching_start` is often mid-week (Spring 2026 starts Wed 2026-02-25).
Week 1 must still start on the Monday on/before that date
(2026-02-23 in this case). Both `date_of` and `week_of` MUST use the
same Monday anchor:

```python
def date_of(self, week, weekday):
    teaching_monday = self.teaching_start - timedelta(
        days=self.teaching_start.weekday()
    )
    return teaching_monday + timedelta(days=7 * (week - 1) + weekday)

def week_of(self, d):
    if not self.is_in_semester(d):       # sign_in ≤ d ≤ final_end
        return 0
    teaching_monday = self.teaching_start - timedelta(
        days=self.teaching_start.weekday()
    )
    return ((d - teaching_monday).days // 7) + 1
```

If they disagree (one anchored to `teaching_start`, the other to
`teaching_monday`), tests silently go wrong because compensatory
matching uses parity (odd/even) which depends on week number.

`_last_teaching_day` also uses the Monday anchor — Sunday of the last
teaching week = `teaching_monday + 7 * (last_teaching_week - 1) + 6`.

## Midterm vs final vs holiday handling

| Day type | Has class? | Notes |
|---|---|---|
| Regular teaching | yes | — |
| Compensatory (补课) | yes | Transferred classes from nearest flushed holiday |
| Holiday (national) | no | Dropped unless a compensatory exists |
| Final week | no | 复习考试周 — no regular class |
| Midterm week | yes | 不停课 — classes continue |
| Extra break (校运会, sports day) | no | In `semester.extra_breaks: set[date]` |
| Weekend (Sat/Sun, not comp) | no | — |

**Terminology (SUSTech academic context):** makeup class = **补课**, NEVER **补班** in user-facing messages or bug reports. 补班 is the labor-law term (national holiday makeup workday for civil servants); 补课 is the SUSTech / academic term. 调休 is also acceptable. This file is canonical — sibling `sustech-calendar-data-source.md` uses 补班 historically in the government-mandate context; ignore that usage for SUSTech user-facing copy.

`Day.is_teaching_day()` and `Day.has_class()` already encode this:

```python
def is_teaching_day(self) -> bool:
    if self.semester is None: return False
    if self.is_holiday() or self.is_compensatory(): return False
    if self.is_final() or self.is_extra_break(): return False
    if self.is_weekend(): return False                # weekends ≠ teaching
    return True

def has_class(self) -> bool:
    return self.is_teaching_day() or self.is_compensatory()
```

## Online vs local JSON

- **Default**: `AcademicCalendar.load(year, level="undergraduate")` reads
  from `https://raw.githubusercontent.com/dumixthestpd/sustech-calendar/main/{year}/`.
- **Local override**: `load(year, level, online=False)` reads from
  `~/Documents/sustech-calendar/{year}/`. Use ONLY when editing the
  JSON in progress — push local edits to GitHub so all users (incl. CI)
  see the same data.
- The local copy may be ahead of the remote during editing. The
  remote is the canonical source for runtime.

## ICS export (`selectcourse/ical.py`)

`courses_to_ical(semester) -> str` is a pure transform:

```python
for ct in semester.classes:
    for d in semester.dates(ct):                    # uses compensatory transfer
        for period in ct.periods:
            events.append(make_vevent(ct, d, period))
```

VEVENT uses China timezone; UTC at `DTSTART`/`DTEND`. Period start
times are in `PERIOD_START_TIMES` (50 min periods, 20-min break
between P2 and P3, 10-min break elsewhere):

| Period | Start (China) |
|---|---|
| 1 | 08:00 |
| 2 | 09:00 |
| 3 | 10:20 |
| 4 | 11:20 |
| 5 | 13:30 |
| 6 | 14:30 |
| 7 | 15:30 |
| 8 | 16:30 |
| 9 | 18:00 |
| 10 | 19:00 |
| 11 | 20:00 |
| 12 | 21:00 |

`webui/blueprints/tis.py` exposes this via `GET /api/tis/ical?xn=...&xq=...&picks=<JSON>`,
returning `text/calendar`. Browser trigger is `window.location = url`.

## Things to verify before committing calendar changes

1. `pdftotext -layout ~/Documents/sustech-calendar/2026/academic-calendar-2026.pdf`
   to read the grid (NOT `web_extract` — it flattens grid layouts).
2. Count grid rows per phase (春季学期 / 期中考试周 / 复习考试周 / 招生周).
   Don't count `招生周` (admissions) as a teaching week.
3. Diff every JSON field against the corresponding grid row.
4. Sanity-check `extra_breaks` dates with
   `python -c "from datetime import date; print(date(y,m,d).strftime('%A'))"`
   — Saturdays can never be school breaks.
5. For each compensatory, verify the work-week-parity (odd/even)
   matches the parity of the flushed holiday's Monday-of-that-week.
6. After changes, push to GitHub so online loader picks them up.

## Known bugs and false alarms (encountered during development)

- **Spurious `extra_breaks: ['2026-04-04']`** in spring JSON — Apr 4
  is a Saturday. Removed.
- **"Spring finals missing week 18"** false alarm — I "fixed" the
  final equivalent_weeks from `[16, 17]` to `[16, 17, 18]` thinking
  it was incomplete. The user caught it: spring is 17 weeks. The "18"
  came from including 招生周 (admissions week, a SEPARATE grid row) as
  a teaching week. JSON was actually correct all along.