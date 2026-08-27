# SUSTech Calendar: PDF → JSON mapping (verified 2026-07-09)

**Source PDF:** https://www.sustech.edu.cn/uploads/files/2025/11/25155108_33786.pdf
**Landing page:** https://www.sustech.edu.cn/zh/academic-calendar.html
**Local repo (canonical):** `/Users/dumix/Documents/sustech-calendar` (always ahead of GitHub remote)
**JSON files:** `2026/undergraduate.json`, `2026/graduate.json`, `2026/general.json`

## Why this document exists

The calendar JSON is the source of truth for ICS export. The PDF is the upstream source.
The PDF and JSON have to stay in sync. This document is the bridge: for every field
in the JSON, which PDF line does it come from, and what was *not* captured (and why).

---

## 🚫 Read the PDF grid, NOT the linearized English summary

This bit me hard on 2026-07-09. I used `web_extract` to read the PDF, and got a
nice English summary that said "Spring Semester (18 Weeks)". I "fixed" the JSON
based on that — changed `[16, 17]` → `[16, 17, 18]`. The user caught me: spring is
actually 17 weeks. The 18 came from including 招生周 (admissions week, a separate
grid row) as a teaching week.

**The trap:** `web_extract` runs an LLM summarizer that flattens the PDF's
two-column grid layout into flowing prose. In the process, it can merge
adjacent rows (招生周 + 第17周 → "18 weeks") and drop the visual distinction
between regular weeks, exam weeks, and administrative weeks.

**The right way:**

```bash
# Layout-preserving text extraction. Grid rows stay as rows.
pdftotext -layout /Users/dumix/Documents/sustech-calendar/2026/academic-calendar-2026.pdf -

# Then read the row labels (第1周 / 第2周 / ... / 复习考试周 / 招生周) and
# count rows in each "phase" (春季学期 / 期中考试周 / 复习考试周 / 招生周).
# The row label is the source of truth, not the surrounding prose.
```

For a sanity check, count weeks of each phase and verify they sum to the
expected total. Spring 2026 grid: 7 + 2 (midterm, 不停课) + 6 + 2 (finals) + 1
(招生周, NOT a teaching week) = 18 calendar rows but **17 teaching weeks**
(because 招生周 is admin, not teaching).

---

## 1. Total week counts — Spring is 17 weeks (17 rows in PDF, 招生周 is admin), Fall is 17 weeks

| Item | PDF says | JSON field | Value |
|---|---|---|---|
| Spring total teaching weeks | "Spring Semester (17 weeks)" — weeks 1-17 are 春季学期/期中/复习考试周; 招生周 is a SEPARATE grid row, NOT 春季学期 | `spring_semester.total_teaching_weeks` | **15** (regular + midterms, excludes finals) |
| Spring finals weeks | 第16周 (Jun 8-14) + 第17周 (Jun 15-21) marked 复习考试周 in grid | `spring_semester.final.equivalent_weeks` | `[16, 17]` |
| Fall total weeks | "Fall Semester (17 Weeks)" — weeks 1-17 in 2026 calendar | `fall_semester.total_teaching_weeks` | **16** (regular + midterms, excludes finals) |
| Fall finals week | 第17周 (Dec 28 - Jan 3) marked 复习考试周 in grid; exam period "12月28日-1月8日" extends into 2027's first week, which is in next year's calendar | `fall_semester.final.equivalent_weeks` | `[17]` |

**Trap that bit me (2026-07-09):**
- The web-extracted PDF text sometimes summarizes Spring as "18 Weeks" by
  including the 招生周 (admissions week, Jun 22-28) as a teaching week.
  The actual grid has 招生周 as a SEPARATE row, NOT a 春季学期 week. So
  spring is 17 weeks (1-17), not 18.
- I "fixed" `[16, 17]` → `[16, 17, 18]` based on the wrong summary;
  user caught it. Reverted.
- **Rule: read the grid rows, not the linearized English summary.** The grid is the source of truth.

