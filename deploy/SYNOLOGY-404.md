# Synology 404 handling

When the Docker container stops, Synology shows a **gray 404 circle** instead of the app. Synology's 404 page XHRs `GET /missing` and replaces itself if that returns **200 + HTML**.

**Critical:** `/missing` must be served from **NAS disk**, not the Docker container. If `/missing` is proxied to Docker, it fails during redeploy and the TV stays on the gray 404 forever.

Install once on the NAS:

```bash
make install-nginx-placeholder NGINX_ROOT=/volume1/web/control-addmylegacy
```

That runs `deploy/build_missing_static.py` (inlines `tv-boot.js` into a self-contained page) and copies it to `$NGINX_ROOT/missing` and `$NGINX_ROOT/updating.html`.

Add a reverse-proxy or nginx rule **before** the Docker rule so `GET /missing` serves the static file. See `deploy/nginx.control.example.conf`.

## Content check (tv-boot.js)

The TV app validates **page content**, not HTTP status alone:

- Waits until HTML contains `control-addmylegacy` + `tv-dashboard`, `#tv-root`, and `#tv-slides-data`
- Ignores Synology gateway pages (gray 404 circle) even if they return HTTP 200
- Never full-page reloads on a timer — only reloads after content check passes
- While the dashboard is already visible, polls every 10s; if the service drops, shows **Still waiting** and retries until `/health/` and the dashboard HTML are valid again

## Verify

```bash
# Static hook — must return 200 even when Docker is stopped
curl -I https://control.addmylegacy.com/missing

curl -s https://control.addmylegacy.com/ | grep 'content="tv-dashboard"'
# must match when dashboard is up

curl -s https://control.addmylegacy.com/sw.js | head -1
# unregister stub (legacy service workers)
```
