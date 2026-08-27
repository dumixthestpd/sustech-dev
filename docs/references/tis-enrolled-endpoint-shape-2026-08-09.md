# TIS enrolled-endpoint quirk — raw schedule-block rows vs per-course rows (2026-08-09)

## The trap

`SelectCourseClient.my_courses(semester)` calls TIS's
`/xszykb/queryxszykbzong` (the **personal-schedule grid endpoint**).
It returns one row per `(rwh × schedule-block × week-parity × 校区)`,
NOT one row per enrolled course. For a student with N enrolled
courses, this returns M > N rows — typically 2-13x more.

A student enrolled in 7 courses observed 13 rows: `MSE307-002`
showed up 4× (4 schedule blocks for the same rwh — different
period-ranges within the [1-8节] lab block), `MSE332-001` and
`MSE345-002` each appeared twice (different ZC week-parity patterns),
etc.

If the blueprint pipes those raw rows straight to the frontend, the
user sees N mostly-empty cards with `MSE307` listed 4 times — and
the frontend's `ENROLLED_RWH` Set becomes a set of duplicates of the
same rwh.

## Fix at the API boundary (where the UI contract lives)

Do NOT change `my_courses()` — CLI usage and `enrolled_rwhs()` still
want the raw blocks. Shape them at the blueprint boundary:

```python
by_rwh: dict[str, dict] = {}
for row in raw:
    rwh = row.get("RWH") or row.get("rwh") or ""
    if not rwh or rwh in by_rwh:
        continue
    sksj = row.get("SKSJ") or ""
    lines = [ln.strip() for ln in sksj.splitlines() if ln.strip()]
    name = lines[0] if lines else ""
    section = lines[2] if len(lines) >= 3 else ""
    if section.startswith("[") and section.endswith("]"):
        section = section[1:-1]
    # Walk all blocks for this rwh to build slots[]
    slots = []
    for sb in raw:
        if (sb.get("RWH") or "") != rwh:
            continue
        slot = _raw_schedule_slot(sb)
        if slot is not None:
            slots.append(slot)
    by_rwh[rwh] = {
        "rwh": rwh, "name": name, "section": section,
        "code": rwh_to_code(rwh),
        "slots": slots, "has_schedule": bool(slots),
        "enrolled": True,
    }
return {"semester": sem, "enrolled": list(by_rwh.values())}
```

## Extracting slots out of the raw row fields — verified 2026-08-09

**This section was wrong when first written.** The original interpretation
of `KEY`'s `jc<M>` tail as the period number, `JSJC` as a period count,
and `ZC` as a 0-indexed week bitmap was untested against real SKSJ text
and produced schedule grids where enrolled blocks stretched across
many rows + false conflicts in the solver. Verified against the raw
rows for `[1-16周]`, `[1-15单周]`, `[2-16双周]` on 2026-08-09:

