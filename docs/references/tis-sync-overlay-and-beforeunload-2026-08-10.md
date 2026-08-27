# TIS sync overlay + beforeunload guard

Date: 2026-08-10.
Trigger: user request *"any time a new change is applied to the tis page
e.g. sync bid to tis i need a loading bar that shows if the sync is
complete. e.g. what would happen if you close the web ui halfway?"*

## The two-tier feedback distinction

There are TWO feedback channels for in-flight operations:

| Channel | Element | For |
|---------|---------|-----|
| **Shimmer bar** (2px top edge) | `#loading-bar` + `.lb-fill` (shimmer animation 20%→85%) | Every fetch — initial load, search, refresh, sync. Fires automatically from `getJSON`/`postJSON`. |
| **Sync overlay** (top-center panel) | `#sync-progress` (spinner + text + detail line) | TIS-**mutating** operations ONLY: Sync to TIS, Drop all enrolled. Whatever actually writes to TIS. |

The shimmer bar alone is insufficient for mutating ops because:
- It fires for every fetch — visually identical for a 200ms catalog refresh and a 30s TIS write.
- It gives the user no indication that "this is a real action that will modify TIS state".
- It does nothing for the "what if I close the tab" question.

The overlay is the "this changes your data, don't close the tab" signal.

## The overlay element + states

```html
<div id="sync-progress" role="status" aria-live="polite">
  <span class="sp-icon spin">⟳</span>
  <span class="sp-label">
    <span class="sp-text"></span>
    <span class="sp-detail"></span>
  </span>
</div>
```

`role="status"` + `aria-live="polite"` so screen readers announce the
state transitions without interrupting the user.

Four states (matched by class):

| State | Classes | Icon | Border | Auto-hide | When |
|-------|---------|------|--------|-----------|------|
| **loading** | `.active` | `⟳` (with `.spin` class for rotation animation) | default panel border | no | fetch in flight |
| **success** | `.active.success` | `✓` | green (`#3a8a4a`) | 3 s | all batches committed |
| **error** (partial) | `.active.error` | `⚠` | red (`#8a3a3a`) | **sticky** — stays until user dismisses | some bids succeeded, some failed |
| **error** (over-budget / network) | `.active.error` | `⚠` | red | **sticky** | zero bids committed, but TIS state may be unknown |

The success auto-hides at 3 s because the green border + the existing
flash message (`flash('Synced: 5/5 bid(s) ...', 'ok')`) already give
two confirmations. Errors stay sticky because the user needs to read
what went wrong before doing anything else.

## The helpers

```js
var SP = document.getElementById('sync-progress');
var SP_ICON = SP && SP.querySelector('.sp-icon');
var SP_TEXT = SP && SP.querySelector('.sp-text');
var SP_DETAIL = SP && SP.querySelector('.sp-detail');
var SP_TIMER = null;
var SYNC_IN_FLIGHT = 0;     // nested counter — supports concurrent mutating ops

function syncStart(msg, detail) {
  var lbId = loadingStart();     // also drive the shimmer bar
  SYNC_IN_FLIGHT++;
  if (SP_TIMER) { clearTimeout(SP_TIMER); SP_TIMER = null; }
  SP.classList.remove('success', 'error');
  SP_ICON.textContent = '⟳';
  SP_ICON.classList.add('spin');
  SP_TEXT.textContent = msg;
  SP_DETAIL.textContent = detail || "Don't close this tab until complete.";
  SP.classList.add('active');
  return lbId;
}

function syncEnd(lbId, opts) {
  opts = opts || {};
  loadingEnd(lbId);
  if (SYNC_IN_FLIGHT > 0) SYNC_IN_FLIGHT--;
  if (SYNC_IN_FLIGHT < 0) SYNC_IN_FLIGHT = 0;  // safety
  var kind = opts.kind || 'info';
  SP.classList.remove('success', 'error');
  SP_ICON.classList.remove('spin');
  SP_ICON.textContent = kind === 'success' ? '✓' : kind === 'error' ? '⚠' : 'ℹ';
  if (kind === 'success') SP.classList.add('success');
  else if (kind === 'error') SP.classList.add('error');
  SP_TEXT.textContent = opts.text || '';
  SP_DETAIL.textContent = opts.detail || '';
  if (SP_TIMER) { clearTimeout(SP_TIMER); SP_TIMER = null; }
  if (!opts.sticky) {
    SP_TIMER = setTimeout(function() {
      SP.classList.remove('active', 'success', 'error');
      SP_TIMER = null;
    }, 3000);
  }
}
```

