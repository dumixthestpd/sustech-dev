# TIS bid panel — locked-enrolled architecture

Date: 2026-08-09 (extended across two conversation rounds).
Trigger: user pushed back twice with *"the bid panel don't show my courses"* and *"when i click on the card of enrolled course i cannot change its bid wtf"*. Both came from the same root cause: the bid panel was built for picks-only, then locked-enrolled was bolted on as a read-only display. The semantics were wrong.

#### "Locked" means the COURSE is locked — not the bid

The "Ignore TIS enrolled" toggle (when off / "locked mode") promises the
user: enrolled rwhs cannot be dropped, cannot be replaced by the solver,
win every conflict. It does NOT promise the bid is read-only.

TIS's `updXkxsByyx` endpoint (the "enrolled" side of `submit_bids`) accepts
bid updates on already-enrolled sections — the bid is a separate field from
the enrollment state. `submitBids()` in the JS already routes bids to
`where: 'enrolled'` when `ENROLLED_RWH.has(k)`. The infrastructure is there.
The UI was just refusing to use it.

**User pushback (verbatim):** *"when i click on the card of enrolled course
i cannot change its bid wtf"* — first read-only attempt dropped the
`.bb-edit` input entirely.

**The fix:** the locked-enrolled box renders the SAME `.bb-edit` input as
a regular pick. Keeps the 🔒 badge + "Already enrolled" note so the
enrollment state stays visible, but the bid is editable.

#### Two bid stores — the source of most bugs

The bid panel has TWO independent bid stores:

