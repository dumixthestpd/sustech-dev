## Display rules for course UI (TIS-specific)

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