**Spring teaching-week breakdown (PDF grid):**
- Weeks 1-7: 春季学期
- Weeks 8-9: 期中考试周 (不停课 — classes continue)
- Weeks 10-15: 春季学期
- Weeks 16-17: 复习考试周 (finals)
- 招生周: separate row, 1 week, NOT a spring teaching week (admissions/admin)
- 暑假 starts Jun 29
- Total spring: 7+2+6+2 = **17 weeks** ✓

**Fall teaching-week breakdown (PDF grid):**
- Weeks 1-7: 秋季学期
- Weeks 8-9: 期中考试周 (不停课 — classes continue)
- Weeks 10-16: 秋季学期
- Week 17: 复习考试周 (finals — but the exam period "12月28日-1月8日" extends into 2027's first week, which is in next year's calendar)
- Total fall: 7+2+7+1 = **17 weeks in the 2026 calendar** ✓

---

## 2. Semesters and key dates (PDF "Spring/Fall Semester" sections)

| Item | PDF line | JSON field | Value |
|---|---|---|---|
| Spring sign-in | "Feb 24 New-term Registration" | `spring_semester.sign_in` | `2026-02-24` |
| Spring classes begin | "Feb 25 Classes Begin" | `spring_semester.teaching_start` | `2026-02-25` |
| Spring midterm start | "Apr 13-26 Mid-term Exams" | `spring_semester.midterm.start` | `2026-04-13` |
| Spring midterm end | (same) | `spring_semester.midterm.end` | `2026-04-26` |
| Spring final start | "Jun 8-18 Final Exams" | `spring_semester.final.start` | `2026-06-08` |
| Spring final end | (same) | `spring_semester.final.end` | `2026-06-18` |
| Fall freshman arrival UG | "Aug 17 Registration for 1st-Year UG Students" | `fall_semester.freshman_arrival` (undergrad only) | `2026-08-17` |
| Fall freshman arrival PG | "Aug 27 Registration for 1st-Year PG Students" | `fall_semester.freshman_arrival` (graduate only) | `2026-08-27` |
| Fall sign-in | "Sep 4 New-term Registration" | `fall_semester.sign_in` | `2026-09-04` |
| Fall classes begin | "Sep 7 Classes Begin" | `fall_semester.teaching_start` | `2026-09-07` |
| Fall midterm start | "Oct 26 - Nov 8 Mid-term Exams" | `fall_semester.midterm.start` | `2026-10-26` |
| Fall midterm end | (same) | `fall_semester.midterm.end` | `2026-11-08` |
| Fall final start | "Dec 28 - Jan 8 Final Exams" | `fall_semester.final.start` | `2026-12-28` |
| Fall final end | (same) | `fall_semester.final.end` | `2027-01-08` |
| Fall Sports Day no-class | "Nov 20-21 ... (**No classes Nov 20**)" | `fall_semester.extra_breaks` | `["2026-11-20"]` |

---

## 3. Compensatory workdays (PDF "Make-up" entries)

| PDF line | JSON entry |
|---|---|
| "Feb 28 Make-up: Odd-week Monday Classes" | `{"date": "2026-02-28", "week_type": "odd", "workday_type": "Monday"}` |
| "May 9 Make-up: Odd-week Tuesday Classes" | `{"date": "2026-05-09", "week_type": "odd", "workday_type": "Tuesday"}` |
| "Sep 20 Make-up: Odd-week Friday Classes" | `{"date": "2026-09-20", "week_type": "odd", "workday_type": "Friday"}` |
| "Oct 10 Make-up: Odd-week Wednesday Classes" | `{"date": "2026-10-10", "week_type": "odd", "workday_type": "Wednesday"}` |

All four are in BOTH `spring_semester.compensatories[]` / `fall_semester.compensatories[]`
(in `undergraduate.json` / `graduate.json`) AND `compensatory_workdays[]` in
`general.json`. The general.json version is just the date list (for "is this a workday?");
the semester-specific version carries the (week_type, workday_type) metadata needed for
the transfer algorithm.

---

## 4. National holidays (PDF mentions, JSON in `general.json`)

