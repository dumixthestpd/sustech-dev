# sustech-survival brand assets

Vector logo files shipped with the package, saved 2026-07-13.

## Files

All live in `src/sustech_survival/resources/` and ship in the wheel via
`[tool.hatch.build.targets.wheel] include` + `MANIFEST.in recursive-include`.

| File | viewBox | What it is | When to use |
|---|---|---|---|
| `logo.svg` | `186 115 372 537` | Geometry-only brush mark (squirrel + 智) | Favicon, app icon, anywhere a small mark is needed |
| `logo-full.svg` | `790 801 1834 1053` | Zoomed lockup (brush + handwritten "sustech_survival") | README header, login screen, paper mentions, docs |
| `logo-full-source.svg` | `0 0 3508 2480` | Same lockup at source-image dimensions | Raster-replacement use cases where exact pixel positions matter |

## Colors (DO NOT change without asking the user)

| Element | Color | Notes |
|---|---|---|
| Brush mark | `#ed7005` | Single color, no gradient, no feather |
| Handwritten text | `#004851` | Below the brush in the lockup |
| Background | `#ffffff` | Explicit `<rect fill="#ffffff"/>` |

The user explicitly rejected the multi-color gradient variants
(`#fad4b4` feather, etc.) in favor of the solid-color version. Don't
re-introduce gradients unless the user asks.

## Author metadata

All three SVGs carry Dublin Core metadata:

```xml
<dc:creator>dumix &lt;dumix@local&gt;</dc:creator>
<dc:title>...</dc:title>
<dc:rights>PolyForm Noncommercial License 1.0.0</dc:rights>
```

`dumix@local` is the canonical alias — never use a real `@sustech.edu.cn`
address in published assets.

## Access from Python

```python
from importlib.resources import files
logo_svg = files("sustech_survival").joinpath("resources/logo.svg").read_text()
```

Or from a path-aware context:

```python
from importlib.resources import as_file
with as_file(files("sustech_survival").joinpath("resources/logo-full.svg")) as p:
    # p is a Path to a real file (use for upload, copy, etc.)
    ...
```

## Wiring status (as of 2026-07-13)

The user said: *"we'll talk about including the logos in our work later."*
So:

- ❌ README.md does NOT yet reference these assets.
- ❌ webui/ does NOT yet serve them.
- ❌ docs/ do NOT yet embed them.
- ✅ Assets exist on disk and ship in the wheel.

When wiring later, the natural places are:
- `README.md` first paragraph — `![logo-full](src/sustech_survival/resources/logo-full.svg)`
- `webui/` landing page — the brush mark in the corner
- login screen background — the lockup at low opacity
- `docs/resources.md` — explicit listing for users who want to reuse

## Versioning the assets

If the user ever wants a refresh (new brush stroke, color tweak, layout
change), the workflow is:

1. Re-trace from the source raster using `raster-to-vector-svg` skill.
2. Apply the same two-version pattern (zoomed + source).
3. Update Dublin Core `<dc:title>` to indicate the version.
4. Re-render with `rsvg-convert -b white -w 800 <file>.svg -o preview.png`
   for visual verification before commit.
5. Commit assets, README/docs can stay unchanged until the user wires them.