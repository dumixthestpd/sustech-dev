---
name: calendar-architecture-2026-07-11
description: Calendar module, ICS export, Authorizer API state, and CLI mounting pattern as of 2026-07-11. Companion to the main sustech-dev SKILL.md.
type: reference
---

# Calendar, ICS, Auth, CLI — current state (2026-07-11)

This file captures the four pieces that changed in the 2026-07-11
build session. Cross-reference with the main SKILL.md for endpoint
catalog and discovery methodology.

## 1. Calendar module — `sustech_survival.calendar`

The canonical answer to "what date does this (week, weekday) fall on?"
and "when do classes run during a comp day?". Module path is
`sustech_survival.calendar` (NOT `sustech_survival.cal`, NOT
`sustech_survival.semester` — that's the legacy TIS-code translator).

### Public types

```python
Weekday = Literal['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                  'Friday', 'Saturday', 'Sunday']
Parity  = Literal['odd', 'even']

@dataclass(frozen=True)
class Compensatory:
    date: date
    week_type: Parity      # "odd" or "even"
    workday: Weekday       # Literal['Monday'..'Sunday']

@dataclass(frozen=True)
class Holiday:
    name: str; start: date; end: date

@dataclass(frozen=True)
class ClassTime:
    weeks: tuple[int, ...]      # which weeks of the semester
    weekday: int                # 0=Mon..6=Sun
    periods: tuple[int, ...]    # 1..12
    title: str = ""             # enrolled class metadata
    teacher: str = ""
    room: str = ""
    # matches_date(date, semester) -> bool helper attached
```

`Day` — **no `DayKind` enum**. Bool methods only:

```python
class Day:
    date, week, weekday, semester, holiday, comp
    in_final_week, in_midterm_week
    def is_holiday(self) -> bool
    def is_compensatory(self) -> bool
    def is_extra_break(self) -> bool
    def is_final(self) -> bool
    def is_midterm(self) -> bool
    def is_weekend(self) -> bool
    def is_teaching_day(self) -> bool    # not holiday/final/break/weekend
    def has_class(self) -> bool          # teaching OR compensatory
    @property
    def schedule(self) -> list[ClassTime]  # classes meeting on this day
    def __str__(self) -> str              # human-readable one-liner
```

`Semester` — date intelligence + enrolled class list:

```python
class Semester:
    # identity (delegated to legacy TIS Semester)
    season, level, xn, xq, tis, human

    # dates (Monday-anchored — week 1 starts on the Monday on/before
    # teaching_start, even if teaching actually begins mid-week)
    sign_in, teaching_start, teaching_end
    total_teaching_weeks, midterm_weeks (set[int]), final_weeks (set[int])
    compensatories: list[Compensatory]
    extra_breaks: set[date]
    classes: list[ClassTime]            # enrolled (TIS or self-defined)

    # day lookup
    def day(self, date=None) -> Day      # None defaults to today
    def __contains__(self, date) -> bool  # date in semester

    # enrolled class management
    def fill(self, class_time: ClassTime) -> bool   # True/False
    def dates(self, class_time: ClassTime) -> list[date]  # actual meeting dates

    # identity: spring=2026 Spring (cohort), tis=2026-20262
```

`AcademicCalendar`:

```python
class AcademicCalendar:
    year, level                                  # "undergraduate"|"graduate"
    spring: Semester
    fall: Semester
    summer: Optional[Semester]                   # None when JSON has only start/end
    holidays: list[Holiday]
    @classmethod
    def load(cls, year, level="undergraduate", *, online=True, base_url=DEFAULT_REPO)
    def day(self, date=None) -> Day
```

### API style rules (user-enforced)

- No Chinese in code, comments, docstrings, or variable names. English only.
- If a Chinese term is the correct domain name (e.g. 补课 for makeup-class day),
  put it in a docstring comment the first time and never mention the wrong
  name (补班) again. No parenthetical "(NOT 补班)" reminders.
- Short names, no underscores for user-facing methods:
  - `holiday_for(comp)` not `find_nearest_holiday_for(comp)`
  - `fill(time)` not `class_meetings(weeks, weekday)`
  - `dates(class_time)` not `meetings(time)`
- TIS always uppercase.
- `date_of(week, weekday)` and `week_of(date)` are both Monday-anchored
  (week 1 = Monday on or before `teaching_start`).
- `AcademicCalendar.load()` default is `online=True` (GitHub raw).
- `Summer` semester is `None` unless the JSON has `teaching_start`.

## 2. Compensatory transfer algorithm

**Per-comp lookup, NOT per-flushed-date.** For each compensatory day, find
the nearest holiday whose same-workday occurrence would have flushed
classes of the comp's (week_type, workday), transfer that schedule to
the comp date, then drop the holiday schedules. Not every holiday has
a comp — don't iterate all holidays.

```python
# In Semester._holiday_for:
def _holiday_for(self, comp: Compensatory) -> Optional[date]:
    """For a compensatory day, find the holiday date whose same-workday
    occurrence would have flushed classes matching (week_type, workday).
    Returns the flushed date (not the holiday range), or None."""
    workday_idx = WEEKDAY_INDEX[comp.workday]
    candidates = []
    for h in self.calendar.holidays:
        for off in range((h.end - h.start).days + 1):
            d = h.start + timedelta(days=off)
            if d.weekday() != workday_idx: continue
            w = self.week_of(d)
            if w == 0: continue
            if ("odd" if w % 2 else "even") != comp.week_type: continue
            candidates.append(d)
    if not candidates: return None
    forward = sorted(d for d in candidates if d <= comp.date)
    backward = sorted(d for d in candidates if d > comp.date)
    return forward[-1] if forward else (backward[0] if backward else None)
```

`fill(time)` uses `_holiday_for` (via `_comp_for_flushed`) to know which
holiday a class is being transferred from. Only the comp days trigger
a lookup; the regular teaching days are included as-is.

## 3. iCal export — `/api/tis/ical`

Web UI route for downloading the picked schedule as an .ics file.

**Endpoint:** `GET /api/tis/ical?xn=<xn>&xq=<xq>&picks=<json>`

- `xn` = TIS academic year string, e.g. `"2025-2026"`
- `xq` = term, `"1"` (fall) or `"2"` (spring)
- `picks` = URL-encoded JSON list of `{weeks, weekday, periods, title, teacher, room}`
  objects (one per slot of a picked course)
- Response: `text/calendar` (RFC 5545) with one `VEVENT` per (date, period)
- 50-min periods, China TZ → UTC. Standard SUSTech break pattern:
  - 1: 08:00, 2: 09:00, 3: 10:20, 4: 11:20, 5: 13:30, 6: 14:30,
  - 7: 15:30, 8: 16:30, 9: 18:00, 10: 19:00, 11: 20:00, 12: 21:00

**Module:** `sustech_survival.selectcourse.ical.courses_to_ical(semester)`
returns a string. Pure transform — no Flask, no fetch. The webui
blueprint loads the calendar online, registers each pick as a
`ClassTime` via `semester.fill()`, and hands off.

**JS:** `webui/static/tis/tis.js` has `exportICal()` that builds the
picks JSON from the picked list and navigates to the endpoint. The
button is mounted in `renderPicked()`.

## 4. Authorizer API (current state, 2026-07-11)

Public surface — stable as of this date:

```python
class Authorizer:
    def ensure() -> tuple[bool, str]    # (ok, reason) — check + auto-refresh
    def check() -> tuple[bool, str]     # verify in-memory session
    def _refresh() -> bool              # private; force a fresh CAS login
    def login(*, headless=False)       # Playwright headful fallback
    @property
    def session() -> requests.Session   # pre-configured (cookies + UA)
```

**REMOVED — do not reintroduce:**

- `auth.refresh()` — no public method. Use `_refresh()` (private) or `ensure()`.
- `auth.load()` — no disk cache. Sessions are in-memory only.
- `auth.requests_session` — use `auth.session` (the property).
- `register_auth(name, instance)` — replaced by `@require_auth(AuthorizerClass)`.

**CAS authorizer inheritors:** `TISAuth`, `BBAuth`, `LibAuth`,
`PMSAuth`, `WSAuth`. All registered as singletons per-class.

**Decorator pattern:**

```python
from sustech_survival.sso import require_auth, TISAuth

@require_auth(TISAuth)
def my_endpoint(auth=None):                # auth kwarg auto-injected
    r = auth.session.get("/xszykb/...")
```

**`python -m sustech_survival.lib.login` flow (fixed 2026-07-11):**
1. `auth_singleton.ensure()` — checks + auto-refreshes
2. If still not OK, `auth_singleton.login()` (Playwright headful)
3. Verifies with `ensure()` again

Previously the script called `auth_singleton.refresh()` (a method that
no longer exists), which crashed with `AttributeError`.

**Outstanding sweep:** `bb/`, `tis/`, `context/`, `tis/eval/`, and
`webui/blueprints/tis.py` still call `auth.refresh()` and will crash
on first use. Fix: `auth._refresh()` or `auth.ensure()`. Mechanical.

## 5. CLI mounting pattern

Every submodule's `__main__.py` (argparse) gets a thin Click wrapper
at `<module>/cli.py`. The unified `sustech` dispatcher mounts them all.

### Wrapper template

```python
# <module>/cli.py
import click

@click.group(name="<module>", help="...")   # same name as the namespace
def cli() -> None:
    pass

@cli.command(
    name="run",
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
        "help_option_names": ["-h", "--help"],
    },
)
@click.pass_context
def run_cmd(ctx: click.Context) -> None:
    """Pass-through to the argparse CLI."""
    import sys
    from .__main__ import main as _argparse_main
    rc = _argparse_main(ctx.args)
    sys.exit(rc or 0)

# Plus a typed subcommand for each argparse command, e.g.:
@cli.command(name="depts", help="List 50+ known department names.")
def depts_cmd() -> None:
    import sys
    from .__main__ import main as _argparse_main
    sys.exit(_argparse_main(["depts"]) or 0)
```

### argparse `main()` signature

Argparse `main()` must accept optional `argv: list[str] | None`:

```python
# <module>/__main__.py
def main(argv: list[str] | None = None) -> int:   # ← optional argv
    parser = argparse.ArgumentParser(...)
    ...
    args = parser.parse_args(argv)
    args.func(args)
    return 0
```

`faculty/__main__.py` was the outlier (had no `argv` param) and was
patched to match. Future `__main__.py` files should follow this
signature so wrappers can pass args.

### Top-level mounting in `sustech_survival/cli.py`

```python
@mount  # noqa
def _mount(module: str, target: click.Group) -> None:
    """Import ``<module>.cli:cli`` and copy its commands onto ``target``."""
    try:
        mod = __import__(f"sustech_survival.{module}.cli", fromlist=["cli"])
        sub_cli = getattr(mod, "cli", None)
    except Exception as e:
        target.help = f"(unavailable: {e})"
        target.short_help = f"{module} (unavailable)"
        return
    if isinstance(sub_cli, click.Group):
        for name, cmd in sub_cli.commands.items():
            target.add_command(cmd, name=name)
    else:
        target.add_command(sub_cli, name="run")

# In the top-level cli.py:
_mount("faculty", faculty_cmd)
cli.add_command(faculty_cmd)
```

### Currently mounted (13 subcommands)

`bb`, `booking`, `context`, `faculty`, `lib-booking`, `nces`,
`papers`, `pms`, `selectcourse`, `tis`, `transit`, `webui`, `ws`.

### Don't migrate argparse → Click wholesale

The wrapper is a one-line shim. Migrating the argparse CLI to Click
is more work and changes the per-submodule CLI surface (which has
its own users). Keep argparse in `__main__.py`, write a thin Click
adapter in `cli.py`.

## 6. Cross-references

- `references/sustech-calendar-pdf-mapping-2026-07-09.md` — every
  PDF grid-row → JSON field mapping. Read this when working with the
  calendar (especially before adding new fields to the JSON).
- `references/tis-cold-start-rate-limit-2026-07-06.md` — what blows
  up on cold TIS loads and how to avoid it.
- `references/architecture-module-vs-ui.md` — module/UI split rules
  for the webui blueprints.
