#!/usr/bin/env python3
"""
probe_tis_kclbdm.py — Fetch TIS kclbdm codes directly from the authoritative source.

WHY THIS EXISTS
===============
TIS's personal-mode search (/Xsxk/queryKxrw) accepts only kclbdm codes in
p_kclb, not the bare kclbmc name. But the correct way to get the mapping
is NOT brute-probing — it's calling the ACTUAL endpoint that the TIS
SPA uses: component/queryKclb.

HOW IT WORKS
============
The TIS xsxk page loads a component bundle `/component/inco/inco.component.kclb-*.js`
that calls `$.post(baseUrl+'component/queryKclb', {"pylb": this.pylb}, ...)`.
This returns the full kclb dictionary as `res.content` — an array of 22
undergrad and 9 graduate entries with {dm, mc, ywmc, level}.

No brute force, no guessing. Found by following the SPA JS bundle walk
methodology (see sustech-dev SKILL.md).

USAGE
=====
    cd /Users/dumix/.openclaw/code/sustech_survival
    python scripts/probe_tis_kclbdm.py

Requires: TISAuth with working CAS login (credentials.txt with username/password).
No need for the webui to be running.

The mapping discovered as of 2026-07-08 (verified live against TIS):
    22 undergrad codes (pylb=1), 9 graduate codes (pylb=2)
    Sub-categories (level=2) like 美育类=0907 HAVE codes — verified
    with live TIS search returning correct filtered results.

See sustech-dev references/tis-kclbdm-discovery-2026-07-08.md for the
complete verified mapping table.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")

from sustech_survival.sso import TISAuth

# The endpoint the TIS SPA actually calls (NOT /Xsxk/queryKclb which 404s)
KCLB_ENDPOINT = "https://tis.sustech.edu.cn/component/queryKclb"

auth = TISAuth()
auth.ensure()
sess = auth.session
sess.headers["X-Requested-With"] = "XMLHttpRequest"
sess.headers["Referer"] = "https://tis.sustech.edu.cn/Xsxk/query/1"

results = {}
for pylb in ("1", "2"):
    label = {"1": "本科 (undergrad)", "2": "研究生 (graduate)"}[pylb]
    print(f"\n=== pylb={pylb} ({label}) ===", flush=True)
    try:
        r = sess.post(KCLB_ENDPOINT, data={"pylb": pylb}, timeout=30)
        data = r.json()
        content = data if isinstance(data, list) else data.get("content", [])
        print(f"  Status: {r.status_code}, entries: {len(content)}", flush=True)
        results[pylb] = content
        for item in content:
            dm = item.get("dm", "?")
            mc = item.get("mc", "?")
            level = item.get("level", "?")
            ywmc = item.get("ywmc", item.get("mc_en", ""))
            print(f"  {dm:>4} | {mc:20s} | lv={level} | {ywmc or '—'}", flush=True)
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)
        results[pylb] = []

out_path = "/tmp/kclbdm_mapping.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nSaved -> {out_path}", flush=True)
