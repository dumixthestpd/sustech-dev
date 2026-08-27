# Async actions need visible feedback (status line pattern)

Date: 2026-08-09.
Trigger: user reported "when I untick ignore, my enrolled won't refresh".
Root cause was a dead TIS session returning `{"error": ...}` — the
original `loadEnrolled()` `.catch` only logged to console, so the user
saw zero feedback and concluded the toggle was broken.

## The rule

Any async action the user explicitly triggers (toggle, button, form
submit) MUST surface its progress and outcome in the UI — not just
the console. Silent failures look to the user like "the button does
nothing" or "it won't refresh", which is impossible to debug from
their end.

## The pattern

Used by `Ignore TIS enrolled` toggle → `loadEnrolled()`. Add a status
line DOM element next to the trigger:

```html
<label>...<input type="checkbox" id="ignore-tis-enrolled">...</label>
<div id="enrolled-status" class="enrolled-status"></div>
```

```js
var statusEl = document.getElementById('enrolled-status');
function setStatus(html, cls) {
  if (!statusEl) return;
  statusEl.className = 'enrolled-status' + (cls ? ' ' + cls : '');
  statusEl.innerHTML = html;
}
setStatus('⏳ Loading TIS enrolled…', 'loading');
getJSON('/api/tis/enrolled' + sem()).then(function(d) {
  // ... success: populate state, re-render surfaces ...
  setStatus(IGNORE_TIS_ENROLLED
    ? ENROLLED_RWH.size + ' TIS-enrolled (ignored)'
    : '🔒 ' + ENROLLED_RWH.size + ' TIS-enrolled (locked)', 'ok');
})['catch'](function(e) {
  setStatus('⚠️ Enrolled load error: ' + escapeHtml(e.message), 'err');
});
```

## Three terminal states

| State | Class | Visual | When |
|-------|-------|--------|------|
| `loading` | `.enrolled-status.loading` | accent color + ⏳ | fetch in flight |
| `ok` | `.enrolled-status.ok` | success color + count | success |
| `err` | `.enrolled-status.err` | bad color + ⚠️ + escaped error message | failure |

## Three rules for the status element

1. **Set "loading" BEFORE the fetch starts**, not in `.then()`. Otherwise
   the user sees nothing during the slow VPN round-trip and assumes
   the click was lost.
2. **Both success AND failure paths must update the status.** A `.catch`
   that only does `console.warn(...)` is the silent failure mode. Mirror
   the success message in the failure message — escape the error
   string with `escapeHtml()` to avoid HTML injection from a TIS
   message.
3. **The error message goes in the UI, not just the console.** The user
   is the one who needs to see "session expired" / "rate limited" /
   "network down" — they can't read your logs.

## Failure-path rendering also re-renders dependents

Silent failure that leaves stale UI is worse than honest "load failed"
status. In `loadEnrolled`, the `.catch` block calls
`renderPicked(); renderGrid3(); renderBidPanel();` even on error so
🔒 badges and locked-enrolled bid boxes clear when the source data
disappears.

This is a special case of the general rule: **every dependent view
needs to be cleared when its source data goes away**. If you add a
new view that consumes `ENROLLED_DATA` (bid panel, schedule grid,
whatever), add it to BOTH the success AND failure paths of the
fetch.

## CSS

```css
.enrolled-status{display:block;font-size:.68rem;color:var(--mut);padding:0 0 .3rem;line-height:1.4}
.enrolled-status.ok{color:var(--ok,#4caf50)}
.enrolled-status.err{color:var(--bad)}
.enrolled-status.loading{color:var(--accent)}
```

Color tokens `--ok` and `--bad` should match the project's existing
theme variables. If they don't exist, fall back to the hex codes shown.

## When NOT to use this pattern

If the action is sub-second and synchronous (e.g. clicking a tab
toggle, opening a modal), the UI state change is the feedback. No
status line needed.

If the action is "fire-and-forget" (analytics, telemetry), no status
line — failures aren't user-actionable.

If the project already has a global toast/flash system, use that
instead — don't add a per-element status line when a unified
notification system exists.