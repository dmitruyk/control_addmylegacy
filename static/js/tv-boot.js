(function () {
  "use strict";

  var HEALTH_PATH = "/health/";
  var WAIT_PATH = "/wait/";
  var DASHBOARD_PATH = "/";
  var pollMs = 3000;
  var monitorMs = 10000;
  var updatingEl = null;
  var rootEl = null;
  var monitoring = false;
  var retryTimer = null;
  var synologyDetected = false;

  var SYNOLOGY_MARKERS = [
    "synology",
    "diskstation",
    "dsm ",
    "webstation",
    "bad gateway",
    "service unavailable",
    "404",
    "not found",
    "page not found",
    "page cannot be found",
    "can't find this page",
    "cannot be found"
  ];

  function getAppMarker() {
    var meta = document.querySelector('meta[name="control-addmylegacy"]');

    return meta && meta.getAttribute ? meta.getAttribute("content") || "" : "";
  }

  function isDashboardDocument() {
    return getAppMarker() === "tv-dashboard";
  }

  function isWaitDocument() {
    var marker = getAppMarker();

    return marker === "wait-page" || marker === "updating-page";
  }

  function isSynologyHtml(html) {
    var text = String(html || "").toLowerCase();
    var index;

    if (!text || text.indexOf("control-addmylegacy") !== -1) {
      return false;
    }

    for (index = 0; index < SYNOLOGY_MARKERS.length; index += 1) {
      if (text.indexOf(SYNOLOGY_MARKERS[index]) !== -1) {
        return true;
      }
    }

    return false;
  }

  function isSynologyDocument() {
    var html = (document.documentElement && document.documentElement.innerHTML) || "";
    var title = document.title || "";

    return isSynologyHtml(html + " " + title);
  }

  function getPollInterval() {
    var body = document.body;
    var value;

    if (!body || !body.getAttribute) {
      return pollMs;
    }

    value = parseInt(body.getAttribute("data-health-poll-seconds"), 10);
    if (!value || value < 1) {
      return pollMs;
    }

    return value * 1000;
  }

  function createXhr() {
    if (window.XMLHttpRequest) {
      return new XMLHttpRequest();
    }

    try {
      return new ActiveXObject("Microsoft.XMLHTTP");
    } catch (error) {
      return null;
    }
  }

  function isDashboardReady() {
    var slidesEl = document.getElementById("tv-slides-data");
    var hud = document.querySelector(".tv-hud");
    var slides = [];

    if (!isDashboardDocument() || !rootEl || !slidesEl || !hud) {
      return false;
    }

    try {
      slides = JSON.parse(slidesEl.textContent || "[]");
    } catch (error) {
      return false;
    }

    return slides.length > 0;
  }

  function getUpdatingMetaEl() {
    return updatingEl ? updatingEl.getElementsByClassName("tv-updating-meta")[0] : null;
  }

  function applySynologyWaitingUi() {
    var badgeEl;
    var titleEl;
    var messageEl;

    synologyDetected = true;

    if (!updatingEl) {
      return;
    }

    updatingEl.className = "tv-updating tv-updating-visible tv-updating-synology";
    updatingEl.setAttribute("aria-hidden", "false");

    badgeEl = document.getElementById("tv-updating-badge");
    titleEl = document.getElementById("tv-updating-title");
    messageEl = document.getElementById("tv-updating-message");

    if (badgeEl) {
      badgeEl.removeAttribute("hidden");
    }

    if (titleEl) {
      titleEl.textContent = "Synology gateway — still waiting";
    }

    if (messageEl) {
      messageEl.textContent =
        "The Synology gateway responded, but the control dashboard is not ready yet. This page will load automatically when the service is available.";
    }

    document.title = "Synology — waiting for dashboard";
  }

  function injectWaitingShell() {
    var styleEl;
    var badgeEl;
    var titleEl;
    var messageEl;

    if (document.getElementById("tv-updating")) {
      updatingEl = document.getElementById("tv-updating");
      setUpdatingVisible(true);
      applySynologyWaitingUi();
      return;
    }

    updatingEl = document.createElement("div");
    updatingEl.id = "tv-updating";
    updatingEl.className = "tv-updating tv-updating-visible tv-updating-synology";
    updatingEl.setAttribute("aria-live", "polite");
    updatingEl.setAttribute("aria-busy", "true");
    updatingEl.innerHTML =
      '<p class="tv-updating-badge" id="tv-updating-badge">Synology gateway</p>' +
      '<div class="tv-updating-mark" aria-hidden="true">AML</div>' +
      '<div class="tv-updating-spinner" aria-hidden="true"></div>' +
      '<h1 class="tv-updating-title" id="tv-updating-title">Synology gateway — still waiting</h1>' +
      '<p class="tv-updating-message" id="tv-updating-message">The control dashboard is not available yet. This page will load automatically when the service is ready.</p>' +
      '<p class="tv-updating-meta" id="tv-updating-meta">Checking control dashboard…</p>';

    styleEl = document.createElement("style");
    styleEl.textContent =
      "html,body{margin:0;height:100%;overflow:hidden;background:#0b0f14;color:#f4f7fb;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;}" +
      ".tv-updating{align-items:center;box-sizing:border-box;display:flex;flex-direction:column;height:100%;justify-content:center;padding:48px;position:fixed;left:0;top:0;width:100%;z-index:2147483647;text-align:center;}" +
      ".tv-updating-mark{align-items:center;background:linear-gradient(135deg,#2dd4bf,#2563eb);border-radius:20px;color:#041018;display:flex;font-size:40px;font-weight:800;height:112px;justify-content:center;letter-spacing:.08em;margin-bottom:40px;width:112px;}" +
      ".tv-updating-title{color:#fbbf24;font-size:56px;font-weight:700;line-height:1.15;margin:0 0 20px;}" +
      ".tv-updating-message{color:#4fd1c5;font-size:32px;line-height:1.4;margin:0 0 16px;max-width:960px;}" +
      ".tv-updating-meta{color:#9aa8bc;font-size:22px;margin:0;}" +
      ".tv-updating-badge{background:rgba(251,191,36,.16);border:1px solid rgba(251,191,36,.45);border-radius:999px;color:#fbbf24;display:block;font-size:16px;font-weight:700;letter-spacing:.14em;margin:0 0 24px;padding:10px 18px;text-transform:uppercase;}" +
      ".tv-updating-spinner{border:4px solid #243041;border-radius:50%;border-top-color:#4fd1c5;height:56px;margin-bottom:36px;width:56px;animation:tv-spin 1s linear infinite;}" +
      "@keyframes tv-spin{to{transform:rotate(360deg);}}";

    document.head.appendChild(styleEl);
    document.body.appendChild(updatingEl);
    synologyDetected = true;
    document.title = "Synology — waiting for dashboard";

    badgeEl = document.getElementById("tv-updating-badge");
    titleEl = document.getElementById("tv-updating-title");
    messageEl = document.getElementById("tv-updating-message");

    if (badgeEl) {
      badgeEl.removeAttribute("hidden");
    }

    if (titleEl) {
      titleEl.textContent = "Synology gateway — still waiting";
    }

    if (messageEl) {
      messageEl.textContent =
        "The Synology gateway responded, but the control dashboard is not ready yet. This page will load automatically when the service is available.";
    }
  }

  function setUpdatingVisible(visible) {
    if (!updatingEl) {
      return;
    }

    if (visible) {
      updatingEl.className = synologyDetected
        ? "tv-updating tv-updating-visible tv-updating-synology"
        : "tv-updating tv-updating-visible";
      updatingEl.setAttribute("aria-hidden", "false");

      if (rootEl) {
        rootEl.className = "tv-gallery tv-content-hidden";
      }
    } else {
      updatingEl.className = "tv-updating";
      updatingEl.setAttribute("aria-hidden", "true");

      if (rootEl) {
        rootEl.className = "tv-gallery";
      }
    }
  }

  function setUpdatingStatus(message) {
    var metaEl = getUpdatingMetaEl();

    if (metaEl) {
      metaEl.textContent = message;
    }
  }

  function checkHealth(onSuccess, onFailure) {
    var xhr = createXhr();

    if (!xhr) {
      onFailure("", 0);
      return;
    }

    xhr.open("GET", HEALTH_PATH, true);
    xhr.timeout = 4000;

    xhr.onreadystatechange = function () {
      var body;

      if (xhr.readyState !== 4) {
        return;
      }

      body = xhr.responseText || "";

      if (xhr.status === 200 && body.indexOf("ok") !== -1) {
        onSuccess();
        return;
      }

      if (isSynologyHtml(body)) {
        applySynologyWaitingUi();
      }

      onFailure(body, xhr.status);
    };

    xhr.onerror = function () {
      if (isSynologyDocument()) {
        applySynologyWaitingUi();
      }
      onFailure("", 0);
    };

    xhr.ontimeout = function () {
      onFailure("", 0);
    };

    try {
      xhr.send(null);
    } catch (error) {
      onFailure("", 0);
    }
  }

  function clearRetryTimer() {
    if (retryTimer) {
      window.clearTimeout(retryTimer);
      retryTimer = null;
    }
  }

  function scheduleRetry(callback) {
    clearRetryTimer();
    pollMs = getPollInterval();
    retryTimer = window.setTimeout(callback, pollMs);
  }

  function openDashboardWhenReady() {
    if (isWaitDocument() || !isDashboardDocument()) {
      window.location.replace(DASHBOARD_PATH);
      return;
    }

    window.location.reload();
  }

  function redirectToWaitingRoute() {
    var path = window.location.pathname || "/";

    if (path.indexOf(WAIT_PATH) === 0 || path.indexOf("/updating") === 0) {
      injectWaitingShell();
      attemptShowDashboard();
      return;
    }

    window.location.replace(WAIT_PATH);
  }

  function activateDashboardIfReady() {
    if (isWaitDocument()) {
      setUpdatingVisible(true);
      setUpdatingStatus("Still waiting for control dashboard…");
      scheduleRetry(function () {
        attemptShowDashboard();
      });
      return;
    }

    if (!isDashboardDocument()) {
      if (isSynologyDocument()) {
        injectWaitingShell();
        setUpdatingStatus("Synology gateway — waiting for control dashboard…");
      } else {
        setUpdatingStatus("Still waiting — loading control dashboard…");
      }

      scheduleRetry(redirectToWaitingRoute);
      return;
    }

    if (!isDashboardReady()) {
      setUpdatingVisible(true);
      setUpdatingStatus("Still waiting — preparing gallery…");
      scheduleRetry(function () {
        attemptShowDashboard();
      });
      return;
    }

    clearRetryTimer();
    setUpdatingVisible(false);

    if (document.body && document.body.setAttribute) {
      document.body.setAttribute("data-dashboard-ready", "true");
    }

    if (document.createEvent && document.body && document.body.dispatchEvent) {
      var readyEvent = document.createEvent("Event");
      readyEvent.initEvent("tv-dashboard-ready", true, true);
      document.body.dispatchEvent(readyEvent);
    }

    startMonitor();
  }

  function attemptShowDashboard() {
    setUpdatingVisible(true);
    setUpdatingStatus("Checking control dashboard…");

    checkHealth(
      function () {
        if (isWaitDocument() || !isDashboardDocument()) {
          setUpdatingStatus("Service is ready. Loading dashboard…");
          openDashboardWhenReady();
          return;
        }

        activateDashboardIfReady();
      },
      function () {
        if (synologyDetected || isSynologyDocument()) {
          applySynologyWaitingUi();
          setUpdatingStatus("Synology gateway — container still starting…");
        } else {
          setUpdatingStatus("Still waiting for control dashboard…");
        }

        scheduleRetry(function () {
          attemptShowDashboard();
        });
      }
    );
  }

  function startMonitor() {
    if (monitoring) {
      return;
    }

    monitoring = true;
    monitorMs = Math.max(getPollInterval() * 2, 10000);

    window.setInterval(function () {
      checkHealth(
        function () {
          if (isDashboardDocument() && !isDashboardReady()) {
            setUpdatingVisible(true);
            setUpdatingStatus("Still waiting — restoring gallery…");
            scheduleRetry(function () {
              attemptShowDashboard();
            });
          }
        },
        function () {
          setUpdatingVisible(true);

          if (synologyDetected || isSynologyDocument()) {
            applySynologyWaitingUi();
            setUpdatingStatus("Synology gateway — waiting for control dashboard…");
          } else {
            setUpdatingStatus("Still waiting for control dashboard…");
          }

          scheduleRetry(function () {
            attemptShowDashboard();
          });
        }
      );
    }, monitorMs);
  }

  function boot() {
    updatingEl = document.getElementById("tv-updating");
    rootEl = document.getElementById("tv-root");

    if (isSynologyDocument() && !isDashboardDocument() && !isWaitDocument()) {
      injectWaitingShell();
      setUpdatingStatus("Synology gateway — waiting for control dashboard…");
      attemptShowDashboard();
      return;
    }

    if (isWaitDocument()) {
      attemptShowDashboard();
      return;
    }

    if (!isDashboardDocument()) {
      redirectToWaitingRoute();
      return;
    }

    if (!updatingEl) {
      injectWaitingShell();
    }

    if (!rootEl) {
      setUpdatingVisible(true);
      setUpdatingStatus("Still waiting — preparing gallery…");
      attemptShowDashboard();
      return;
    }

    setUpdatingVisible(true);
    setUpdatingStatus("Checking control dashboard…");
    attemptShowDashboard();
  }

  if (document.readyState === "loading") {
    if (document.addEventListener) {
      document.addEventListener("DOMContentLoaded", boot);
    } else {
      window.attachEvent("onload", boot);
    }
  } else {
    boot();
  }
})();
