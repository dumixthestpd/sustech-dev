# TIS write endpoints — HAR-derived field map (2026-08-09)

Verified against `/Users/dumix/Downloads/tis.sustech.edu.cn.har`
(10.8 MB, captured 2026-08-08 during a real successful course-selection
session by a test account).

## Endpoints observed

| Endpoint | Method | Purpose | HAR calls |
|---|---|---|---|
| `Xsxk/queryKxrw` | POST | personal-mode search | many |
| `Xsxk/queryYxkc` | POST | round config + cart/enrolled snapshot | 1+ |
| `Xsxk/queryXkdqXnxq` | POST | current TIS active term | 1+ |
| `Xsxk/queryRwxxcxList` | POST | campus catalog (in `Xsxktz/` not `Xsxk/`) | many |
| `Xsxk/addGouwuche` | POST | add to cart | 1 |
| `Xsxk/updXkxsByyx` | POST | update bid on enrolled | 1 |
| `Xsxk/tuike` | POST | drop | 1 |

**`Xsxk/upd_xkxsBygwc` does NOT exist** — that URL 404s. Cart-update
is folded into `addGouwuche` (upsert semantics). The Python constant
`TIS_UPD_XKXS_BY_GWC` in `selectcourse.endpoints` is an alias pointing
at `TIS_ADD_GOUWUCHE_URL`.

## `p_id` vs `rwh` — the critical distinction

Both fields exist in queryKxrw rows:

| Field | Shape | Use |
|---|---|---|
| `rwh` | `"2026-2027-1-MSE301-002"` (human-readable 任务号) | Display label, lookup key |
| `id`  | `"5069899DC41FD1D5E0631F1712ACA7BD"` (32-char hex UUID) | **Write endpoint key** — goes in `p_id` |

Every successful HAR write call uses the hex `id` as `p_id`. The `rwh`
is never used in a write payload. Catalog rows (`queryRwxxcxList`)
have `rwh` only; personal-mode rows (`queryKxrw`) have both.

If you only have the catalog's `rwh`, you must run a personal-mode
search first to populate the hex `id`, then merge into the catalog
cache (`search_personal` already does this — see the merge logic in
`selectcourse.py`).

## Per-endpoint canonical body

All three write endpoints (`addGouwuche`, `updXkxsByyx`, `tuike`)
share the same queryform shape (~44 keys). The differences are:

| Field | addGouwuche | updXkxsByyx | tuike |
|---|---|---|---|
| `p_xkfsdm` | `"bxxk"` | `"yixuan"` | `"yixuan"` |
| `p_xktjz` | `"rwtjzyx"` | `"rwtjzyx"` | `"rwtjzyx"` |
| `p_xkxs` (bid) | `"1"` | `"5"` (current value being set) | `"5"` (any int) |
| `p_id` (hex UUID) | 32-char hex | 32-char hex | 32-char hex |

### addGouwuche (canonical successful HAR body)

```
cxsfmt=0&p_pylx=1&mxpylx=1&p_sfgldjr=0&p_sfredis=0&p_sfsyxkgwc=0
&p_xktjz=rwtjzyx&p_chaxunxh=&p_gjz=&p_skjs=
&p_xn=2026-2027&p_xq=1&p_xnxq=2026-20271
&p_dqxn=2025-2026&p_dqxq=3&p_dqxnxq=2025-20263
&p_xkfsdm=bxxk&p_xiaoqu=&p_kkyx=&p_kclb=
&p_xkxs=1&p_dyc=&p_kkxnxq=
&p_id=4EFDC62C358DA047E0631F1712ACE9E6
&p_sfhlctkc=0&p_sfhllrlkc=0
&p_kxsj_xqj=&p_kxsj_ksjc=&p_kxsj_jsjc=
&p_kcdm_js=&p_kcdm_cxrw=&p_kcdm_cxrw_zckc=
&p_kc_gjz=&p_xzcxtjz_nj=&p_xzcxtjz_yx=&p_xzcxtjz_zy=
&p_xzcxtjz_zyfx=&p_xzcxtjz_bj=
&p_sfxsgwckb=1&p_skyy=&p_sfmxzj=&p_chaxunxkfsdm=
&pageNum=1&pageSize=19
```

Response: `{"gjhczztm":"OPERATE.RESULT_SUCCESS","message":"操作成功","jg":"1"}`

### updXkxsByyx (canonical successful HAR body)

```
cxsfmt=0&p_pylx=1&mxpylx=1&p_sfgldjr=0&p_sfredis=0&p_sfsyxkgwc=0
&p_xktjz=rwtjzyx&p_chaxunxh=&p_gjz=&p_skjs=
&p_xn=2026-2027&p_xq=1&p_xnxq=2026-20271
&p_dqxn=2025-2026&p_dqxq=3&p_dqxnxq=2025-20263
&p_xkfsdm=yixuan&p_xiaoqu=&p_kkyx=&p_kclb=
&p_xkxs=5&p_dyc=&p_kkxnxq=
&p_id=587ED17D2EFCF6BAE0631F1712AC1493
&p_sfhlctkc=0&p_sfhllrlkc=0
&p_kxsj_xqj=&p_kxsj_ksjc=&p_kxsj_jsjc=
&p_kcdm_js=&p_kcdm_cxrw=&p_kcdm_cxrw_zckc=
&p_kc_gjz=&p_xzcxtjz_nj=&p_xzcxtjz_yx=&p_xzcxtjz_zy=
&p_xzcxtjz_zyfx=&p_xzcxtjz_bj=
&p_sfxsgwckb=1&p_skyy=&p_sfmxzj=&p_chaxunxkfsdm=
&pageNum=1&pageSize=19
```

