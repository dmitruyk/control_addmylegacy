# Synology 404 handling (optional)

The TV app now validates **page content**, not HTTP status alone:

- Waits until HTML contains `control-addmylegacy` + `tv-dashboard`, `#tv-root`, and `#tv-slides-data`
- Ignores Synology gateway pages (gray 404 circle) even if they return HTTP 200
- Never full-page reloads on a timer (removed meta refresh) — only reloads after content check passes

A **service worker** (`/sw.js`) is registered on the first successful dashboard visit. After that, gateway HTML navigations are replaced with the wait page automatically — **no Synology NAS install required**.

## Optional: `/missing` host file

Synology's built-in 404 page can fetch `GET /missing` and replace itself. This only helps on the **very first** visit before a service worker exists. Install is optional:

```bash
./deploy/install-updating-placeholder.sh /volume1/web/control-addmylegacy
```

See `deploy/nginx.control.example.conf` if you use custom nginx.

## Verify content check

```bash
curl -s https://control.addmylegacy.com/ | grep 'content="tv-dashboard"'
# must match when dashboard is up

curl -s https://control.addmylegacy.com/sw.js | head -1
# must return JavaScript
```
