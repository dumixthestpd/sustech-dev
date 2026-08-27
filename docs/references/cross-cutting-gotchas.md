# Things that break across all SUSTech APIs

  dropping `p_xktjz` from the form encoding because it was None;
  TIS treats missing as 操作失败.

- **`TIS_UPD_XKXS_BY_GWC = /Xsxk/upd_xkxsBygwc` was a 404 phantom.**
  HAR has NO `upd_xkxsBygwc` calls — cart-update is folded into
  `addGouwuche` (which behaves like an upsert). Replaced the constant
  with an alias pointing at `TIS_ADD_GOUWUCHE_URL` so legacy
