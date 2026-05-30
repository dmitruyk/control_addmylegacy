#!/bin/sh
set -e

ROOT="${1:-/var/www/control-addmylegacy}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
SOURCE="${SCRIPT_DIR}/updating.html"
SYNOLOGY_SOURCE="${SCRIPT_DIR}/synology-tv-wait.html"
TARGET="${ROOT}/updating.html"
SYNOLOGY_TARGET="${ROOT}/synology-tv-wait.html"

if [ ! -f "$SOURCE" ]; then
  echo "Missing source file: $SOURCE" >&2
  exit 1
fi

mkdir -p "$ROOT"
cp "$SOURCE" "$TARGET"
cp "$SYNOLOGY_SOURCE" "$SYNOLOGY_TARGET"
chmod 644 "$TARGET" "$SYNOLOGY_TARGET"

echo "Installed updating placeholders:"
echo "  $TARGET"
echo "  $SYNOLOGY_TARGET"
echo ""
echo "Optional: point the TV browser to synology-tv-wait.html on Web Station"
echo "when the Docker container is fully stopped."
echo ""
echo "Verify:"
echo "  ls -la $TARGET"
echo ""
echo "If using nginx, reload after updating deploy/nginx.control.example.conf:"
echo "  sudo nginx -t && sudo nginx -s reload"
