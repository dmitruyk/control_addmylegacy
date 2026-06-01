#!/usr/bin/env python3
"""Build self-contained wait pages for Synology (no Docker / static files required)."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WAIT_SHELL = ROOT / "templates" / "core" / "wait_shell.html"
TV_BOOT_JS = ROOT / "static" / "js" / "tv-boot.js"
OUTPUT_PATHS = (
    ROOT / "deploy" / "updating.html",
    ROOT / "static" / "updating.html",
)

SITE_URL = os.environ.get("SITE_URL", "https://control.addmylegacy.com").rstrip("/")
SITE_NAME = os.environ.get("SITE_NAME", "Addmlegacy Control")
POLL_SECONDS = os.environ.get("TV_HEALTH_POLL_SECONDS", "3")


def build_html() -> str:
    template = WAIT_SHELL.read_text(encoding="utf-8")
    tv_boot = TV_BOOT_JS.read_text(encoding="utf-8")

    html = template.replace("{{ SERVICE_BASE_URL }}", SITE_URL)
    html = html.replace("{{ SERVICE_MODE }}", "production")
    html = html.replace("{{ poll_seconds }}", POLL_SECONDS)
    html = html.replace("{{ SITE_NAME }}", SITE_NAME)

    match = re.search(
        r"\{%\s*load static\s*%\}\s*"
        r'<script src="\{% static \'js/tv-boot\.js\' %\}\?v=\{\{ STATIC_BUILD_ID \}\}"></script>',
        html,
        flags=re.DOTALL,
    )
    if not match:
        print("build_missing_static: could not find tv-boot.js script tag in wait_shell.html", file=sys.stderr)
        sys.exit(1)

    html = html[: match.start()] + "<script>\n" + tv_boot + "\n</script>" + html[match.end() :]

    if 'src="/static/js/tv-boot.js' in html or "{% static" in html:
        print("build_missing_static: template still has external tv-boot.js reference", file=sys.stderr)
        sys.exit(1)

    return html


def main() -> None:
    html = build_html()
    for path in OUTPUT_PATHS:
        path.write_text(html, encoding="utf-8")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
