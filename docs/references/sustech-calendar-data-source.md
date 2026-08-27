# SUSTech 校历 (academic calendar) data source

> **When to use this.** Anything involving real calendar dates in the
> SUSTech webui: .ics calendar export, "no class this week" indicators
> on the weekly grid, exam-week banners, scheduling-tool date arithmetic.
> Anything you think you can compute from `xn` / `xq` alone — you can't,
> not accurately. **Use this data.**

## ⚠️ Source of truth: local copy, not the GitHub remote

The user's local repo at `~/Documents/sustech-calendar/` is **ahead of
the GitHub remote** (`github.com/dumixthestpd/sustech-calendar`). As of
2026-07-08 the local copy has 3 unpushed commits including Fall 2026
data and a refined schema (the older `special_days` blob was split into
`compensatories`, `extra_breaks`, `holidays`, etc.).

**Rule:** when reading or reasoning about this data, prefer the local
file over the GitHub URL. The local one is the authoritative version
that the user has been actively editing.

```
# Authoritative paths on this machine
LOCAL_GENERAL    = ~/Documents/sustech-calendar/2026/general.json
LOCAL_UNDERGRAD  = ~/Documents/sustech-calendar/2026/undergraduate.json
LOCAL_GRADUATE   = ~/Documents/sustech-calendar/2026/graduate.json
LOCAL_PDF        = ~/Documents/sustech-calendar/2026/academic-calendar-2026.pdf

# GitHub remote (stale — only use if local is unavailable)
REMOTE = https://raw.githubusercontent.com/dumixthestpd/sustech-calendar/main/2026/{general|undergraduate|graduate}.json
```

**If you ever have to re-derive field names from the GitHub URL** and
the local file contradicts, the local file wins. Same shape-of-truth
principle as reading source code instead of docs.

## Files in the local repo

| File                                          | Contents                                                              |
|-----------------------------------------------|-----------------------------------------------------------------------|
| `2026/general.json`                           | `holidays[]` (national) + `compensatory_workdays[]` (ISO date strings) |
| `2026/undergraduate.json`                     | `winter_holiday` + `spring_semester` + `summer_semester` + `summer_holiday` + `fall_semester` blocks |
| `2026/graduate.json`                          | Same shape as undergraduate                                          |
| `2026/academic-calendar-2026.pdf`             | Original PDF (2 pages, Chinese-left + English-right columns)         |

## Current field shape (local 2026)

```json
{
  "holidays": [
    {"name": "春节", "start": "2026-02-15", "end": "2026-02-23"},
    {"name": "国庆节", "start": "2026-10-01", "end": "2026-10-07"}
  ],
  "compensatory_workdays": ["2026-02-28", "2026-05-09", "2026-09-20", "2026-10-10"]
}
```

```json
{
  "winter_holiday": {"start": "...", "end": "..."},
  "spring_semester": {
    "start": "...", "end": "...", "sign_in": "...", "teaching_start": "...",
    "freshman_arrival": "...",
    "total_teaching_weeks": 15,
    "midterm": {"start": "...", "end": "...", "equivalent_weeks": [8, 9]},
    "final":   {"start": "...", "end": "...", "equivalent_weeks": [16, 17]},
    "compensatories": [
      {"date": "2026-02-28", "week_type": "odd",  "workday_type": "Monday"},
      {"date": "2026-05-09", "week_type": "odd",  "workday_type": "Tuesday"}
    ],
    "extra_breaks": ["2026-04-04"]
  },
  "fall_semester": {
    "start": "2026-09-01", "end": "2027-01-11", "sign_in": "2026-09-04",
    "teaching_start": "2026-09-07", "freshman_arrival": "2026-08-17",
    "total_teaching_weeks": 16,
    "midterm": {"start": "2026-10-26", "end": "2026-11-08", "equivalent_weeks": [8, 9]},
    "final":   {"start": "2026-12-28", "end": "2027-01-08", "equivalent_weeks": [17]},
    "compensatories": [
      {"date": "2026-09-20", "week_type": "odd", "workday_type": "Friday"},
      {"date": "2026-10-10", "week_type": "odd", "workday_type": "Wednesday"}
    ],
    "extra_breaks": ["2026-11-20"]
  }
}
```

## Naming quirks — read carefully

The field names are misleading if you take them literally:

- **`midterm.equivalent_weeks: [8, 9]`** — sounds like "these weeks have
  NO classes" but the actual SUSTech regulation is 不停课 (classes run
  normally). These weeks are a **midterm period label** for the
  instructor/student to know midterms are happening, not a class-
  cancellation flag. **Do NOT skip these weeks in calendar generation.**

- **`final.equivalent_weeks: [16, 17]`** (or `[17]`) — these ARE real
  class-cancellation. Final exam weeks have no regular class meetings.
  In ICS export, skip events where `slot.week in final.equivalent_weeks`
  OR `slot.week > total_teaching_weeks`.

