#!/usr/bin/env bash
# probe_ncesnext.sh — re-check ncesnext.com's anti-bot posture.
#
# Run this BEFORE designing any new NCES integration. Four checks:
#   1. Behind Anubis PoW challenge? (anubis_challenge script in body)
#   2. Public JSON API up? (/api/v1/stats answers JSON without cookies)
#   3. iframe-embeddable? (no X-Frame-Options / frame-ancestors CSP)
#   4. /sitemap.xml reachable without a gate?
#
# Exits 0 if the posture matches the latest catalog note (gate DOWN,
# 2026-10-04), non-zero if anything flipped. Posture has flipped before
# (2026-07-05 gate up -> 2026-10-04 gate down) — treat a non-zero exit as
# "re-read the site before coding", not as an error.
#
# Windows note: bodies are kept in shell variables, never in temp files —
# native curl.exe cannot write MSYS /tmp paths (0-byte bodies, silently).
#
# Verified 2026-07-05 (gate up) and 2026-10-04 (gate down) — see
# references/ncesnext-anubis-2026-07-05.md and
# references/ncesnext-public-api-2026-10-04.md

set -uo pipefail
HOST="https://ncesnext.com"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120"

# fetch <url> -> sets REPLY_BODY / REPLY_CODE (body in a var: see Windows note)
fetch() {
    local out
    out=$(curl -sS --max-time 8 -A "$UA" -w '%{http_code}' "$1" 2>/dev/null) || out=""
    REPLY_CODE="${out: -3}"
    REPLY_BODY="${out:0:${#out}-3}"
}

probe() {
    fetch "$1"
    echo "  $1"
    echo "    HTTP/Size: $REPLY_CODE ${#REPLY_BODY}"
    if printf '%s' "$REPLY_BODY" | grep -q 'anubis_challenge'; then
        echo "    Body:      Anubis challenge (PoW gate active)"
    elif printf '%s' "$REPLY_BODY" | grep -qi '<title>'; then
        local title; title=$(printf '%s' "$REPLY_BODY" | grep -oE '<title>[^<]+' | head -1)
        echo "    Body:      Real HTML — title: $title"
    else
        echo "    Body:      Unknown"
    fi
}

header_check() {
    echo "$1"
    local hdr; hdr=$(curl -sSI --max-time 8 -A "$UA" "$HOST/search?q=test" 2>/dev/null) || true
    for h in X-Frame-Options "Content-Security-Policy"; do
        if echo "$hdr" | grep -qi "^$h:"; then
            echo "    $h: $(echo "$hdr" | grep -i "^$h:" | head -1 | tr -d '\r')"
        else
            echo "    $h: (absent — OK)"
        fi
    done
}

anubis_up=0; api_up=0; fail=0

echo "=== ncesnext.com anti-bot posture check ==="
echo

echo "[1] Anubis PoW challenge on common paths"
probe "$HOST/"
probe "$HOST/search?q=MSE306"
probe "$HOST/course/8721/"
[ "$REPLY_CODE" = "200" ] && printf '%s' "$REPLY_BODY" | grep -q 'anubis_challenge' && anubis_up=1
echo

echo "[2] public JSON API (/api/v1/stats, no cookies)"
fetch "$HOST/api/v1/stats"
echo "    $HOST/api/v1/stats"
echo "    HTTP/Body: $REPLY_CODE $(printf '%s' "$REPLY_BODY" | head -c 80)"
if [ "$REPLY_CODE" = "200" ] && printf '%s' "$REPLY_BODY" | head -c 1 | grep -q '{'; then
    api_up=1
else
    echo "    Body:      no JSON — API gated or moved"
fi
echo

echo "[3] iframe-embeddable?"
header_check "Response headers on /search?q=test"
echo

echo "[4] Sitemap & robots.txt (discovery endpoints)"
probe "$HOST/sitemap.xml"
probe "$HOST/robots.txt"
echo

echo "=== summary ==="
if [ "$anubis_up" = 1 ]; then
    echo "Anubis gate: UP (challenge served) — posture flipped back to 2026-07-05"
    fail=1
else
    echo "Anubis gate: down — no challenge served on any probe path"
fi
if [ "$api_up" = 1 ]; then
    echo "Public API:  up — /api/v1/stats answers JSON without auth"
else
    echo "Public API:  NOT answering — re-check before coding against it"
    fail=1
fi
echo "Expected posture (2026-10-04 note): gate down, API up."
echo "If either line above disagrees, update the catalog note before coding."
exit "$fail"
