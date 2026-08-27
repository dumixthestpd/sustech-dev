# Schedule Week Display — Format Rules

TIS stores weeks as a list of integers: `[1, 3, 5, 7]` for odd-only,
`[2, 4, 6]` for even-only, `[1,2,3,...,16]` for full semester, etc.

The web UI's `formatWeeks(weeks)` helper produces the display string.
Get these rules right or the display confuses students.

## Rules (all required)

1. **Format:** `1-16` — no `w` prefix. Comma-separated only when ≤6 weeks.
   - Right: `1-16`, `1,3,5,7`, `3,5`
   - Wrong: `w1-16`, `w1,3,5,7`

2. **Parity suffix (`单周` / `双周`) only when informative:**
   - **All weeks odd** → `单周` (e.g., `1,3,5单周`)
   - **All weeks even** → `双周` (e.g., `2,4,6双周`)
   - **Mixed or single week** → NO suffix

3. **Single-week entries** never get a suffix.
   `1单周` is redundant — week 1 is single by nature.

## Example outputs (canonical)

| Weeks data | Output | Why |
|---|---|---|
| `[1,2,...,16]` full semester | `1-16` | no parity to note |
| `[1,3,5,7,9,11,13,15]` odd only | `1,3,5,7,9,11,13,15单周` | parity informative |
| `[2,4,6,8,10,12,14,16]` even only | `2,4,6,8,10,12,14,16双周` | parity informative |
| `[1,3,5]` short odd | `1,3,5单周` | parity informative |
| `[1]` single week, odd | `1` | single, label redundant |
| `[3]` single week, odd | `3` | single, label redundant |
| `[1,2,3,4,5]` mixed short | `1,2,3,4,5` | mixed, no parity |

## Where it lives

`webui/templates/tis.html` — `formatWeeks()`, used by
`formatSchedule()` and `formatScheduleHTML()`.

## Implementation (don't lose the `>1` guard)

```js
function formatWeeks(weeks) {
  if (!weeks || !weeks.length) return '';
  var suffix = '';
  if (weeks.length > 1) {  // ← the guard that makes single weeks quiet
    if (weeks.every(function(w) { return w % 2 === 1; })) suffix = '单周';
    else if (weeks.every(function(w) { return w % 2 === 0; })) suffix = '双周';
  }
  var w;
  if (weeks.length <= 6) w = weeks.join(',');
  else w = weeks[0] + '-' + weeks[weeks.length - 1];
  return ' ' + w + suffix;
}
```

## Bug history

- Earlier versions appended `单周`/`双周` unconditionally. Summer
  BIOS201 class showed `Wed 1-4 慧园2栋503 1单周` — week 1 is single
  by definition, the label was noise. User flagged it 2026-07.
- Same formatter is also reused by the picked list and the solver
  output, so a fix in `formatWeeks()` fixes all three views.