- **`compensatories[]` `week_type: "odd"`** — paired with
  `workday_type: "Monday"` etc., this tells you WHICH (week-parity,
  weekday) class is being made up. NOT a constraint on which courses
  are affected. (See the transfer rule below.)

## The compensatory day theory (transfer rule)

Background: the Chinese government mandates multi-day national holidays
(e.g. 国庆节 Oct 1-7) and requires workers to "make up" the lost work
days by working on the adjacent Sat/Sun. These makeup days are
**补班** (būbān). When SUSTech gets a 补班, the calendar marks it
as a `compensatories[]` entry — a Saturday or Sunday designated as a
workday for the lost class time.

**The phrase "上单周周一的课"** (literally "conduct the class of
Monday-of-odd-weeks") is the instruction that appears on the 补班 day.
It means: "the Monday class that was scheduled for an odd-numbered
week but got flushed by a holiday, conduct it today on this
compensatory workday instead."

### The two-step ICS rule (verified with user 2026-07-08)

For each course's `slot.weeks[N]` with weekday=W (Mon=1..Sun=7):

```python
def course_events(courses, semester, calendar):
    sem = calendar[semester]                       # fall_semester etc.
    teaching_start = parse_date(sem["teaching_start"])
    total_weeks    = sem["total_teaching_weeks"]
    # Class-cancellation days (NOT midterm weeks — those don't cancel)
    flushed_dates  = set(expand_ranges(calendar["holidays"]))
    flushed_dates |= set(sem["extra_breaks"])
    compensatories = sem["compensatories"]

    # ── Step 1: fill in all events on their natural date ────────
    # No "is this a holiday?" check. Every (course × slot × week) exists.
    events = []
    for course in courses:
        for slot in course.slots:
            for week in slot.weeks:
                if week in sem["final"]["equivalent_weeks"]: continue  # finals = no class
                if week > total_weeks: continue
                date = teaching_start + timedelta(days=(week-1)*7 + (slot.weekday-1))
                events.append(VEvent(course, slot, date, week))

    # ── Step 2: transfer events on flushed dates, or drop them ──
    # Conditional transfer: only if a matching compensatory exists.
    # If no match: the event is dropped (the class is "flushed forever"
    # — no makeup, no calendar entry).
    for e in list(events):
        if e.date not in flushed_dates: continue
        comp = find_comp(compensatories,
                         week_type="odd" if e.week % 2 else "even",
                         workday=WEEKDAY_NAME[e.weekday])
        if comp:
            e.date = parse_date(comp["date"])
        else:
            events.remove(e)
    return events
```

**Why fill-then-transfer rather than skip-on-flush:** it makes the
logic checkable. Step 1 is a pure date computation — no calendar
awareness. Step 2 is the only piece that knows about holidays. Testing
becomes: "give it a courses list and a calendar, count events at each
date, that's the answer."

**Why drop rather than mark cancelled (e.g. STATUS:CANCELLED):**
the ICS is for things that actually happen. A class that didn't run
has no place in the calendar. The user pushed back explicitly on
adding `STATUS:CANCELLED` — YAGNI. If a class is "flushed forever",
it's gone.

## What's NOT in this data

- **Period → time mapping.** Period 1 = 08:00, period 2 = 08:55, etc.
  (SUSTech standard, 45-min periods + 5-min break.) This is schedule
  convention, not calendar data — belongs as a constant in
  `sustech_survival/selectcourse.ical.py`. Verify against
  `classroom.classroom` live data before hardcoding.
- **Course-specific 停课 dates** (an instructor's personal
  cancellation). TIS's `slot.weeks` already excludes these.
- **2027+ data.** Add new `{YEAR}-{program}.json` files to the local
  repo when SUSTech publishes. Don't fabricate.

## Quick reference: what to skip vs include

| Field                                    | Skip events? | Why                                           |
|------------------------------------------|--------------|-----------------------------------------------|
| `holidays[]` ranges                      | YES (per-date, transfer to compensatory) | National holiday days                          |
| `extra_breaks[]` (e.g. 校运动会)         | YES (drop)   | One-day stop-class events with no makeup      |
| `compensatories[]` `workday_type` matches| TRANSFER     | Move VEVENT from holiday date to here          |
| `compensatories[]` no match              | DROP         | "Flushed forever" — no class that session     |
| `midterm.equivalent_weeks`               | NO           | 不停课 — classes continue normally            |
| `final.equivalent_weeks`                 | YES          | Real class-cancellation for finals             |
| `slot.week > total_teaching_weeks`       | YES          | Beyond teaching period                        |

## See also

- `references/tis-kclbdm-discovery-2026-07-08.md` — companion: once
  this data + kclbdm are both available, .ics export is unblocked
- `references/spa-js-bundle-walk-recipe.md` — how to find TIS endpoints
  for the course schedule data (the data side, not the calendar side)
- TODO(ical) marker in `src/sustech_survival/webui/blueprints/tis.py` —
  the location where the blueprint will mount this work when wired up