| Field    | Shape                                | Use (verified)                          |
|----------|--------------------------------------|----------------------------------------|
| `KEY`    | `"xq<N>_jc<M>"`                      | `N` = weekday (1-7). **`jc<M>` is the class-block index on that day** (1st, 2nd, 3rd, 4th meeting) — NOT the period number. Don't extract `period_start` from here. |
| `KSJC`   | int (e.g. 1, 3, 5, 7)                | **period start** (the source of truth — matches the first number in `SKSJ`'s `[X-Y节]`). |
| `JSJC`   | int (e.g. 8, 4, 6)                   | **END period (inclusive)**, NOT a count. `JSJC=8` with `KSJC=7` means periods 7-8 (2 periods), NOT "8 periods of duration". `period_end = JSJC`. |
| `ZC`     | 32-char binary string                 | Week parity pattern. **Skip `ZC[0]`** (1-char header / pre-semester buffer, always `'0'` regardless of pattern). For `i >= 1`: `ZC[i] == '1'` means week `i` is active. |
| `JASMC`  | str                                  | classroom name (optional)              |
| `SKSJ`   | multi-line str (newline-joined)      | kcmc / teachers / section / weeks / room — for display only |

### Verified example rows

| `SKSJ` week pattern | `KSJC` | `JSJC` | `KEY`           | `ZC` (active positions)        | Expected `weeks`            |
|---------------------|--------|--------|------------------|--------------------------------|-----------------------------|
| `[1-16周]`          | 1      | 8      | `xq3_jc1..4`     | 1,2,...,16 (positions 1-16)    | 1, 2, ..., 16               |
| `[1-15单周]` (odd)  | 3      | 4      | `xq2_jc2`        | 1,3,5,7,9,11,13,15            | 1, 3, 5, 7, 9, 11, 13, 15   |
| `[2-16双周]` (even) | 7      | 8      | `xq1_jc4`        | 2,4,6,8,10,12,14,16            | 2, 4, 6, 8, 10, 12, 14, 16  |
| `[5-8节]`           | 5      | 8      | `xq2_jc3`        | (depends)                      | (depends) — 4 periods P5-8   |

All confirmed via raw TIS data 2026-08-09. MSE416 (`[2-16双周]` P7-8
Monday) was the smoking gun: previous code rendered it as P4-P11
(8 rows!) and the solver flagged false conflicts with MSE307 etc.
After fix: P7-P8 (2 rows), zero false conflicts among TIS-enrolled
data (verified by pairwise overlap test — they never conflict with
each other, as expected).

### The correct slot builder

```python
def _raw_schedule_slot(row: dict) -> dict | None:
    key = row.get("KEY") or ""
    ksjc = row.get("KSJC"); jsjc = row.get("JSJC"); zc = row.get("ZC") or ""
    m = key.split("_") if key else []
    if not m or len(m) < 2:
        return None
    try:
        weekday = int(m[0].lstrip("xq")) if m[0].startswith("xq") else None
    except (TypeError, ValueError):
        return None
    if weekday is None or weekday < 1 or weekday > 7:
        return None
    # JSJC is the END period (inclusive), NOT a count.
    if ksjc is None or jsjc is None:
        return None
    period_start = int(ksjc)
    period_end = int(jsjc)
    # ZC[0] is a 1-char buffer (always '0'); skip it. ZC[i] for i>=1
    # is "is week i active?". Skip position 0 explicitly.
    weeks = [i for i, ch in enumerate(zc) if i > 0 and ch == "1"]
    if not weeks:
        return None
    return {
        "day": weekday,
        "period_start": period_start,
        "period_end": period_end,
        "weeks": weeks,
        "room": row.get("JASMC") or "",
    }
```

`weeks` uses actual week numbers (1-16), matching `Course.slots_raw`
shape consumed by the frontend `sectionsToBlocks()`.

### Why this trap was easy to write wrong

The original interpretation read like a sensible encoding:
- `KEY`'s `jc<N>` → "period N" (looked like a sequential index)
- `JSJC` → "period count" (matches the name "JieShuCount"-ish)
- `ZC` → "zero-indexed weeks" (standard 0-indexed intuition)

Each guess was plausible in isolation, but ALL THREE were wrong. The
only way to verify is to read the raw `SKSJ` text from `my_courses()`
and cross-check `KSJC`/`JSJC`/`ZC`/`KEY` against it. Always do this
when adding a new parser for a TIS field.

## Frontend counterpart — TIS-enrolled in the weekly grid

The blueprint's `slots` field enables the frontend to render enrolled
courses in the step-3 weekly grid alongside picked sections. Match
by `rwh` (not `code` — same course can have multiple picked rwhs,
only the enrolled one should get the lock badge). Enrolled blocks
get `.blk-enrolled` class + a 🔒 lock badge.

Two-grid architecture (added 2026-08-09):
- **Step 1 (Pick)** — `.grid-weeks-stacked` — odd/even full-width
  stacked vertically. Reason: mass selection (4-5 candidates of the
  same code ticked at once) needs wide cells for block-packing.
- **Step 3 (Schedule)** — `.grid-weeks-side-by-side` — odd/even
  side-by-side horizontally. Reason: shows the final picked +
  enrolled view, no mass selection, narrow cells are fine.

## Why a separate grid, not a re-use of step 1's

- Different DOM IDs (`grid-body-odd-3` / `grid-body-even-3` /
  `grid-legend-3` vs step 1's `grid-body-odd` / `grid-body-even` /
  `grid-legend`) so `renderGrid()` and `renderGrid3()` don't trample
  each other when the user toggles steps.
- Different `sectionsToBlocks` input — `renderGrid3` combines picked
  + enrolled, dedupes by rwh (PICKED wins over ENROLLED for shared
  rwhs, since user-owned state overrides TIS view).

## Cascade addition

`renderGrid3()` is now part of the picked-state cascade. All three
mutators (`addPicked` / `removePicked` / `applyPicksFromData`) call
it after `renderGrid()`. `loadEnrolled()` calls it after populating
`ENROLLED_RWH` + `ENROLLED_DATA`.

## Diagnosing "the enrolled list is weird"

1. `curl http://localhost:61019/api/tis/enrolled?xn=...&xq=... | jq '.enrolled | length'`
   — should be 1× the number of enrolled courses, NOT 2-13×.
2. If the count is too high: blueprint is piping raw rows. Apply the
   dedupe-by-rwh fix above.
3. If the count is right but rows are empty: `SKSJ` parsing failed.
   The multi-line string is newline-joined; line 0 = kcmc, line 2 =
   section (with `[brackets]`), line 1 = teachers list.
4. If the count is right but blocks stretch across too many grid rows
   OR the solver flags false conflicts between enrolled courses that
   "shouldn't" overlap: this is the period-parsing trap above. Verify
   `period_start` / `period_end` from `KSJC` / `JSJC` directly against
   `SKSJ`'s `[X-Y节]` text. Verify `weeks` by counting active `ZC`
   positions and matching to the `[weeks pattern]` in `SKSJ`.