# Web UI Architecture — course selector + unified port

Date: 2026-07-06
Context: Preparing TIS course selector for 2026 Fall semester opening.

## Port unification

| Server | Old port | Status |
|--------|----------|--------|
| `webui/app.py` | 61019 | **Active** — single unified port |
| `tis/grid_server.py` | 8765 | Deprecated; delegates to webui with warning |
| `transit/__main__.py` serve | 61019 | Deprecated; delegates to webui |

Run: `python -m sustech_survival.webui serve --port 61019`

## Module structure

```
src/sustech_survival/webui/
├── __init__.py          # Docstring + exports (create_app, run)
├── __main__.py          # argparse: `serve [--port N] [--transit-data DIR]`
├── app.py               # Flask factory: landing page + register blueprints
├── blueprints/
│   ├── __init__.py      # (empty docstring)
│   ├── tis.py           # /tis page + /api/tis/* endpoints (582 lines)
│   ├── transit.py       # /transit page + /api/transit/live + static proxy
│   └── nces.py          # /api/nces/code/<code> + /api/nces/reviews/<code> (73 lines)
└── templates/
    ├── landing.html     # Navigation cards: /tis and /transit
    └── tis.html         # Full SPA: search, grid, solve, eval, bids (2211 lines)
```

## API surface

All routes under `/api/<submodule>/...`. Browser never touches SUSTech.

| Route | Method | What |
|-------|--------|------|
| `/api/tis/info` | GET | Semester + filter options (colleges, categories, campuses, languages, task_types) |
| `/api/tis/courses` | GET | Filtered course list. `mode=personal` (选课) or `mode=campus` (全校课表) |
| `/api/tis/refresh` | POST | Force re-fetch from TIS |
| `/api/tis/course/<rwh>` | GET | One section detail |
| `/api/tis/enrolled` | GET | Enrolled sections |
| `/api/tis/solve` | POST | Non-conflicting section combos |
| `/api/tis/add` | POST | Add course (dry-run by default) |
| `/api/tis/drop` | POST | Drop course (dry-run by default) |
| `/api/tis/add-to-cart` | POST | Cart add (dry-run) |
| `/api/tis/remove-from-cart` | POST | Cart remove (dry-run) |
| `/api/tis/course-types` | GET | xkfsdm tabs |
| `/api/tis/round` | GET | 剩余积分 + round window |
| `/api/tis/bids` | POST | Submit bid values |
| `/api/nces/code/<code>` | GET | NCES brief data for hover card + eval tab |
| `/api/nces/reviews/<code>` | GET | Full review list for a course |

## NCES eval wiring (do NOT use old endpoint)

**Dead route (removed):** `GET /api/tis/nces?code=X`
**Correct route:** `GET /api/nces/code/<code>`

The old `renderEval()` expected:
```js
d.direct_url         // → wrong, should be d.detail_url
d.results[]          // → wrong, should be d.review_excerpts[]
d.results[i].course  // → wrong, use d.name at top level
d.results[i].professor // → wrong, use d.teacher at top level
d.results[i].summary // → wrong, use d.review_excerpts[i].excerpt
```

The NCES `brief()` method returns:
```python
{
    "available": True,
    "code": str, "name": str, "teacher": str,
    "semester": str, "rating": float, "review_count": int,
    "dimensions": {
        "difficulty": {"label": str, "pct": int},
        "workload": {"label": str, "pct": int},
        "grading": {"label": str, "pct": int},
        "takeaways": {"label": str, "pct": int},
    },
    "detail_url": str,  # link to NCES course page
    "review_excerpts": [{"username": str, "semester": str, "likes": int, "excerpt": str}],
    "nces_teacher": str,
    "alternatives": [...],
}
```

Not-found from `not_found(code)`:
```python
{"available": False, "reason": "course not found in NCES",
 "search_url": "https://ncesnext.com/search?q=<code>"}
```

## Frontend patterns

### Filter pills
- Function `renderFilterPills()` reads all filter inputs and shows active ones as chips.
- Clicking the ✕ on a chip clears that filter and calls `loadCourses()`.
- Called at end of `loadCourses()` success handler.
- Uses `.filter-pill` CSS class (rounded, small, dark background).

### Schedule tags
- `formatScheduleHTML(slots)` outputs `<span class="slot-tag">Mon 3-4 一教125 1-16</span>` per slot.
- Container `.c-card .sched` uses `display:flex; flex-wrap:wrap; gap:.3rem`.
- Tags are compact dark badges with `white-space:nowrap`.

### JS scope rules
- All module-level helper functions must be at IIFE scope (same level as `loadCourses`, `renderBidPanel`).
- Functions inside `document.addEventListener('DOMContentLoaded', function() { ... })` are NOT accessible from IIFE scope.
- No `XN`/`XQ` global variables → use `currentXn()` / `currentXq()` / `sem()`.

### Loading bar — global fetch monkey-patch

A 2px animated bar at the top of the page that activates on every HTTP request:

```js
// Counter-based — stays active until ALL stacked requests finish
var LOADING = 0;
function showLoading() {
  LOADING++;
  if (LOADING === 1) {
    // fade bar in, start at 20%
    LB.classList.add('active');
    // clear stale results so user knows something is happening
    RESULTS.innerHTML = '<div class="loading">⟳ Loading…</div>';
    STAT.textContent = '⟳ Loading…';
    // animate bar 20% → ~85% with random increments
    fill._timer = setInterval(function() {
      if (fill._tick < 85) { fill._tick += Math.random() * 8; fill.style.width = fill._tick + '%'; }
    }, 600);
  }
}
function hideLoading() {
  if (LOADING > 0) LOADING--;
  if (LOADING === 0) {
    clearInterval(fill._timer);
    fill.style.width = '100%';  // snap to full
    setTimeout(fadeOut, 400);
    restore STAT to previous text
  }
}
// Monkey-patch fetch to auto-track
window.fetch = function(url, opts) {
  showLoading();
  return _origFetch(url, opts).then(r => { hideLoading(); return r; })
    .catch(e => { hideLoading(); throw e; });
};
```

**Key design choices:**
- Counter handles mode toggle (course-types + info + courses = 3 concurrent requests). Only hides on last completion.
- Stale results cleared immediately (not after response arrives) so the user doesn't stare at old data.
- STAT bar saves/restores previous text so a single-request transition (e.g. keyword debounce → courses fetch) is seamless.
- `showLoading()` is an idempotent guard (`if LOADING === 1`) — safe to call from the monkey-patch AND from explicit `loadCourses` code paths.

**Integration:** the monkey-patch wraps `window.fetch` at IIFE boot time. All `getJSON()` / `postJSON()` calls use `fetch()` under the hood, so all API calls are auto-tracked. The only non-fetch path is the hover brief's `$.ajax()` call (which should be converted to fetch if the brief card ever becomes a priority).

**CSS:**
```css
#loading-bar { position:fixed; top:0; left:0; z-index:9999; width:100%; height:2px; pointer-events:none; opacity:0; transition:opacity .15s }
#loading-bar.active { opacity:1 }
#loading-bar .lb-fill { height:100%; width:0; background:linear-gradient(90deg,var(--accent),#7fb0ff,var(--accent)); background-size:200% 100%; animation:lb-shimmer 1.2s ease infinite }
@keyframes lb-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
```
