# Verifying a TIS form fix against the HAR


When fixing bugs in `_build_queryform` / `submit_bids` / any function that
serializes data to TIS, **don't trust the test suite alone** — TIS silently
rejects malformed payloads with `操作失败` and no diagnostic. The verification
is byte-comparison against a **captured HAR from a real successful submission**.

Recipe:

1. User captures a successful HAR (Chrome DevTools → Network → save all as HAR
   with `.har` extension or `.zip` with `*.txt` request bodies).
2. Extract the form body of a known-good write call (e.g. `updXkxsByyx`).
3. In Python, build the same form via the fixed function with the **same input
   values** the HAR used.
4. Compare the two sorted-by-key form strings:

```python
def normalize_form(form: dict) -> str:
    # Drop None values (TIS rejects those); sort for deterministic comparison
    items = [(k, v) for k, v in form.items() if v is not None]
    items.sort()
    return "&".join(f"{k}={v}" for k, v in items)

har_body = "p_xktjz=rwtjzyx&p_xkfsdm=yixuan&..."
ours = normalize_form(_build_queryform(round_code="yixuan", xktjz="rwtjzyx", ...))
# Assert: set(har_body.split('&')) == set(ours.split('&'))  # exact key set
# Assert: all(kv in ours.split('&') for kv in har_body.split('&'))  # subset
```

5. **Diff the keys, not the values.** Missing keys = TIS silently rejects.
   Extra keys = usually tolerated but not guaranteed. Wrong flag values
   (e.g. `p_sfsyxkgwc=1` vs `=0`) = silent rejection with the same `操作失败`.

**Step 6 (added 2026-08-09, after the dry-run lesson):** byte-match against
the HAR proves the **printer** produces the right bytes — NOT that the
network request succeeds. After the byte-match passes, fire **at least one
real POST against TIS** with a single test rwh, capture the response, and
confirm `jg="1"` and a sensible `message`. Do this BEFORE declaring the
write path verified. Reason: dry-run of a queryform that prints
`{rwh: ..., p_id: ...}` proves the printer works; TIS still has a chance
to reject the actual bytes for reasons the HAR didn't capture.

**Real bugs caught this way on 2026-08-08:**

- Missing keys: `cxsfmt`, `mxpylx`, `p_chaxunxkfsdm`, `pageNum`, `pageSize`
- Wrong value: `p_sfsyxkgwc="1"` (HAR: `"0"`), `p_pylx` defaulted to `None`
  (HAR: `"1"`)
- Missing current-term: `p_dqxn`/`p_dqxq`/`p_dqxnxq` not populated from
  `_fetch_dq()`

**Real bugs caught by the live-write step on 2026-08-09** (HAR byte-match
passed but real POST still 操作失败 — these are the ones dry-run can't
catch):

- **`p_id` is NOT the human-readable `rwh`.** TIS write endpoints
  (`addGouwuche`, `addXuanke`, `updXkxsByyx`, `tuike`, `delGouwuche`)
  take a 32-char hex UUID from `queryKxrw`'s `row.id` field, NOT the
  `rwh` ("任务号") like `2026-2027-1-MSE301-002`. The hex id is on
  personal-mode rows only — the catalog (`queryRwxxcxList`) doesn't
  carry it. The docstring hedge "if TIS rejects, pass a different
  `id_field` value" was wrong; the correct answer is "the catalog
  doesn't carry it, run a personal search first to populate it."
  Course.id is the field. Wire it from the catalog after a
  `search_personal` call merges the result rows in.

- **`p_xkfsdm` must be set on every write endpoint**, not empty.