The `lbId` round-trip is so `syncStart` drives the shimmer bar (which
fades on its own via `loadingEnd`) AND the overlay together. The
overlay handles its own auto-hide timer independently.

## The beforeunload guard

```js
window.addEventListener('beforeunload', function(e) {
  if (SYNC_IN_FLIGHT > 0) {
    e.preventDefault();
    e.returnValue = 'A sync to TIS is in progress. Leaving now may leave partial changes.';
    return e.returnValue;
  }
});
```

The `SYNC_IN_FLIGHT > 0` guard is critical: plain browsing (tab close
during no-op) does NOT trigger the dialog, only actual in-flight writes.
Modern browsers ignore `returnValue` content but still show the
"Leaving site?" dialog when `preventDefault()` is called.

Nested counter pattern: `syncStart` increments, `syncEnd` decrements.
If multiple mutating ops overlap (unlikely but possible — e.g. user
clicks Sync while Drop is still iterating), the guard stays engaged
until all finish. Prevents under-counting (early release of the guard)
and over-counting (permanent block after a normal request).

## Wiring it into the actions

Two existing actions, both call `syncStart` on entry and `syncEnd` on
exit:

### `syncToTIS` (button: `📤 Sync to TIS`)

```js
// AFTER confirm() returns true, BEFORE the first batch fetch:
var btn = document.getElementById('btn-sync-tis');
var prevLabel = btn ? btn.textContent : '';
if (btn) { btn.disabled = true; btn.textContent = '⟳ Syncing…'; }
var lbId = syncStart('Syncing ' + totalPicks + ' bid(s) to TIS…',
                      'This writes to TIS — keep this tab open until done.');

// AFTER Promise.all(batches):
if (btn) { btn.disabled = false; btn.textContent = prevLabel || '📤 Sync to TIS'; }
// ... merge results, decide success / partial / over-budget / network ...
syncEnd(lbId, {
  kind: allOk ? 'success' : 'error',
  text: flashMsg,
  detail: allOk ? 'TIS now has your bids.' : 'Some bids did not commit — see flash for details.',
  sticky: !allOk,
});
```

The button is disabled + relabeled during the call so a double-click
can't fire a second sync while one's running.

### `dropAllEnrolled` (sequential loop — update overlay per step)

```js
var lbId = syncStart('Dropping ' + rwhs.length + ' enrolled section(s)…',
                     'This writes to TIS — keep this tab open until done.');
function _refreshDetail(done) {
  SP_TEXT.textContent = 'Dropping ' + rwhs.length + ' section(s) · ' + done + '/' + rwhs.length + ' done';
}
_refreshDetail(0);
function _next(i) {
  if (i >= rwhs.length) {
    var allOk = okCount === rwhs.length;
    syncEnd(lbId, { kind: allOk ? 'success' : 'error', text: flashMsg, ..., sticky: !allOk });
    return;
  }
  _refreshDetail(i);
  postJSON(...).then(function(r) {
    if (r && r.ok) okCount++;
    else failed.push(...);
    _next(i + 1);
  });
}
_next(0);
```

Sequential POSTs (TIS rate-limits) → per-step overlay text update is
the only way the user sees progress on a 7-enrolled-section drop.
Skipping this and the overlay just shows "Dropping 7…" for 30 s with
no feedback until the final result.

## "What happens if I close the UI mid-sync?" — the honest answer

Three cases. Document these in the user-visible detail line so the
user understands the failure mode:

1. **Network request aborted (browser closes connection):** server-side
   the in-flight POST may complete or be dropped, depending on how far
   TIS got before the socket closed. Any batches the server had
   already finished processing **are committed on TIS** — there's no
   transactional rollback. The client never sees the response so it
   can't tell the user which commits landed.

