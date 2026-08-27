# TIS browser-side patterns — inline utilities, JSON load, IIFE testing

Date: 2026-08-06
Context: Restructured the TIS stepper from 4 steps to 5 (added a separate
Compare step); added per-candidate Export as JSON + Export all as .zip;
added multi-format JSON load. Patterns here are the reusable bits — the
design-level decisions live in `sustech-dev/SKILL.md` "Workflow
representation" and the iron laws in `sustech-architecture`.

## Inline ZIP writer (no external deps)

**When to use:** exporting multiple files as a single `.zip` from the
browser (TIS Compare step "Export all as .zip"). The whole project
avoids npm/build steps (per iron law #14's "Inline JS/CSS in
templates"), so dropping in JSZip just for this is overkill.

**Implementation (~80 lines):** STORE method (no compression), CRC-32
with precomputed 0xEDB88320 table, three sections per file (Local
File Header + data, Central Directory Header, End of Central Directory
record). Verify by extracting with Python's `zipfile` module — if
`zipfile.ZipFile(path).namelist()` returns the same file list the
writer claimed, the format is correct.

**Reference implementation:** `src/sustech_survival/webui/static/tis/tis.js`
function `buildZip(files)` + `exportAllCandidatesAsZip()`. Skeleton:

```js
// CRC-32 table (256-entry lookup)
var crcTable = (function() {
  var t = new Uint32Array(256);
  for (var n = 0; n < 256; n++) {
    var c = n;
    for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    t[n] = c >>> 0;
  }
  return t;
})();

function buildZip(files) {
  // For each file: write LFH + data → parts[], write CDH → central[]
  // Track byte offset of each LFH (for CDH's local-header-offset field)
  // After all files: write EOCD with central-dir size + offset + entry count
  // Return new Blob([parts, central, eocd], {type: 'application/zip'})
}
```

**Gotchas:**
- Set `dosTime = 0` and `dosDate = ((2020 - 1980) << 9) | (1 << 5) | 1`
  (Jan 1, 2020) — many ZIP readers reject `dosTime` with high bits set.
  The user doesn't need real per-file mtimes; a fixed recent timestamp
  is fine.
- Filenames need UTF-8 encoding (use `new TextEncoder().encode(name)`)
  AND sanitization (`/` `\` `:` `*` `?` `"` `<` `>` `|` all break
  some OS — replace with `_`).
- Always test with `python -m zipfile -l <downloaded.zip>` after
  writing — Python's reader is the strictest de-facto validator.

**Trigger download helper:** `URL.createObjectURL(blob)` + invisible
`<a download>` click + `URL.revokeObjectURL` after a 0ms timeout. Same
helper works for both `.zip` and `.json` exports.

## Multi-format JSON load pattern

**When to use:** any time users bring their own `.json` files into the
web UI, especially when the on-disk format has evolved over multiple
versions. TIS Compare step accepts four shapes:

| On-disk shape | Detection | Internal shape |
|---|---|---|
| `{type: "tis-candidate", schedule: {...}}` | envelope marker | `{label, sections, dropped, totalCredits, blocked, priority}` |
| `{version: 2, schedules: [{...}, {...}]}` | `Array.isArray(data.schedules)` | same, one entry per array item |
| `{sections: [...], dropped: [...]}` (legacy raw) | `Array.isArray(data.sections)` | same, single entry |
| `{picks: [...], version: 1}` (legacy picks-file) | `Array.isArray(data.picks)` | same, `picks` → `sections`, `dropped = []` |

**Pattern:** one `normalizeCandidateFile(data, fileName) -> entry[]`
function that throws on unrecognized shapes. Per-file errors collected
in a `failed[]` array and reported in one toast at the end:

```js
function loadCandidatesFromFiles(fileList) {
  var pending = fileList.length;
  var added = 0, failed = 0;
  fileList.forEach(function(file) {
    var reader = new FileReader();
    reader.onload = function() {
      try {
        var items = normalizeCandidateFile(JSON.parse(reader.result), file.name);
        items.forEach(function(it) { /* dedupe label, push */ added++; });
      } catch (e) {
        failed++;
        errs.push(file.name + ': ' + e.message);
      }
      if (--pending === 0) onAllDone();
    };
    reader.readAsText(file);
  });
}
```

**Why batch the errors:** reporting per-file failure separately (toast
per file) floods the UI. One summary toast + `console.warn(errs)`
gives the user a clean signal and the developer the detail.

**Why dedupe labels:** if the user loads `Z1.json` and `solution-1.json`
on different days, both produce a label `Z1` or `solution-1`. Append
`(2)`, `(3)` to the second onwards so `cmp-card[data-idx]` stays unique.

## IIFE-scope Playwright testing pattern

**The trap:** all module-level helpers in `tis.js` are inside an
IIFE for scope hygiene (per "JS scope rules" — they need to share
state with each other but stay out of the global namespace). This
means **`page.evaluate("someInternalFunction()")` fails with
`ReferenceError: someInternalFunction is not defined`** — the
function exists in JS but not in the page's global scope.

**Workarounds, in preference order:**

1. **Drive via the UI.** The cleanest test exercises real user
   flows — file input + button click + `expect_download`. This
   catches more bugs anyway (e.g. wiring bugs between the button
   and the function). For multi-file loads, use
   `page.set_input_files()` with a temp file path.

2. **Capture the download.** `async with page.expect_download():` +
   `download.path()` lets you inspect the resulting file with Python's
   `zipfile.ZipFile(...)` / `json.loads(...)`. Don't try to read the
   Blob from inside the page — Playwright's download API is the
   cross-process handoff.

3. **Seed localStorage + reload.** For tests that need a populated
   state, write to `localStorage` via `page.evaluate(...)` then
   `page.reload()`. The IIFE re-runs and reads the seeded state on
   init. Works for `SAVED_SCHEDULES`, `BLOCKED`, `PICKED`, etc.

4. **Expose for testing only.** Last resort — add a debug hook like
   `window.__test_loadCandidates = loadCandidatesFromFiles;` behind
   a flag. Don't ship the exposure to production — the IIFE
   encapsulation is the point.

**Real session example:** the multi-JSON load test initially called
`page.evaluate("loadCandidatesFromFiles([file])")` and failed with
`ReferenceError`. The fix was switching to `set_input_files` on the
hidden `<input type="file">` element (`#candidates-file-input`) +
listening for the resulting UI change (new `.cmp-card` elements).

**The lesson:** when testing IIFE-wrapped code, treat the page like
a real user. Don't try to call internal functions; click buttons,
fill inputs, capture downloads. You get a more honest test AND
avoid scope-debugging time.

## Stepper split workflow (the recipe)

**When to use:** the user says "step X is doing two things, split it"
or "add a step between X and Y." This pattern is exactly the
2026-08-06 split of "Step 3 (Schedule)" into "Step 3 (Schedule)" +
"Step 4 (Compare)".

**Recipe (in order):**

1. **Read the existing step's code thoroughly first.** Don't trust
   memory — open the file, search for every `switchStep(N)`,
   `data-step-pane="N"`, `data-step="N"`, every JS call that
   references the old number. The cascade contract (iron law #14)
   applies here too: missing one reference → silent staleness.

2. **Decide where the split point lands.** TIS pattern: anything that
   "picks promising schedules" stays in the source step; anything
   that "compares / loads from disk / exports" moves to the new step.
   The split is usually along the "in-memory workflow" vs. "file /
   external workflow" line.

3. **Add the new chip + pane to the HTML.** New `<button
   class="step-chip" data-step="N+1">` + new `<div class="step-pane"
   data-step-pane="N+1">`. Renumber all chips/panes after the new
   one. The existing `<input type="file">` for the new pane lives
   inside its pane body, hidden (`display:none`).

4. **Move the in-flow element into a static div in the new pane.**
   Don't keep the auto-create pattern (`pane =
   document.createElement('div')` appended to SOLVE_OUT) — move the
   element to a static position in the new step-pane so the layout
   is predictable. The static div needs an empty-state fallback
   (icon + help message) when the data is empty.

5. **Update `switchStep(n)`:**
   - Bump the bounds check `n > 4` → `n > 5`
   - Move the per-step render call (e.g. `renderComparePane()` was
     called on step 3 → now on step 4)
   - Update the grid-visibility default if the new step is also
     grid-hidden by default

6. **Renumber everywhere.** `switchTab('bids')` → `switchStep(5)`.
   `onclick="switchStep(4)"` on the right-panel "go to bids"
   trigger → `switchStep(5)`. Bid-panel binding comment → "step 5
   terminal action wiring." Easy to miss one — `grep -rn
   'switchStep([45])'` before committing.

7. **Update keyboard handlers.** The `keydown` handler had a guard
   `if (CURRENT_STEP !== 3) return` — change to also allow the new
   step. Each step gets its own key behavior (step 3 ←/→ cycles
   solver results; step 4 ←/→ focuses/cycles candidate cards).

8. **Wire the new step's toolbar.** Load JSONs → `set_input_files` on
   the hidden `<input>`. Clear all → `confirm()` modal. Export all
   as .zip → trigger download (see ZIP section above).

9. **Re-render on entry.** `if (n === NEW_STEP) { renderXxx(); }` in
   `switchStep`. The user revisits the step after editing elsewhere —
   the pane must reflect current state, not the stale snapshot from
   when they last visited.

10. **Test the full flow with Playwright.** Don't just verify the
    new step renders. Click the new step chip from every other step
    (does `switchStep(N+1)` correctly hide N's pane?), trigger
    every toolbar button (does the file input open? does the zip
    download?), apply a candidate (does it jump to the renumbered
    bid step?).

**Renumbering audit pattern:** before committing a stepper change,
`grep -n 'step' static/tis/tis.js | grep -v '^.*://.*'` + manual
review of every match. The cascade contract says missing one
reference is a bug — the audit is the explicit pre-commit check.

## `sectionsToBlocks` dual-format acceptance

**The rule (be liberal in what you accept):** when a function takes a
section-shaped object that has been serialized in multiple ways over
the project's history, **support all of them** rather than enforcing
one shape via migration or rejection.

**TIS specifics:** `sectionsToBlocks(sections)` in `tis.js` was
originally written for the **solver-result format**
(`{slots: [{day, period_start, period_end, weeks}]}`). After the
stepper split, candidate cards also need to render from the **flat
picks-file format**
(`{day, period_start, period_end, weeks_odd, weeks_even, weeks_all}`).
The fix was to accept both shapes in `sectionsToBlocks` — synthesize
a single slot from the top-level fields if `slots` is empty.

```js
var slots = c.slots;
if (!slots || !slots.length) {
  if (c.day && c.period_start && c.period_end) {
    var wArr = [];
    if (c.weeks_all) wArr.push(0, 1);
    else {
      if (c.weeks_odd)  wArr.push(0);
      if (c.weeks_even) wArr.push(1);
    }
    slots = [{day: c.day, period_start: c.period_start,
              period_end: c.period_end, weeks: wArr.length ? wArr : [0, 1]}];
  }
}
```

**The lesson:** functions that take "the shape of a thing" should be
documented as accepting all known shapes, with comments explaining
where each shape comes from. Don't add a `version` field check that
rejects older shapes — the user's data lives on disk, possibly across
years. A silent normalization is better than a hard error.

## Don't make your user babysit your tests (live-device safety)

**Triggered 2026-08-06:** user said "just don't disconnect yourself
to test it. i am currently away and will see if this works out for
a device." They were testing the new Wi-Fi auth flow on a real
device and didn't want me making changes that disrupt their live
session.

**Rule:** if the user is currently using a device / session / browser
tab to test something they're working on, **do not make changes
that affect that surface until they're back and have confirmed
the test is done.** The "test" can be a Playwright test, a CLI
command, a manual browser session — anything that holds live state
that the user is observing.

**Specifically:**
- Don't run a Playwright test against a browser instance the user
  has open. Don't reload their tab. Don't run destructive actions
  via the same auth session.
- Don't make a code change to a file the user is editing live
  (their editor may have unsaved buffers; the change won't be
  picked up until they reload, and the reload might clobber their
  test state).
- Don't push to a remote device / server that the user is
  observing (the change may go live before they finish their
  observation).

**When in doubt, ask.** "Are you currently testing X? Want me to
defer this change until you're done?" is cheap and avoids the
heartburn of "you broke my test session."