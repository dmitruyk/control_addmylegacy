(function () {
  "use strict";

  var HEALTH_PATH = "/health/";
  var DASHBOARD_PATH = "/";
  var pollMs = 3000;
  var monitorMs = 10000;
  var updatingEl = null;
  var rootEl = null;
  var monitoring = false;
  var retryTimer = null;
  var gatewayDetected = false;

  var DASHBOARD_MARKERS = [
    'name="control-addmylegacy" content="tv-dashboard"',
    'id="tv-root"',
    'id="tv-slides-data"',
  ];

  var GATEWAY_MARKERS = [
    "synology inc",
    "circle_text",
    "the page you are looking for cannot be found",
  ];

  function getAppMarker() {
    var meta = document.querySelector('meta[name="control-addmylegacy"]');

    return meta && meta.getAttribute ? meta.getAttribute("content") || "" : "";
  }

  function htmlContainsMarkers(html, markers) {
    var text = String(html || "").toLowerCase();
    var index;

    for (index = 0; index < markers.length; index += 1) {
      if (text.indexOf(String(markers[index]).toLowerCase()) === -1) {
        return false;
      }
    }

    return true;
  }

  function isValidDashboardHtml(html) {
    return htmlContainsMarkers(html, DASHBOARD_MARKERS);
  }

  function isGatewayErrorHtml(html) {
    var text = String(html || "").toLowerCase();

    if (!text || text.indexOf("control-addmylegacy") !== -1) {
      return false;
    }

    return htmlContainsMarkers(html, GATEWAY_MARKERS) || text.indexOf(">404<") !== -1;
  }

  function isDashboardDocument() {
    if (getAppMarker() !== "tv-dashboard") {
      return false;
    }

    return !!(
      document.getElementById("tv-root") &&
      document.getElementById("tv-slides-data") &&
      document.querySelector(".tv-hud")
    );
  }

  function isWaitDocument() {
    var marker = getAppMarker();

    return marker === "wait-page" || marker === "updating-page";
  }

  function isGatewayErrorDocument() {
    if (isDashboardDocument() || isWaitDocument()) {
      return false;
    }

    var html = (document.documentElement && document.documentElement.innerHTML) || "";
    var title = document.title || "";

    return isGatewayErrorHtml(html + " " + title);
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

  function getRefreshInterval() {
    var body = document.body;
    var value;

    if (!body || !body.getAttribute) {
      return 0;
    }

    value = parseInt(body.getAttribute("data-refresh-seconds"), 10);
    if (!value || value < 1) {
      return 0;
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

  function parseSlidesPayload(raw) {
    var data;

    if (!raw) {
      return [];
    }

    try {
      data = JSON.parse(raw);
    } catch (error) {
      return [];
    }

    if (typeof data === "string") {
      try {
        data = JSON.parse(data);
      } catch (innerError) {
        return [];
      }
    }

    return data && data.length !== undefined ? data : [];
  }

  function isDashboardReady() {
    var slidesEl = document.getElementById("tv-slides-data");
    var slides = [];

    if (!isDashboardDocument() || !rootEl || !slidesEl) {
      return false;
    }

    slides = parseSlidesPayload(slidesEl.textContent || "[]");

    return slides.length > 0 && slides[0] && slides[0].url;
  }

  function getUpdatingMetaEl() {
    return updatingEl ? updatingEl.getElementsByClassName("tv-updating-meta")[0] : null;
  }

  function applyGatewayWaitingUi() {
    var badgeEl;
    var titleEl;
    var messageEl;

    gatewayDetected = true;

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
      titleEl.textContent = "Gateway page detected — still waiting";
    }

    if (messageEl) {
      messageEl.textContent =
        "The response was not the control dashboard yet. Waiting until the real dashboard page is available.";
    }

    document.title = "Still waiting for dashboard";
  }

  function injectWaitingShell() {
    if (document.getElementById("tv-updating")) {
      updatingEl = document.getElementById("tv-updating");
      setUpdatingVisible(true);
      applyGatewayWaitingUi();
      return;
    }

    updatingEl = document.createElement("div");
    updatingEl.id = "tv-updating";
    updatingEl.className = "tv-updating tv-updating-visible tv-updating-synology";
    updatingEl.setAttribute("aria-live", "polite");
    updatingEl.setAttribute("aria-busy", "true");
    updatingEl.innerHTML =
      '<p class="tv-updating-badge" id="tv-updating-badge">Gateway</p>' +
      '<div class="tv-updating-mark" aria-hidden="true">AML</div>' +
      '<div class="tv-updating-spinner" aria-hidden="true"></div>' +
      '<h1 class="tv-updating-title" id="tv-updating-title">Still waiting</h1>' +
      '<p class="tv-updating-message" id="tv-updating-message">The control dashboard will appear automatically when the real service page is available.</p>' +
      '<p class="tv-updating-meta" id="tv-updating-meta">Checking dashboard page content…</p>';
    document.body.appendChild(updatingEl);
    gatewayDetected = true;
    document.title = "Still waiting for dashboard";
  }

  function setUpdatingVisible(visible) {
    if (!updatingEl) {
      return;
    }

    if (visible) {
      updatingEl.className = gatewayDetected
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

  function fetchDashboardPage(onSuccess, onFailure) {
    var xhr = createXhr();

    if (!xhr) {
      onFailure("", 0);
      return;
    }

    xhr.open("GET", DASHBOARD_PATH, true);
    xhr.timeout = 8000;

    xhr.onreadystatechange = function () {
      var body;

      if (xhr.readyState !== 4) {
        return;
      }

      body = xhr.responseText || "";

      if (isValidDashboardHtml(body)) {
        onSuccess(body, xhr.status);
        return;
      }

      if (isGatewayErrorHtml(body)) {
        applyGatewayWaitingUi();
      }

      onFailure(body, xhr.status);
    };

    xhr.onerror = function () {
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

  function clearBrokenServiceWorkers() {
    if (!("serviceWorker" in navigator) || !navigator.serviceWorker.register) {
      return;
    }

    try {
      navigator.serviceWorker.register("/sw.js").catch(function () {});

      if (!navigator.serviceWorker.getRegistrations) {
        return;
      }

      window.setTimeout(function () {
        navigator.serviceWorker.getRegistrations().then(function (registrations) {
          var index;

          for (index = 0; index < registrations.length; index += 1) {
            if (registrations[index].active && registrations[index].active.scriptURL.indexOf("tv-sw.js") !== -1) {
              registrations[index].unregister();
            }
          }
        });
      }, 2000);
    } catch (error) {
      /* ignore */
    }
  }

  function revealDashboard() {
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
    startSoftRefresh();
  }

  function activateDashboardIfReady() {
    if (!isDashboardDocument()) {
      injectWaitingShell();
      setUpdatingStatus("Still waiting — verifying dashboard page content…");
      scheduleRetry(attemptShowDashboard);
      return;
    }

    if (!isDashboardReady()) {
      setUpdatingVisible(true);
      setUpdatingStatus("Still waiting — preparing gallery…");
      scheduleRetry(attemptShowDashboard);
      return;
    }

    revealDashboard();
  }

  function attemptShowDashboard() {
    setUpdatingVisible(true);

    if (isDashboardDocument() && isDashboardReady()) {
      setUpdatingStatus("Dashboard page ready.");
      revealDashboard();
      return;
    }

    if (isDashboardDocument()) {
      setUpdatingStatus("Still waiting — preparing gallery…");
      scheduleRetry(attemptShowDashboard);
      return;
    }

    setUpdatingStatus("Checking dashboard page content…");

    fetchDashboardPage(
      function () {
        setUpdatingStatus("Dashboard page verified. Loading…");
        window.location.replace(DASHBOARD_PATH);
      },
      function () {
        if (gatewayDetected || isGatewayErrorDocument()) {
          applyGatewayWaitingUi();
          setUpdatingStatus("Gateway page detected — waiting for real dashboard…");
        } else {
          setUpdatingStatus("Still waiting for control dashboard…");
        }

        scheduleRetry(attemptShowDashboard);
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
      if (!isDashboardDocument()) {
        setUpdatingVisible(true);
        applyGatewayWaitingUi();
        scheduleRetry(attemptShowDashboard);
        return;
      }

      fetchDashboardPage(
        function () {
          if (!isDashboardReady()) {
            setUpdatingVisible(true);
            setUpdatingStatus("Still waiting — restoring gallery…");
            scheduleRetry(attemptShowDashboard);
          }
        },
        function () {
          if (isDashboardDocument() && isDashboardReady()) {
            return;
          }

          setUpdatingVisible(true);
          applyGatewayWaitingUi();
          setUpdatingStatus("Gateway page detected — waiting for real dashboard…");
          scheduleRetry(attemptShowDashboard);
        }
      );
    }, monitorMs);
  }

  function startSoftRefresh() {
    var refreshMs = getRefreshInterval();
    var currentBuildMeta;
    var currentBuildId;

    if (!refreshMs || !isDashboardDocument()) {
      return;
    }

    currentBuildMeta = document.querySelector('meta[name="aml-static-build"]');
    currentBuildId = currentBuildMeta ? currentBuildMeta.getAttribute("content") : "";

    window.setInterval(function () {
      fetchDashboardPage(
        function (html) {
          var match = String(html).match(/name="aml-static-build"\s+content="([^"]+)"/);

          if (match && currentBuildId && match[1] !== currentBuildId) {
            window.location.reload();
          }
        },
        function () {
          /* Keep showing the current dashboard if the poll fails. */
        }
      );
    }, refreshMs);
  }

  function boot() {
    updatingEl = document.getElementById("tv-updating");
    rootEl = document.getElementById("tv-root");

    clearBrokenServiceWorkers();

    if (isGatewayErrorDocument()) {
      injectWaitingShell();
      setUpdatingStatus("Gateway page detected — waiting for real dashboard…");
      attemptShowDashboard();
      return;
    }

    if (isWaitDocument()) {
      attemptShowDashboard();
      return;
    }

    if (!isDashboardDocument()) {
      injectWaitingShell();
      setUpdatingStatus("Still waiting — verifying dashboard page content…");
      attemptShowDashboard();
      return;
    }

    if (!updatingEl) {
      injectWaitingShell();
    }

    setUpdatingVisible(true);
    setUpdatingStatus("Checking dashboard page…");
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
