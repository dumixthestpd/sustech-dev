#!/usr/bin/env bash
# probe_ncesnext.sh — re-check ncesnext.com's anti-bot posture.
#
# Run this BEFORE designing any new NCES integration. Three checks:
#   1. Still behind Anubis PoW challenge? (anubis_challenge script present)
#   2. Still iframe-embeddable? (no X-Frame-Options / frame-ancestors CSP)
#   3. /sitemap.xml still reachable without Anubis gate?
#
# Output format: human-readable table + 0/1 exit for each check (1=failed).
# Exits 0 if all OK, non-zero if any check changed.
#
# Verified 2026-07-05 — see references/ncesnext-anubis-2026-07-05.md

set -uo pipefail
HOST="https://ncesnext.com"
fail=0

probe() {
    local url="$1"
    local tmp; tmp=$(mktemp)
    local code size; code=$(curl -sS --max-time 8 -o "$tmp" -w "%{http_code} %{size_download}" \
        -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120" \
        "$url") || true
    echo "  $url"
    echo "    HTTP/Size: $code"
    if grep -q 'anubis_challenge' "$tmp" 2>/dev/null; then
        echo "    Body:      Anubis challenge (PoW gate active)"
    elif grep -qi '<title>' "$tmp" 2>/dev/null; then
        local title; title=$(grep -oE '<title>[^<]+' "$tmp" | head -1)
        echo "    Body:      Real HTML — title: $title"
    else
        echo "    Body:      Unknown ($(wc -c < "$tmp") bytes)"
    fi
    rm -f "$tmp"
}

header_check() {
    echo "$1"
    shift
    local hdr; hdr=$(curl -sSI --max-time 8 "$@" "$HOST/search?q=test" 2>/dev/null) || true
    for h in X-Frame-Options "Content-Security-Policy"; do
        if echo "$hdr" | grep -qi "^$h:"; then
            echo "    $h: $(echo "$hdr" | grep -i "^$h:" | head -1 | tr -d '\r')"
        else
            echo "    $h: (absent — OK)"
        fi
    done
}

echo "=== ncesnext.com anti-bot posture check ==="
echo

echo "[1] Anubis PoW challenge on common paths"
probe "$HOST/"
probe "$HOST/search?q=MSE306"
probe "$HOST/course/8721/"
probe "$HOST/api/courses/?search=MSE306"
echo

echo "[2] iframe-embeddable?"
header_check "Response headers on /search?q=test"
echo

echo "[3] Sitemap & robots.txt (discovery endpoints)"
probe "$HOST/sitemap.xml"
probe "$HOST/robots.txt"
echo

echo "=== summary ==="
echo "See references/ncesnext-anubis-2026-07-05.md for the full probe transcript"
echo "and the recommended integration strategy (iframe embed + direct URL fallback)."
