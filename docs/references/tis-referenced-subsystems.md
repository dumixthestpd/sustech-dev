# TIS — referenced subsystems (duplicate content removed)


## Web UI

The webui module registers itself as a Flask blueprint. The blueprint owns HTTP + render; the module owns domain logic.

### Source of truth for skin work (added 2026-08-24)

Three locations exist for webui content. **Edit only (1).**

1. **`~/.openclaw/code/sustech_survival/src/sustech_survival/webui/skins/`** — workspace repo, canonical source. Edit here, commit, push.
2. **`dumixthestpd/sustech_survival` on GitHub** — read-only mirror after `git push`. Don't edit here; nothing flows back.
3. **`~/.sustech_survival/skins/`** — user-installed skin cache. Independent copies. May be **ahead** of the workspace from hand-edits done for fast iteration.

When the user says "the default skin" or "look at what we previously did", they mean (1). Audit recipe when unsure where to look:

```bash
git -C ~/.openclaw/code/sustech_survival log --oneline -5 -- src/sustech_survival/webui/skins/<name>
git -C ~/.openclaw/code/sustech_survival status --short
```

If the workspace has uncommitted changes for the skin, that's where to look first. If clean, "previously did" is at HEAD or older commits. **If you find content in (3) that's not in (1), that's local-only work — ask the user whether to bring it back into the repo before redoing it.**

### Skins are strictly monolingual — one folder per (skin × language) pair (added 2026-08-24)

After the 2026-08-24 split, the convention is firm:

- **One skin folder per (skin-name × language).** No `?lang=zh` query params, no inline `<script>` i18n blocks, no `<base>.zh.html` suffixed files alongside `<base>.html`.
- **Each skin's HTML is hardcoded in its target language.** The loader picks the active skin; the skin itself does not switch.

**Wrong (mixed-language, was the old pattern):**
```
default/
  index.html          # English
  index.zh.html       # Chinese (same skin, language switch)
  tis.html            # bilingual with inline i18n script
```

**Right (split):**
```
default/
  index.html          # English only
  tis.html            # English only
default_zh/
  index.html          # Chinese only, baked translations
  tis.html            # Chinese only, baked translations
```

**Why the i18n approach was retired** (real bugs found in `default/tis.html` before the split):

- `:nth-of-type(N)` selectors in the i18n JS counted `<div>` siblings of the same type, not `.row` siblings — labels shifted off-by-one because the `.row` parent had non-`.row` `<div>` siblings before them (stat div, mode-btn container).
- Translation tools / humans occasionally translated CSS class names (`.save-file-btn` → `.save-文件-btn`) while the JS still queried English names — silent styling and JS breakage.
- Half-translated strings (placeholders, `title=` attributes, comments) were easy to miss.
- The whole machinery was redundant: the only thing it enabled was a header `<a href="?lang=zh">` link, and the complexity wasn't worth it.

**Translation rule when baking a CN skin:** change ONLY text content of elements, `placeholder="..."` attributes, `title="..."` attributes, and `<option>...</option>` text. **Never** change `class="..."`, `id="..."`, JS file references, comment text, or attribute names. Tell translators / tools this explicitly — automated translations often don't.

### `:nth-of-type(N)` counts type-position, not class-position (added 2026-08-24)

`:nth-of-type(N)` is positional based on HTML tag type, NOT class. If the parent has:

```html
<div class="sub">
  <h2>Mode</h2>                  <!-- h2, ignored by nth-of-type(div) -->
  <div class="row">A</div>       <!-- div #1, IS .row -->
  <div>button container</div>    <!-- div #2, NOT .row -->
  <div class="stat">Ready.</div> <!-- div #3, NOT .row -->
  <div class="row">B</div>       <!-- div #4, IS .row -->
  <div class="row">C</div>       <!-- div #5, IS .row -->
</div>
```

Then `.row:nth-of-type(3)` matches `<div class="row">B</div>` (the 4th `<div>`), NOT the second `.row`. Adding any non-`.row` `<div>` sibling anywhere in the parent shifts every subsequent index.

**Wrong fix:** tweaking the N value to compensate. Fragile — any future addition of a `<div>` sibling breaks it again.

**Right fix:** ID-based traversal. Give each target element an ID, walk from the ID up to its enclosing wrapper:

