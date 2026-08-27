# TIS enrolled endpoint — field semantics + slot-dedup rule

Session: 2026-08-09. Triggered by enrolled courses rendering as thin column
slices instead of full-width blocks in the step-3 weekly grid. Three bugs
were entangled; all fixed in commit `eca7a7d`.

## Field semantics (these were the root cause of "periods extend to row 11")

`my_courses()` returns raw rows. Each row has these fields that the parser
gets wrong if it treats them as "what the name suggests":

| Field | What it actually means | Wrong reading that breaks everything |
|--------|------------------------|---------------------------------------|
| `KSJC` | Start period (1-12). | — (correct in the code already) |
| `JSJC` | **END period (inclusive).** With `KSJC=7, JSJC=8` the slot is periods 7-8. | Treating as a count → `period_end = KSJC + JSJC - 1 = 14`. MSE416 lecture turned into a 7-row monster spanning to period 14. |
| `KEY` (`"xq<N>_jc<M>"`) | `<N>` is weekday (1-7). `<M>` is the **class-block index on that day** (1st, 2nd, 3rd, 4th meeting) — NOT the period number. | Reading `jc<N>` as the period. |
| `ZC` (32-char binary string) | `ZC[i]=1` means **week `i+1` is active**. Position 0 is week 1, not a pre-semester buffer. | `weeks.append(i + 1)` (off-by-one) or skipping position 0. |

**Verification recipe:** pick one course with `[1-16周]` (all weeks),
`[1-15单周]` (odd only), `[2-16双周]` (even only). Compute `weeks`
yourself from the ZC and confirm the three patterns all decode correctly.
Don't trust the field names — verify against the raw rows.

The previous commits (`771a1fd`, `8bc9f79`) had the JSJC and KEY bugs.
This session fixed them. The ZC off-by-one was the third one — verified
2026-08-09.

## Slot-dedup rule (universal — applies to any data source feeding the grid)

`my_courses()` returns **multiple raw rows per rwh** — one per (lecture / lab
/ tutorial / 校区 / parity combo). Many of those rows describe the **same
time slot**. If you don't dedupe, the shared grid pipeline sees:

```
MSE307-002: 4 slots, all (day=3, period=1-8)   ← 4 dupes of one slot
MSE345-002: 2 slots, both (day=2, period=5-8)  ← 2 dupes of one slot
```

`buildPackedItems` then assigns each duplicate its own column. The
course renders as 4 thin slices instead of 1 full-width block.

**Fix lives in the shared `sectionsToBlocks`, not in the enrolled
endpoint.** The user explicitly asked (verbatim): *"shouldn't course grid
display be uniformly coded and reused to avoid logic concerns?"* — they
don't want a per-source branch in the renderer.

```javascript
function sectionsToBlocks(sections) {
  var seenKeys = {};
  for (...) {
    for (var si = 0; si < slots.length; si++) {
      var s = slots[si];
      var weeks = s.weeks || [];
      // Canonical key — sort weeks so [0,1] and [1,0] collide.
      var key = s.day + ':' + s.period_start + ':' + s.period_end + ':' +
                weeks.slice().sort((a,b)=>a-b).join(',');
      if (seenKeys[key]) continue;
      seenKeys[key] = true;
      allBlocks.push({ day: s.day, periodStart: s.period_start,
                       periodEnd: s.period_end, weeks: weeks, ... });
    }
  }
}
```

**Why the shared path is the right home:**
- Picked sections (catalog format) are already deduped upstream, but the
  dedup still applies cleanly — no per-source branching.
- Solver format and flat-file format (the two shapes `sectionsToBlocks`
  accepts) both go through it.
- Removing the dedup would mean every caller (picked, enrolled, solver
  results, ICS export) would have to remember to dedupe independently.

## Bug verification (the diff that caught it)

```
$ curl -s 'http://127.0.0.1:61019/api/tis/enrolled?xn=...&xq=1' | \
  python3 -c "import json,sys; d=json.load(sys.stdin); \
  [print(c['rwh'], 'slots=', len(c.get('slots',[])), 'unique=', \
         len({(s['day'],s['period_start'],s['period_end']) for s in c.get('slots',[])})) \
   for c in d['enrolled']]"

2026-2027-1-MSE307-002 slots= 4 unique= 1
2026-2027-1-MSE345-002 slots= 2 unique= 1
2026-2027-1-MSE416-001 slots= 1 unique= 1   ← no dupes, single slot
```

Then after the fix:

```javascript
// All enrolled blocks in the DOM:
allWidthsDistinct: ["100%"]
heights: 304px (8 periods), 152px (4), 76px (2)
```

## Related (this same session)

The enrolled endpoint's `slots` field also broke the period math — JSJC
off-by-N made the solver flag **false conflicts** between TIS-enrolled
courses that never conflict. Fix in the same commit (`eca7a7d`).

The visible-feedback lesson (loading → success/error status line under
the "Ignore TIS enrolled" toggle, so silent failures stop masquerading
as "won't refresh") is in `webui-architecture-2026-07-06.md` §
**"Async actions need visible feedback"**.