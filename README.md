# Control AddMyLegacy

Single-page TV dashboard for **control.addmylegacy.com**, deployed the same way as the main [AddMyLegacy](https://addmylegacy.com) backend (Docker → private registry → Synology/nginx reverse proxy).

Optimized for **Samsung Q6F QLED 2018** (QN49Q6FAMFXZA) at 3840×2160 — large type, high contrast, Tizen-safe CSS/JS, auto-refresh.

## Quick start

Requires **Python 3.13** and **Django 5.1+**.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
cp .env.example .env
npm ci && npm run build:css
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000 — production: https://control.addmylegacy.com

## Project structure

```
config/           # Django settings, URLs
core/             # TV dashboard view + health check
templates/        # Single-page TV UI
static/           # Tailwind build + TV-specific CSS/JS
```

## Docker deploy (same as addmylegacy)

```bash
cp .env.example .env   # edit for production
make build-push-docker # builds, tags, pushes to 192.168.0.230:5005
```

| Makefile variable | Default |
|-------------------|---------|
| `service_name` | `control-addmylegacy-backend` |
| `registry` | `192.168.0.230:5005` |
| `port` | `8000` |

Run locally in Docker:

```bash
make build-docker
make run-docker
```

## Production checklist

1. Set `DEBUG=False`, strong `SECRET_KEY`, and PostgreSQL `DATABASE_URL`
2. Set `ALLOWED_HOSTS=control.addmylegacy.com`
3. Set `CSRF_TRUSTED_ORIGINS=https://control.addmylegacy.com`
4. Enable `TRUST_PROXY_HEADERS=True` and `USE_HTTPS=True` behind nginx
5. Point nginx subdomain `control.addmylegacy.com` at the container (see `deploy/nginx.control.example.conf`)
6. Install the offline placeholder: `make deploy-placeholder` (copy `deploy/updating.html` to nginx host)
7. Bump `STATIC_BUILD_ID` on each deploy to refresh TV browser cache
8. Set `TV_REFRESH_SECONDS` (default 60) for live dashboard reload; use `0` to disable. The page waits at least one full slideshow cycle before reloading, so long slide durations still advance.
9. Set `TV_HEALTH_POLL_SECONDS` (default 3) for deploy recovery polling

## Waiting during deploy

No Synology setup is required. Point the TV browser at `https://control.addmylegacy.com/` and leave it there.

On every load, `tv-boot.js`:

1. Shows **Still waiting** first
2. Checks `/health/` and verifies the page is the real dashboard (app marker, gallery slides, weather HUD)
3. Reveals the gallery only when everything is ready
4. If the service drops later, returns to **Still waiting** and retries automatically (polls bypass TV cache; reloads on new `STATIC_BUILD_ID` or after 3 min stuck)

Optional: set `TV_MAINTENANCE_MODE=true` in `.env` before a restart to redirect `/` → `/updating/` (same page, same waiting logic).

## Endpoints

| Path | Purpose |
|------|---------|
| `/` | Full-screen art slideshow + weather/time HUD |
| `/health/` | Plain-text health check for load balancers |
| `/admin/` | Toggle info panels, slideshow timing, art slides |

## Art gallery

26 city/nature photographs ship in `static/art/slides/` (1920×1080). The slideshow crossfades smoothly; duration and transition are configurable in **Admin → TV display configuration**.

**Admin → Art slides** controls which images are active and their order.

Weather for **Palo Alto** and **San Francisco** is fetched from [Open-Meteo](https://open-meteo.com/) (no API key) and cached for 10 minutes.

**Binance US** portfolio value and a 3-month trend chart appear above the earthquake widget when `BINANCE_US_API_KEY` and `BINANCE_US_API_SECRET` are set in `.env` (read-only API key recommended). Cached for 5 minutes by default.

Information panels (platform, environment, build) are **hidden by default**. Enable them in **Admin → TV display configuration → Show info panels**.

**Art images** must be committed in `static/art/slides/` — they are copied into the Docker image at build time. If the TV shows a black screen, verify images exist:

```bash
curl -I https://control.addmylegacy.com/static/art/slides/city-new-york.jpg
```

## TV display (Samsung Q6F 2018)

Target engine: **Tizen 4.0 / Chromium M56** (fixed at manufacture — not upgraded by firmware).

The page is built for that engine:

| Feature | Approach |
|---------|----------|
| Layout | Flexbox + margins (no CSS Grid, no `gap`) |
| CSS | Literal color fallbacks, `-webkit-` flex prefixes |
| JavaScript | ES5 only (`var`, `function`) — no modules or modern syntax |
| Clock | `Intl.DateTimeFormat` with manual date/time fallback |
| Refresh | `<meta http-equiv="refresh">` + JS `location.reload()` backup |
| Deploy | In-page waiting overlay via `tv-boot.js` until dashboard verified |
| Assets | `tv.css` + `tv-boot.js` + `tv-theme.js` + `tv-clock.js` + `tv-slideshow.js` — no Tailwind, no CDN scripts |
| Brightness | Always **dark mode** on the gallery HUD (`theme-night`) for readable widgets over photos. Actual panel brightness is Samsung **Eco Solution → Ambient Light Detection**, not the webpage |
| No-JS | Server-rendered date/time still visible via `<noscript>` |

Point the Samsung TV browser to `https://control.addmylegacy.com`. Typography scales at 1600px+ and 2560px+ breakpoints for 10-foot viewing.