```js
// Don't: '.row:nth-of-type(3) .lbl'
// Do:
function setLabelByInput(inputId, text) {
  var row = document.getElementById(inputId);
  if (!row) return;
  row = row.closest('.row');
  if (!row) return;
  var lbl = row.querySelector('.lbl');
  if (lbl) lbl.textContent = text;
}
```

**Trigger:** when you see `:nth-of-type(N)` in CSS or JS, ask "does this selector depend on the position of `<div>` siblings of mixed classes?" If yes, refactor to ID-based or wrap in a class-only container so `.nth-child(N)` of the parent is unambiguous.

### Orphan class hooks — JS queries `.foo` but nothing creates it (added 2026-08-24)

Symptom: a feature silently doesn't work. JS does `element.querySelector('.foo')` and gets `null`. No console error. No code path creates an element with `class="foo"`. The conditional branch never fires.

Audit recipe when debugging "JS feature X doesn't trigger despite the JS calling it":

```bash
# 1. Where JS queries the class:
grep -nE "querySelector(All)?\(['\"]\.foo['\"]\)" src/.../tis.js
# 2. Where HTML defines it statically:
grep -nE 'class="[^"]*\bfoo\b[^"]*"' src/.../tis.html
# 3. Where JS template strings create it dynamically:
grep -nE "['\"`][^'\"`]*\bfoo\b[^'\"`]*['\"`]" src/.../tis.js
```

If (1) finds a query but (2) is empty AND (3) doesn't show `foo` in any template literal → **orphan**. Decide:

- The JS branch is the right behavior → add `class="foo"` to wherever the wrapper is built (in JS template strings).
- The query is querying the wrong class → fix the query.

**Real example (2026-08-24):** `SOLVE_OUT.querySelector('.solved')` at the start of the ignore-flag-change handler always returned null. `solve()` built its result HTML with `<div class="solve-card">` but no code added `class="solved"` to anything in `SOLVE_OUT`. Result: the "ignore-flag flipped → auto re-solve" branch never fired. Fix: changed `class="solve-card"` to `class="solve-card solved"` in the wrapper template string.

**Why it's easy to miss:** orphan classes don't show up in HTML grep (the test is for static markup), don't show up in JS template strings (you have to scan template literals separately), and don't throw errors. The only signal is "this branch of code never runs" — which requires reading the conditional and tracing what populates the queried subtree.

**Companion pitfall (already in this skill, see the "Before deleting or renaming any HTML element with an `id`" pitfall above):** orphan classes are the same family — drift between template (static markup + JS template strings) and JS (queries). The fix pattern is the same: audit both directions before claiming a feature works.

### Key design decisions
the button visibility** — the same semantic shift must cascade to every
other consumer of the underlying state, or the UI becomes inconsistent:

```
ignore-tis-enrolled checkbox (single source of truth)
└─ IGNORE_TIS_ENROLLED IIFE-scope var (mirrors checkbox.checked)
└─ drop-all-enrolled button  → display:none when false
└─ renderPicked conflictMsg  → skip the conflict check for the enrolled rwh
└─ computePickedConflicts    → don't add the enrolled rwh to PICKED_CONFLICTS
└─ solve POST body           → locked_rwhs: Array.from(ENROLLED_RWH)
└─ server api_solve          → locked codes forced into every subset
└─ loadEnrolled() right panel → render 🔒 badge + lock banner
```

When you add the toggle, audit which other renderers, badges, banners,
or downstream API calls reference the gated state. If you only patch
the button, the user gets: "I can't drop the button but the conflict
warning still says 'conflicts with MSE307'" — inconsistent.

Three places this came up specifically:

1. **The destructive button itself** — gate visibility, don't
   `disabled=true` (the user already enforced this — see "Right-panel
   UX preferences" pitfall above).
2. **Visual surfacing** — the right panel should show that the toggle
   is set, e.g. `🔒 TIS-enrolled courses are locked — solver keeps
   them, cannot be dropped from here` banner, plus `🔒 locked` badges
   on each enrolled row. Without these, the user forgets the flag is
   set and wonders why dropping doesn't work.
3. **The downstream solver** — the user's "win every conflict" rule
   requires the solver to receive `locked_rwhs` in its POST body, AND
   the server to enforce "locked codes must appear in every subset"
   (the original solver tried to drop lowest-priority codes, which
   would drop the locked ones too — see the `_solve_subset` /
   `free_codes` / `locked_codes` split in `api_solve`).