| Holiday | PDF date | `general.json` entry |
|---|---|---|
| 春节 | "Feb 17" (winter break) | `{"start": "2026-02-15", "end": "2026-02-23"}` |
| 清明节 | "Apr 5" | `{"start": "2026-04-04", "end": "2026-04-06"}` |
| 劳动节 | "May 1" | `{"start": "2026-05-01", "end": "2026-05-05"}` |
| 端午节 | "Jun 19" | `{"start": "2026-06-19", "end": "2026-06-21"}` |
| 中秋节 | "Sep 25" | `{"start": "2026-09-25", "end": "2026-09-25"}` |
| 国庆节 | "Oct 1" | `{"start": "2026-10-01", "end": "2026-10-07"}` |

Note: the JSON holiday dates are the official 3-day statutory ranges, not the
PDF's "highlighted" date. The PDF only mentions the first day of multi-day
holidays; the JSON has the full statutory range.

---

## 5. Information in PDF that is NOT in JSON (and why)

These appear in the PDF but are **not class-canceling** — they don't affect ICS:

- **退补选课暨导师指导周 (Advisory Week & Course Confirmation, weeks 1-3)**: informational,
  classes still meet normally. Skipped on purpose.
- **重大活动** (faculty/staff meetings, 开学典礼, 校园开放日, 毕业典礼, 评职称会议, etc.):
  none of these are marked "No classes" in the PDF, so they don't cancel student schedules.
  Skipped on purpose.
- **Course-selection windows** (Jan 12-Feb 23, Jul 6-Sep 3, Jun 22-Jul 3): admin schedule,
  not class schedule. Skipped.
- **Vacations** (winter break, summer break): covered by `winter_holiday` / `summer_holiday`
  blocks. ✓ captured.
- **Summer semester dates** (Jun 29-Aug 7): captured as `summer_semester`.

**If the user ever asks why a PDF event is missing from the JSON, check this section first.**

---

## 6. Known misleading field names (NOT renamed, just documented)

These names are bad. Do not copy them to new code. They are not renamed to preserve
the existing repo's data shape (would require migrating downstream consumers).

- `midterm.equivalent_weeks` — *sounds* like "no class these weeks". But SUSTech
  midterm is 不停课 (classes continue normally). This field is purely informational,
  no algorithmic effect on ICS.
- `final.equivalent_weeks` — *sounds* like "no class these weeks". This one is
  accidentally correct: finals DO cancel regular class meetings. The name is still
  wrong (should be `no_class_weeks` or `finals_weeks`) but the data is right.

**For ICS export, the correct usage is:**
```python
skip_weeks = set(sem["final"]["equivalent_weeks"])
# DO NOT add midterm.equivalent_weeks to skip_weeks — 不停课
```

---

## 7. Verification commands

```bash
# Verify the JSON against the PDF
cd /Users/dumix/Documents/sustech-calendar
python3 -c "
from datetime import date
import json
data = json.load(open('2026/undergraduate.json'))
# Spring: 7 + 2 (midterm) + 6 + 2 (final) = 17 weeks; 招生周 is NOT a teaching week
assert data['spring_semester']['total_teaching_weeks'] == 15  # excludes finals, midterms included
assert data['spring_semester']['final']['equivalent_weeks'] == [16, 17]  # 2 weeks, NOT 18
# Fall: 7 + 2 + 7 + 1 = 17 weeks (in 2026 calendar; 2nd exam wk spills into 2027)
assert data['fall_semester']['total_teaching_weeks'] == 16
assert data['fall_semester']['final']['equivalent_weeks'] == [17]
# Spring Sports Day Apr 4 is a Saturday — no longer in extra_breaks
assert 'extra_breaks' not in data['spring_semester']
# Fall Sports Day Nov 20 is still a no-class day
assert '2026-11-20' in data['fall_semester']['extra_breaks']
print('✓ all assertions pass')
"

# Re-fetch the PDF and diff (manual, eyeball — but read the GRID, not the linearized text)
curl -sL 'https://www.sustech.edu.cn/uploads/files/2025/11/25155108_33786.pdf' -o /tmp/cal-2026.pdf
pdftotext -layout /Users/dumix/Documents/sustech-calendar/2026/academic-calendar-2026.pdf - | head -100
```