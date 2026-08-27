
When implementing a domain transform (e.g. course schedule → .ics calendar),
the temptation is to write it directly in `static/<sub>/<sub>.js` because
"the button is right there in the JS." **Don't.** This violates the split.

Wrong: `exportICS()` function in `tis.js`, exporting a Blob from the frontend.
The button click is the surface (UI), but the transformation is domain.

Right: `sustech_survival.selectcourse.ical.courses_to_ical(courses, semester)`
in the Python module. Pure transform — no Flask, no JSON, no fetch. Returns
a string. The blueprint does `return Response(courses_to_ical(...), mimetype="text/calendar")`
and the JS does `window.location = "/api/tis/ical"` to download. **Two layers,
one line of glue.**

Tests for "did I just violate the split?":
- Does the function name match a domain concept (calendar generation, schedule
  merging, conflict detection)? → Should be in the module.
- Does the function take a `Course` object or a `dict` that mirrors a `Course`? → Module.
- Does the function return JSON / HTML / a Blob / a base64 string? → Module
  (the data) + blueprint (the HTTP wrapper).
- Does the function read DOM or call `fetch()` / `XMLHttpRequest`? → UI only.
  If you need data from the backend, fetch it — don't recompute it client-side.

The split matters because:
- Tests can exercise pure transforms without a browser, Flask, or a network.
- The same transform can be reused from a CLI, a script, or another blueprint.
- Localization / format changes don't require touching the JS bundle.
- "I'll just put it in JS for now, move it later" never happens — the JS
  becomes load-bearing and untouchable.