| Store | Holds | Used for |
|-------|-------|----------|
| `PICKED_BIDS[rwh]` | Bids the user is actively setting on PICKED rwhs | Picks, both cart-state and enrolled-state picks |
| `EXISTING_BIDS[rwh]` | Bids TIS already has on enrolled / cart rwhs (populated from `search_personal` response's `xkxs` field) | Locked-enrolled rwhs the user hasn't picked here |

`bidTotal()` originally only summed `PICKED_BIDS`. For locked-enrolled to
show up in the budget, it had to also sum `EXISTING_BIDS[ENROLLED_RWH - PICKED]`.
`submitBids()` originally only iterated `PICKED_BIDS` (and even then guarded
on `PICKED[k]` — so locked-enrolled bids were silently dropped). All four
edit handlers (`startBidEdit` / `onBidEditInput` / `onBidEditKey`
Enter/Escape / `onBidEditBlur`) originally wrote to `PICKED_BIDS` only.

**Three small helpers route reads/writes to the right store based on
whether the rwh is a pick or a locked-enrolled:**

```js
function _bidIsLockedEnrolled(rwh) {
  return !IGNORE_TIS_ENROLLED && ENROLLED_RWH.has(rwh) && !PICKED[rwh];
}
function _bidRead(rwh) {
  return _bidIsLockedEnrolled(rwh)
    ? (Number(EXISTING_BIDS[rwh]) || 0)
    : (Number(PICKED_BIDS[rwh]) || 0);
}
function _bidWrite(rwh, v) {
  if (_bidIsLockedEnrolled(rwh)) EXISTING_BIDS[rwh] = v;
  else PICKED_BIDS[rwh] = v;
}
```

Every edit handler uses `_bidRead` / `_bidWrite`. The `BID_EDIT` state
captures `isLockedEnrolled` at edit start so subsequent handlers don't
re-evaluate (and aren't tripped by toggle flips mid-edit).

#### The full cascade — five functions need updating

Adding locked-enrolled support to the bid panel is not a one-line change.
Five renderers / controllers all reference `PICKED_BIDS` and need a
locked-enrolled branch (or to call the helpers above):

| Function | What needs to know about locked-enrolled |
|----------|---------------------------------------------|
| `bidShouldShow()` | | Must show ` even with zero picks, if locked-enrolled exist in locked mode. Otherwise flipping the toggle off with no picks leaves the entire bid step blank — looks like the fix didn't work. |
| `renderBidPanel()` | | Iterate PICKED keys + (locked mode ? locked-enrolled - PICKED : []) for both the bar and the boxes. Locked boxes render the same `.bb-edit` input + 🔒 + "Already enrolled" note. |
| `updateBidTotals()` | | Bar segments include locked-enrolled (`bid-seg-locked` class for the striped-blue pattern). |
| `bidTotal()` | | Sum PICKED_BIDS + EXISTING_BIDS for locked-enrolled. |
| `submitBids()` | | Explicitly add locked-enrolled rwhs from EXISTING_BIDS (the `PICKED_BIDS` iteration's `PICKED[k]` guard excludes them). |
| `loadEnrolled()` `.then` | | Must call `renderBidPanel()` so step 5 updates when the toggle loads enrolled data. |

If you miss one, the symptom is silent: bids don't appear, total is wrong,
edits don't commit, submit doesn't send — but no error is thrown. Test all
five after any bid-panel change.

#### Why `bidShouldShow()` was wrong

Original:
```js
function bidShouldShow() {
  if (MODE !== 'personal') return false;
  if (!Object.keys(PICKED).length) return false;
  return true;
}
```

User feedback: *"i don't see the fix. the bid panel don't show my courses"*
— they had zero picks and only locked-enrolled. The function returned
`false`, `renderBidPanel()` short-circuited on the empty branch, and the
panel never rendered. The locked-enrolled boxes I added existed nowhere
to live.

Fix:
```js
function bidShouldShow() {
  if (MODE !== 'personal') return false;
  if (Object.keys(PICKED).length) return true;
  if (!IGNORE_TIS_ENROLLED && ENROLLED_RWH.size) return true;
  return false;
}
```

#### `submitBids` — the silent bid-drop trap

Original:
```js
for (var k in PICKED_BIDS) {
  if (PICKED_BIDS.hasOwnProperty(k) && PICKED[k]) {  // ← PICKED[k] excludes locked-enrolled
    var w = ENROLLED_RWH.has(k) ? 'enrolled' : 'cart';
    picksByWhere[w][k] = PICKED_BIDS[k];
  }
}
```

The `PICKED[k]` guard was there to ensure the submit only included
actively-picked courses. But it also excluded locked-enrolled edits, so
any bid change the user made on a locked-enrolled box was silently
dropped. TIS rejected nothing — the request simply never contained the
rwh.

Fix: explicit locked-enrolled branch reading from `EXISTING_BIDS`:
```js
if (!IGNORE_TIS_ENROLLED) {
  ENROLLED_RWH.forEach(function(rwh) {
    if (PICKED[rwh]) return;                    // already handled above
    if (EXISTING_BIDS[rwh] == null) return;      // no bid known — skip
    picksByWhere.enrolled[rwh] = EXISTING_BIDS[rwh];
  });
}
```

#### Verification recipe

After any bid-panel locked-enrolled change, verify all five paths:

1. **Zero picks + locked-enrolled exist + locked mode on** → bid panel
   shows with N read-only-looking (but editable!) locked boxes. Total
   includes locked-enrolled EXISTING_BIDS.
2. **Edit a locked-enrolled bid (click → type → Enter)** → box re-renders
   with new value, bar segment grows, total updates.
3. **Toggling locked mode off mid-session** → locked boxes disappear from
   panel, total drops back to PICKED_BIDS only.
4. **Locked-enrolled also in PICKED** (user picked an enrolled rwh) →
   renders as a regular pick (the `if (PICKED[rwh]) return;` guard skips
   it in the locked-enrolled loop).
5. **Submit picks-only in locked mode** → request contains both PICKED
   bids AND EXISTING_BIDS (possibly edited) for locked-enrolled. Inspect
   network panel: `picks` body should include the locked-enrolled rwhs.

#### `showTransferOverlay` — the missed call site

The multi-store helper pattern above fixes the four edit handlers
(`startBidEdit`, `onBidEditInput`, `onBidEditKey` Enter/Escape,
`onBidEditBlur`). But the bid panel has a FIFTH operation that the
user can perform on a bid box: **drag-to-transfer** (mousedown on one
box → mousemove → mouseup on another → modal asks "how many points
to move?"). This used to only handle pick→pick:

```js
function showTransferOverlay(srcRwh, dstRwh) {
  var src = PICKED[srcRwh];              // undefined for locked-enrolled
  var dst = PICKED[dstRwh];              // undefined for locked-enrolled
  var srcBid = Number(PICKED_BIDS[srcRwh]) || 0;   // wrong store
  var dstBid = Number(PICKED_BIDS[dstRwh]) || 0;
  ...
  PICKED_BIDS[srcRwh] = srcBid - amt;    // wrong store on write
  PICKED_BIDS[dstRwh] = dstBid + amt;
}
```

Result: dragging from any locked-enrolled box (or to one) silently
no-op'd. `src.name` threw `Cannot read properties of undefined`, and
even if it didn't, the destination write went to `PICKED_BIDS` instead
of `EXISTING_BIDS`, so the bid edit never persisted on TIS.

**User pushback (verbatim, 2026-08-10):** *"i cannot apply
re-assigning bid from one course to another if the course is enrolled
in tis. why do they have to behave differently?? you are obviously
not reasonably reusing and count how many wheels you rebuild"*.

The fix is the same pattern — one more helper, one more call site
updated:

```js
// Course objects (picks + locked-enrolled have the same shape:
// name/code/slots/class_group) — single lookup so callers don't
// branch on which store the rwh lives in.
function getCourseByRwh(rwh) {
  return PICKED[rwh] || ENROLLED_DATA[rwh] || null;
}
```

`showTransferOverlay` then uses `getCourseByRwh` for the course
objects and `_bidRead` / `_bidWrite` for the bid values. Now all four
combinations work: pick→pick, pick→locked, locked→pick, locked→locked.

#### The "wheel rebuilding" anti-pattern — the real lesson

This session shipped SIX commits across two conversation rounds to
build out the locked-enrolled bid panel:

1. Period/week parser fixes (unrelated, but in the same area)
2. Status line for silent failures
3. Slot dedup for the weekly grid
4. `bidShouldShow()` so the panel renders with zero picks
5. Locked-enrolled boxes + `submitBids` routing
6. (THEN) drag-to-transfer unification

Five commits set up the helpers and partially applied them. The SIXTH
caught the remaining hole and was the one that triggered the user's
frustration: *"count how many wheels you rebuild"*.

The lesson: when a feature has parallel stores with a UI overlay
(picks ∪ locked-enrolled, both renderable as bid boxes), the moment
you add the first locked-enrolled branch, factor the difference into
helpers AND audit every other call site in the same file. If you
build the helpers but only update the call sites you remember, you
ship a working-looking feature with silent holes.

**Audit recipe after multi-commit locked-enrolled work:**

```bash
# Find every raw access to the parallel stores in the file
grep -n 'PICKED\[' src/.../tis.js     # raw course lookup — should be getCourseByRwh
grep -n 'PICKED_BIDS\[' src/.../tis.js  # raw bid read/write — should be _bidRead/_bidWrite
grep -n 'EXISTING_BIDS\[' src/.../tis.js # same — only bidTotal() and submitBids() legitimately iterate this directly
```

For each remaining raw access, ask: does this code path ever run on a
locked-enrolled rwh? If yes, route through the helper. If no (e.g.
`renderBidPanel` iterates `Object.keys(PICKED)` which by definition
excludes locked-enrolled), leave it.

**Verified clean state** as of 2026-08-10, commit `893348b`: every
bid-related read/write in `tis.js` routes through `_bidRead` /
`_bidWrite`, every course lookup routes through `getCourseByRwh`. If
a future change adds a SIXTH operation (e.g. right-click "set to 10"
quick action), it MUST route through the same helpers.

#### Related

- Slot-dedup + field-semantics lessons (JSJC=end period, jc=class-block
  index, ZC off-by-one) are in `tis-enrolled-slot-dedup-and-field-semantics-2026-08-09.md`.
- The "loadEnrolled → visible status line" pattern (so silent failures
  don't masquerade as "won't refresh") is in
  `async-actions-visible-feedback-2026-08-09.md`.