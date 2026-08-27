# TIS course selector solver — subset backtracking with priority dropping

**Date: 2026-07-05**  
**Based on:** c.x-d.fun (by @xCipHanD) scheduler algorithm  
**Code:** `sustech_survival.webui.blueprints.tis:api_solve()`

---

## Algorithm overview

Given N course codes, the solver finds all non-conflicting section
combinations by trying subsets from largest to smallest, using
priority to decide which courses to keep when conflicts force dropping.

```
for size from N down to 1:
    generate ALL subsets of this size from the course codes
    sort subsets by priority sum (lower = higher priority kept)
    for each subset:
        run backtracking to find non-conflicting combos
        add solutions, capped at max_res total
```

## Data structures

### Input

```json
{
  "codes": ["ACC201", "BIO102B", "BIO203", "BIO103", "BIO104"],
  "priority": ["ACC201", "BIO102B", "BIO203", "BIO103", "BIO104"],
  "rwhs": ["2026-2027-1-ACC201-001", "2026-2027-1-BIO102B-001", ...],
  "blocked": [[6, [1,2,3,4,5]]],
  "max": 30
}
```

- `codes` — all picked course codes (deduplicated on frontend).
- `priority` — same codes in priority order (most important first).
- **`rwhs` — list of specific RWH strings the user actually picked (CRITICAL).**
  Without this, the (v1) solver loaded ALL catalog sections for each
  course code including ones the user never selected, producing solutions
  that used unknown sections or dropped courses because extra catalog
  sections caused conflicts.
- `blocked` — time slots to exclude, `[day, [periods]]`.
- `max` — max total solutions across all coverage levels.

### Lookup (v2 — now uses picked RWHs only)

```python
# Build a lookup from rwh → course, then group by code
by_rwh = {x.rwh: x for x in all_courses}
by_code: Dict[str, list] = {}
for rwh in rwhs:
    course = by_rwh.get(rwh)
    if course:
        by_code.setdefault(course.code, []).append(course)
```

Groups ONLY the user's selected sections (by RWH) by course code.
Multiple sections of the same code = different class groups the user
explicitly chose. **DO NOT load all catalog sections** — that was the
v1 bug that caused "solve drops everything" behavior.

### Per-subset backtracking

```python
def _solve_subset(subset_codes, limit):
    result = []
    
    def backtrack(i, current):
        if len(result) >= limit:
            return
        if i == len(subset_codes):
            result.append([serialize(section) for section in current])
            return
        for section in by_code[subset_codes[i]]:
            if not section.has_schedule:
                continue
            if conflicts_with_blocked(section.slots_raw, blocked_slots):
                continue
            if any(conflicts(section.slots_raw, other.slots_raw) 
                   for other in current):
                continue
            current.append(section)
            backtrack(i + 1, current)
            current.pop()
    
    backtrack(0, [])
    return result
```

### Conflict check

```python
def slots_overlap(a, b):
    if a["day"] != b["day"]:
        return False
    a_periods = set(range(a["period_start"], a["period_end"] + 1))
    b_periods = set(range(b["period_start"], b["period_end"] + 1))
    if not (a_periods & b_periods):
        return False
    a_weeks = set(a.get("weeks") or [])
    b_weeks = set(b.get("weeks") or [])
    if a_weeks and b_weeks and not (a_weeks & b_weeks):
        return False
    return True
```

**Key detail:** If EITHER slot has empty weeks `[]`, weeks are ignored
— the slots only need day+period overlap to conflict. This matches
the fact that empty weeks = placeholder (no schedule data).

### Priority-based subset generation

```python
import itertools

n = len(codes)
for size in range(n, 0, -1):
    subsets = list(itertools.combinations(codes, size))
    # Sort by priority: lower sum = higher-priority courses kept
    subsets.sort(key=lambda s: sum(priority_index[c] for c in s))
    for subset in subsets:
        solutions = solve_subset(list(subset), remaining_budget)
        ...
```

`priority_index[code] = i` where `i` is the index in the priority list.
Lower indices = higher priority. The sum of indices for a subset
represents how "important" the kept courses are — smaller sum = better.

### Response shape

```json
{
  "solutions": [
    {
      "sections": [{...course_dict...}, ...],
      "covered": 4,
      "total": 5,
      "dropped": ["BIO203"],
      "size": 4
    }
  ],
  "codes": ["ACC201", "BIO102B", ...],
  "priority": ["ACC201", "BIO102B", ...]
}
```

## Frontend rendering pattern

The frontend in `tis.html`:

1. **Groups solutions by coverage** (`byCoverage[covered]`) — shows the
   best results first.
2. **Displays coverage header**: "✅ 4/5 courses kept (3 solutions)".
3. **Each solution card** shows:
   - Coverage status: "Kept 4/5 · Dropped: **BIO203**" or
     "All 5 courses kept — no conflicts".
   - Each section: code, class group, name, schedule.
   - "Apply" button.
4. **Apply button** replaces `PICKED` with the solution's sections,
   re-renders cards, picked list, and grid.
5. Shows max 5 solutions per coverage level, with "… and N more" if
   there are more.

### Performance considerations

- For N courses, `C(N, N-1) + C(N, N-2) + ... + C(N, 1) = 2^N - 1`
  subsets total. For N=8: 255 subsets. For N=10: 1023.
- Each subset runs backtracking. If `max_res=30`, the solver stops
  early once enough solutions are found at a given coverage level.
- Subsets at size N-1 are typically few: for N=8, only 8 subsets.
- **Practical limit:** N=10 max. Beyond that, `itertools.combinations`
  generates 1023 subsets and the backtracking may timeout (Flask's
  default 30s). If the user picks more than 10 courses, suggest
  culling first.

## Comparison with c.x-d.fun's algorithm

| Feature | c.x-d.fun (SUSTech_AutoScheduler) | Our solver |
|---|---|---|
| Grouping | By course name (kcmc), experiment bundles | By course code (codes) — simpler, no experiment logic |
| Within-group sorting | By time-slot count (fewer first) | N/A — sections in API order |
| Full-set first | Yes — max 100 solutions | Yes — max 30 (configurable) |
| Subset fallback | Yes — skip 1, then 2, etc. | Yes — try ALL subsets at each size |
| Priority | Implicit (by list order) | Explicit `priority` field |
| Scoring | Capacity score (enrolled/capacity) | Priority sum only |
| Exports | PNG, CSV, ICS | Not yet |