Response: `{"message":"操作成功","jg":"1"}`

### tuike (canonical successful HAR body)

Same as `updXkxsByyx` (same `p_xktjz`, same `p_xkfsdm`, same
`p_xkxs`). Response: `{"gjhczztm":"OPERATE.RESULT_SUCCESS","message":"操作成功","jg":"1"}`

## Always-set keys (the "if empty → 操作失败" set)

These keys MUST be non-empty in any write payload — TIS rejects the
request silently if any is empty:

- `p_id` (32-char hex UUID)
- `p_xkfsdm` (round code — `bxxk`/`yixuan`/`kzyxk`/...)
- `p_xktjz` (HAR shows `rwtjzyx` for all 3 write endpoints)
- `p_pylx` (`"1"` undergrad / `"2"` grad — HAR shows `"1"`)
- `p_xn`, `p_xq`, `p_xnxq` (target term)
- `p_dqxn`, `p_dqxq`, `p_dqxnxq`, `cxsfmt` (current active term — comes
  from `queryXkdqXnxq`, cached for the session)
- `pageNum`, `pageSize` (HAR shows `1` and `19`)
- `mxpylx` (mirror of `p_pylx` — HAR shows `"1"`)

## Always-empty keys (don't set these for writes)

These are in the queryform but HAR shows them as empty. Setting them
to non-empty values may or may not break TIS, but the HAR shows them
empty so leave them empty:

- `p_chaxunxh`, `p_gjz`, `p_skjs`, `p_xiaoqu`, `p_kkyx`, `p_kclb`,
  `p_dyc`, `p_kkxnxq`, `p_kxsj_xqj`, `p_kxsj_ksjc`, `p_kxsj_jsjc`,
  `p_kcdm_js`, `p_kcdm_cxrw`, `p_kcdm_cxrw_zckc`, `p_kc_gjz`,
  `p_xzcxtjz_nj`, `p_xzcxtjz_yx`, `p_xzcxtjz_zy`, `p_xzcxtjz_zyfx`,
  `p_xzcxtjz_bj`, `p_skyy`, `p_sfmxzj`, `p_chaxunxkfsdm`

## Always-empty-OR-specific-value flags

- `p_sfgldjr="0"` (是否管理端进入)
- `p_sfredis="0"` (是否Redis缓存)
- `p_sfsyxkgwc="0"` (是否使用选课购物车 — HAR shows `0`, NOT `1` as the
  Python originally had)
- `p_sfhlctkc="0"` or `"1"` (是否忽略冲突课程 — flag, not empty)
- `p_sfhllrlkc="0"` or `"1"` (是否忽略零容量课程)
- `p_sfxsgwckb="1"` (是否显示购物课表)

## `p_xkxs` semantics

`p_xkxs` is the 选课系数 (selection coefficient / bid). For:
- `addGouwuche` (first add): HAR shows `"1"` (default)
- `updXkxsByyx` (update bid): HAR shows the new value being set
- `tuike`: HAR shows any int (TIS doesn't check on tuike)

The Python code currently defaults to `None` (omitted). TIS rejects
with `操作失败` if `p_xkxs` is missing on `addGouwuche`/`updXkxsByyx`
during a 积分 (credit-based) round.

## Diagnosing "silent 操作失败" rejections

If `_post_xsxk` raises `EnrollmentError(jg="-1", message="操作失败")`:

1. Confirm `p_id` is the 32-char hex UUID, not the `rwh`. Most common cause.
2. Confirm `p_xkfsdm` is set. Second most common.
3. Confirm `p_xktjz` is set. Third.
4. Check that the round is actually open for the user
   (`SELECTION_INFO.kc_rq_open`) — a closed round silently 操作失败's.
5. Check the 32-key form against this reference HAR body — any
   mismatch is suspect.

## Reproducing a single pick with byte-exact verification

```python
import json
from urllib.parse import parse_qs

with open("/Users/dumix/Downloads/tis.sustech.edu.cn.har") as f:
    har = json.load(f)

# Find a successful updXkxsByyx call
for entry in har["log"]["entries"]:
    if "updXkxsByyx" not in entry["request"]["url"]:
        continue
    pd = entry["request"].get("postData", {}) or {}
    text = pd.get("text", "") if isinstance(pd, dict) else ""
    qs = parse_qs(text)
    print(f"p_id:        {qs.get('p_id', [''])[0]}")
    print(f"p_xkfsdm:    {qs.get('p_xkfsdm', [''])[0]}")
    print(f"p_xkxs:      {qs.get('p_xkxs', [''])[0]}")
    print(f"p_xn/xq/xnxq:{qs.get('p_xn', [''])[0]}/{qs.get('p_xq', [''])[0]}/{qs.get('p_xnxq', [''])[0]}")
    print(f"p_dqxn/xq/xnxq:{qs.get('p_dqxn', [''])[0]}/{qs.get('p_dqxq', [''])[0]}/{qs.get('p_dqxnxq', [''])[0]}")
    print(f"cxsfmt:      {qs.get('cxsfmt', [''])[0]}")
    print(f"p_pylx/mxpylx:{qs.get('p_pylx', [''])[0]}/{qs.get('mxpylx', [''])[0]}")
    # 30+ more keys, but these are the high-signal ones
    break
```

## Source

HAR file: `~/Downloads/tis.sustech.edu.cn.har` (10,816,645 bytes,
captured 2026-08-08 during testing). User message confirming the
session worked: "操作成功" responses on all three write endpoints.

If the file is missing, the user's Chrome DevTools → Network → "Save
all as HAR with content" reproduces it in one click.