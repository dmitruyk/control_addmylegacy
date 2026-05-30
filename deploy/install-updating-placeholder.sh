#!/bin/sh
set -e

ROOT="${1:-/var/www/control-addmylegacy}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
SOURCE="${SCRIPT_DIR}/updating.html"
SYNOLOGY_SOURCE="${SCRIPT_DIR}/synology-tv-wait.html"
TARGET="${ROOT}/updating.html"
MISSING_TARGET="${ROOT}/missing"
SYNOLOGY_TARGET="${ROOT}/synology-tv-wait.html"

if [ ! -f "$SOURCE" ]; then
  echo "Missing source file: $SOURCE" >&2
  exit 1
fi

mkdir -p "$ROOT"
cp "$SOURCE" "$TARGET"
cp "$SOURCE" "$MISSING_TARGET"
cp "$SYNOLOGY_SOURCE" "$SYNOLOGY_TARGET"
chmod 644 "$TARGET" "$MISSING_TARGET" "$SYNOLOGY_TARGET"

echo "Installed offline wait pages:"
echo "  $TARGET"
echo "  $MISSING_TARGET   <- Synology 404 hook (GET /missing must return 200)"
echo "  $SYNOLOGY_TARGET"
echo ""
echo "Synology reverse proxy: add a rule so GET /missing serves $MISSING_TARGET"
echo "from Web Station BEFORE the Docker container rule. See deploy/SYNOLOGY-404.md"
echo ""
echo "Verify:"
echo "  ls -la $MISSING_TARGET"
echo "  curl -I https://control.addmylegacy.com/missing"
echo "  # must return HTTP 200, not Synology 404 circle"
