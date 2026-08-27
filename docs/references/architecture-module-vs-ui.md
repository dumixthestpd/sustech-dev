# Architecture: Module vs Web UI Boundary

The `sustech-survival` codebase splits responsibility between the
**module** (`src/sustech_survival/<sub>/`) and the **web UI blueprints**
(`webui/blueprints/<sub>.py`). Misplacing these creates silent coupling
that's painful to undo later.

## The module owns the DOMAIN

What the data means, how it's interpreted, all shaping that depends on
knowing what the user wants.

Specifically:
- Domain methods (e.g. `search_course`, `fetch_reviews`)
- Response shaping for the UI (e.g. `NCESScraper.brief()` returns the
  exact dict the UI consumes — top-N reviews, truncated excerpts,
  `{label, pct}` dimensions, alternatives list)
- "Not found" payloads with reason (`NCESScraper.not_found()`)
- Caching, parsing, retries, all auth handshake concerns
- All "what does the user want" logic (top-N, truncation length, label
  format, fallback strategy)

## The web UI blueprint owns the SURFACE

How the user reaches the module — and **nothing else**.

- Parse HTTP query params
- Call **one** module method
- `jsonify` the result
- Process-wide singleton lifecycle (`_get_scraper()`)

**Zero data shaping, zero sorting, zero truncation, zero field
restructuring** in the blueprint.

## Concrete pattern — NCES blueprint refactor

Before (BAD — webui doing domain work, ~50 lines):

```python
reviews = s.fetch_reviews(code, teacher=teacher)
review_excerpts = []
if reviews:
    sorted_revs = sorted(reviews, key=lambda r: r.get("likes", 0), reverse=True)
    for r in sorted_revs[:3]:
        text = r.get("text", "")
        review_excerpts.append({
            "username": r.get("username", ""),
            "excerpt": text[:200] if text else "",
            ...
        })
return jsonify({
    "available": True, "code": course.code, ...,
    "review_excerpts": review_excerpts,
    "dimensions": {...},
})
```

After (GOOD — module returns the exact dict, blueprint is 9 lines):

```python
# In module — knows the brief format
def brief(self, code, *, teacher="", xn="", xq="") -> dict | None:
    course, exact_match, alternatives = self.search_course(code, ...)
    if course is None:
        return None
    reviews = self.fetch_reviews(code, teacher=teacher) or []
    top = sorted(reviews, key=lambda r: r.get("likes", 0), reverse=True)[:3]
    excerpts = [
        {"username": r.get("username", ""),
         "excerpt": (r.get("text", "") or "")[:200], ...}
        for r in top
    ]
    return {
        "available": True, "code": course.code, ...,
        "review_excerpts": excerpts,
        "dimensions": {...},
    }

def not_found(self, code: str) -> dict:
    return {"available": False, "reason": "course not found in NCES",
            "search_url": f"{self.BASE}/search?q={code}"}

# In blueprint — dumb transport
return jsonify(
    _get_scraper().brief(code, teacher=..., xn=..., xq=...)
    or _get_scraper().not_found(code)
)
```

## When to apply this boundary

Whenever adding or modifying any web endpoint:

| Logic type | Where it goes |
|---|---|
| Sort/filter/truncate | **Module** |
| Field rename/restructure | **Module** |
| "Not found" payload with reason | **Module** |
| Top-N by some criterion (likes, recency) | **Module** |
| Shape conversion (tuple → `{label, pct}`) | **Module** |
| Parse query params, JSON encode, HTTP errors | **Blueprint** |
| Process-wide singleton | **Blueprint** |
| Status/refresh endpoints (pass-through) | **Blueprint** |

## Test the boundary

Read the blueprint file. If it has `sorted(`, `.slice()`, `.find()`,
`if reviews:` style logic on domain data → the logic is misplaced.

## Reference case

`webui/blueprints/nces.py:api_nces_code()` after the 2026-07 refactor
is 9 lines. The module owns the `brief()` and `not_found()` shapes.
