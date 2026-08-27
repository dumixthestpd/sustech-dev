# API naming law — our public API is NOT TIS ping-speak


TIS uses cryptic `p_xktjz`, `p_xkfsdm`, `kclbdm`, `xkfsdm` etc. names internally.
We do NOT propagate those to our public API surface. The user's directive
(verbatim, 2026-08-08): *"Do not build our module's most important APIs with the
bad naming conventions of TIS system. TIS systems uses pings for their naming,
and that is an unhealthy way of naming."*

Two layers, two naming conventions:

| Layer              | Naming                          | Examples                                              |
|--------------------|---------------------------------|-------------------------------------------------------|
| **Our public API** | Semantic English                | `round_code`, `category_name`, `enrolled_list`, etc.  |
| **Wire format**    | TIS's `p_*` / `xkfsdm` names    | `p_xktjz=rwtjzyx`, `p_xkfsdm=bxxk`, `p_sfsyxkgwc=0` |

The wire layer (`_build_queryform` inside the selectcourse module) is allowed
to use `p_*` keys because those are the actual bytes TIS expects on the wire
— re-translating them to semantic names there adds no value and risks drift.
**Everything OUTSIDE the wire layer** uses semantic names.

Concrete renames already shipped (commit `0540e0a`):

- `KCLBDM_MAP` → `CATEGORY_MAP`
- `KCLBDM_REVERSE` → `CATEGORY_REVERSE`
- `kclbmc_to_code` → `category_name_to_code`
- `xkfsdm` (Python param) → `round_code`
- `KCLBDM_TASK_TO_CART` (`rwtjzgwc`, wrong) → `XKTJZ_TASK_TO_ENROLLED` (`rwtjzyx`, HAR-verified)

Back-compat aliases are kept for at least one minor version
(`KCLBDM_MAP = CATEGORY_MAP`); expose new semantic names in `__init__.py` with
a "Naming note" docstring so the next agent sees the convention.

**Test for naming hygiene:** when adding a new function/field, ask *"would a
fresh reader understand this name without knowing TIS internals?"* If no, it's
a ping and needs renaming.