2. **`fetch` promise rejected with `AbortError`:** the client-side
   `.catch` fires, the overlay transitions to the error state with
   "Network error during sync · TIS state is unknown — refresh the
   page to check." This is the helpful message — refresh reloads the
   page and `loadEnrolled()` + `loadRound()` pull the current TIS
   state, so the user can see what actually committed.

3. **Page fully closes before the fetch resolves:** same as case 1
   from the client's perspective, plus the overlay never had a chance
   to update. The beforeunload dialog is the only signal that
   something is mid-flight.

The honest answer is: "TIS has whatever it received before the abort,
and you need to refresh the page to find out." Don't oversell the
overlay's certainty — the spinner + the detail line set the right
expectation.

## CSS

```css
#sync-progress {
  position: fixed; top: 0; left: 50%; transform: translateX(-50%);
  z-index: 10001;
  padding: .55rem 1.2rem;
  border-radius: 0 0 10px 10px;
  background: var(--panel);
  border: 1px solid #2a3340; border-top: 0;
  color: var(--fg);
  font-size: .85rem;
  box-shadow: 0 6px 22px rgba(0,0,0,.45);
  display: flex; align-items: center; gap: .6rem;
  pointer-events: none;
  opacity: 0;
  transition: opacity .2s, transform .2s;
  min-width: 280px; max-width: 520px;
}
#sync-progress.active { opacity: 1; transform: translateX(-50%) translateY(0); }
#sync-progress.success {
  border-color: #3a8a4a;
  background: linear-gradient(180deg,#1a3a22 0%,var(--panel) 70%);
}
#sync-progress.error {
  border-color: #8a3a3a;
  background: linear-gradient(180deg,#3a1a1a 0%,var(--panel) 70%);
}
#sync-progress .sp-icon { font-size: 1.1rem; line-height: 1; }
#sync-progress .sp-icon.spin { animation: sp-spin 1s linear infinite; }
#sync-progress .sp-label { flex: 1; line-height: 1.3; }
#sync-progress .sp-label .sp-detail {
  display: block; font-size: .72rem; color: var(--mut); margin-top: .15rem;
}
@keyframes sp-spin { 0% { transform: rotate(0); } 100% { transform: rotate(360deg); } }
```

`pointer-events: none` so the overlay never blocks clicks on
elements behind it (top of the page, header buttons).

## Verification

After wiring a new mutating action:

1. **Happy path:** click Sync → button disabled + overlay shows
   "Syncing N bid(s)…" → response → overlay flips to green ✓ with
   summary → button re-enabled + flash message.
2. **Force a 500 (or unplug network mid-fetch):** overlay flips to
   red ⚠ sticky → flash shows error → beforeunload dialog was active
   during the fetch (you can't see it but the listener fired).
3. **Click sync twice quickly:** first click disables the button so
   the second click is a no-op. No race.
4. **Toggling locked mode mid-sync:** doesn't break — the SYNC_IN_FLIGHT
   counter doesn't touch locked mode, and `syncEnd` reads whatever
   the result holds.

## Server-side template caching pitfall

**Flask Jinja does not auto-reload templates in production mode.** After
editing `tis.html`, the served HTML may still be the pre-edit version
until the server is restarted. Symptom: `curl -s ... | grep
'<your-new-element>'` returns 0 hits even though the file on disk
contains the element. Fix: restart the webui server process (not just
the browser tab).

This is the server-side cousin of the browser-cache pitfall in SKILL.md
(after editing `tis.js`, browser may show old code → hard-refresh).
Same diagnostic recipe — verify what's actually served before assuming
the fix is loaded.

## Related

- The simpler inline status line pattern (e.g. for the Ignore-TIS-enrolled
  toggle) is in `async-actions-visible-feedback-2026-08-09.md`. Use that
  for non-mutating toggles / single fetch with a clear source-of-truth
  element. Use the sync overlay when the action:
    - actually mutates server state (writes to TIS)
    - runs longer than ~2 s (network round-trip + TIS work)
    - would leave the user confused if they closed the tab mid-flight
- The "Web UI fix isn't visible — check stale browser cache first" section
  in SKILL.md covers client-side caching. Server-side caching (Flask
  Jinja not auto-reloading templates) is a separate failure mode — same
  diagnostic recipe, different fix.