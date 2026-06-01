(function () {
  "use strict";

  var pollMs = 3000;
  var monitorMs = 10000;
  var stuckOverlayMs = 180000;
  var updatingEl = null;
  var rootEl = null;
  var monitoring = false;
  var retryTimer = null;
  var gatewayDetected = false;
  var serviceConfig = null;
  var overlayShownAt = 0;

  var LOCAL_HOSTS = {
    localhost: true,
    "127.0.0.1": true,
    "0.0.0.0": true,
    "::1": true,
  };

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

  function readMeta(name) {
    var meta = document.querySelector('meta[name="' + name + '"]');

    return meta && meta.getAttribute ? (meta.getAttribute("content") || "").trim() : "";
  }

  function readBodyData(name) {
    var body = document.body;

    if (!body || !body.getAttribute) {
      return "";
    }

    return (body.getAttribute(name) || "").trim();
  }

  function normalizeBase(url) {
    return String(url || "").replace(/\/+$/, "");
  }

  function joinUrl(base, path) {
    var normalizedBase = normalizeBase(base);
    var normalizedPath = path || "/";

    if (normalizedPath.charAt(0) !== "/") {
      normalizedPath = "/" + normalizedPath;
    }

    return normalizedBase + normalizedPath;
  }

  function cacheBustUrl(url) {
    var separator = String(url || "").indexOf("?") === -1 ? "?" : "&";

    return String(url || "") + separator + "_=" + new Date().getTime();
  }

  function getCurrentBuildId() {
    var meta = document.querySelector('meta[name="aml-static-build"]');

    return meta && meta.getAttribute ? (meta.getAttribute("content") || "") : "";
  }

  function extractBuildId(html) {
    var match = String(html || "").match(/name="aml-static-build"\s+content="([^"]+)"/);

    return match ? match[1] : "";
  }

  function shouldReloadForHtml(html) {
    var remoteBuild = extractBuildId(html);
    var localBuild = getCurrentBuildId();

    return !!(remoteBuild && localBuild && remoteBuild !== localBuild);
  }

  function isOverlayVisible() {
    return !!(
      updatingEl &&
      updatingEl.className &&
      updatingEl.className.indexOf("tv-updating-visible") !== -1
    );
  }

  function markOverlayShown() {
    if (!overlayShownAt) {
      overlayShownAt = new Date().getTime();
    }
  }

  function clearOverlayShown() {
    overlayShownAt = 0;
  }

  function isLocalHost(hostname) {
    return !!LOCAL_HOSTS[String(hostname || "").toLowerCase()];
  }

  function resolveServiceConfig() {
    var hostname = window.location.hostname || "";
    var currentOrigin = normalizeBase(window.location.origin || "");
    var configuredBase = readMeta("aml-service-url") || readBodyData("data-service-base");
    var configuredMode = readMeta("aml-service-mode") || readBodyData("data-service-mode");
    var base;
    var mode;

    if (configuredMode === "local" || isLocalHost(hostname)) {
      base = currentOrigin;
      mode = "local";
    } else if (configuredBase) {
      base = normalizeBase(configuredBase);
      mode = "production";
    } else {
      base = currentOrigin;
      mode = isLocalHost(hostname) ? "local" : "production";
    }

    return {
      base: base,
      mode: mode,
      healthUrl: joinUrl(base, "/health/"),
      dashboardUrl: joinUrl(base, "/"),
      dashboardPath: "/",
    };
  }

  function getServiceConfig() {
    if (!serviceConfig) {
      serviceConfig = resolveServiceConfig();
    }

    return serviceConfig;
  }

  function serviceStatusLabel(prefix) {
    var config = getServiceConfig();
    var label = prefix || "Checking";

    if (config.mode === "local") {
      return label + " local service at " + config.base + "…";
    }

    return label + " " + config.base.replace(/^https?:\/\//, "") + "…";
  }

  function openDashboard() {
    var config = getServiceConfig();
    var currentOrigin = normalizeBase(window.location.origin || "");
    var target = config.dashboardPath;

    if (config.base !== currentOrigin) {
      target = config.dashboardUrl;
    }

    window.location.replace(cacheBustUrl(target));
  }

  function getAppMarker() {
    return readMeta("control-addmylegacy");
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
    var value = parseInt(readBodyData("data-health-poll-seconds"), 10);

    if (!value || value < 1) {
      return pollMs;
    }

    return value * 1000;
  }

  function getRefreshInterval() {
    var value = parseInt(readBodyData("data-refresh-seconds"), 10);

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
      markOverlayShown();

      if (rootEl) {
        rootEl.className = "tv-gallery tv-content-hidden";
      }
    } else {
      updatingEl.className = "tv-updating";
      updatingEl.setAttribute("aria-hidden", "true");
      clearOverlayShown();

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

  function fetchUrl(url, onSuccess, onFailure) {
    var xhr = createXhr();

    if (!xhr) {
      onFailure("", 0);
      return;
    }

    xhr.open("GET", cacheBustUrl(url), true);
    xhr.timeout = 8000;

    try {
      xhr.setRequestHeader("Cache-Control", "no-cache");
      xhr.setRequestHeader("Pragma", "no-cache");
    } catch (headerError) {
      /* ignore — not all engines allow these on GET */
    }

    xhr.onreadystatechange = function () {
      var body;

      if (xhr.readyState !== 4) {
        return;
      }

      body = xhr.responseText || "";

      if (xhr.status === 200) {
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

  function fetchHealth(onSuccess, onFailure) {
    var config = getServiceConfig();

    fetchUrl(
      config.healthUrl,
      function (body) {
        if (body.indexOf("ok") !== -1) {
          onSuccess(body);
          return;
        }

        if (isGatewayErrorHtml(body)) {
          applyGatewayWaitingUi();
        }

        onFailure(body, 200);
      },
      onFailure
    );
  }

  function fetchDashboardPage(onSuccess, onFailure) {
    var config = getServiceConfig();

    fetchUrl(
      config.dashboardUrl,
      function (body) {
        if (isValidDashboardHtml(body)) {
          onSuccess(body);
          return;
        }

        if (isGatewayErrorHtml(body)) {
          applyGatewayWaitingUi();
        }

        onFailure(body, 200);
      },
      onFailure
    );
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

  function reloadDashboard() {
    setUpdatingStatus("Loading updated dashboard…");
    openDashboard();
  }

  function handleRecoveredDashboardHtml(html) {
    if (shouldReloadForHtml(html)) {
      reloadDashboard();
      return true;
    }

    if (!isDashboardReady()) {
      reloadDashboard();
      return true;
    }

    if (isOverlayVisible()) {
      gatewayDetected = false;
      revealDashboard();
    }

    return false;
  }

  function recoverFromStuckOverlay() {
    if (!isOverlayVisible() || !overlayShownAt) {
      return;
    }

    if (new Date().getTime() - overlayShownAt < stuckOverlayMs) {
      return;
    }

    setUpdatingStatus("Still waiting — forcing refresh…");

    fetchHealth(
      function () {
        fetchDashboardPage(
          function (html) {
            if (isValidDashboardHtml(html)) {
              reloadDashboard();
              return;
            }

            scheduleRetry(attemptShowDashboard);
          },
          function () {
            scheduleRetry(attemptShowDashboard);
          }
        );
      },
      function () {
        scheduleRetry(attemptShowDashboard);
      }
    );
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
      setUpdatingStatus(serviceStatusLabel("Still waiting — verifying"));
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
    recoverFromStuckOverlay();

    if (isDashboardDocument() && isDashboardReady()) {
      setUpdatingStatus("Dashboard page ready.");
      revealDashboard();
      return;
    }

    if (isDashboardDocument()) {
      setUpdatingStatus("Still waiting — preparing gallery…");

      fetchHealth(
        function () {
          fetchDashboardPage(
            function (html) {
              if (handleRecoveredDashboardHtml(html)) {
                return;
              }

              revealDashboard();
            },
            function () {
              scheduleRetry(attemptShowDashboard);
            }
          );
        },
        function () {
          scheduleRetry(attemptShowDashboard);
        }
      );
      return;
    }

    setUpdatingStatus(serviceStatusLabel("Checking"));

    fetchHealth(
      function () {
        fetchDashboardPage(
          function () {
            setUpdatingStatus("Dashboard page verified. Loading…");
            reloadDashboard();
          },
          function () {
            setUpdatingStatus(serviceStatusLabel("Still waiting — verifying"));
            scheduleRetry(attemptShowDashboard);
          }
        );
      },
      function () {
        if (gatewayDetected || isGatewayErrorDocument()) {
          applyGatewayWaitingUi();
          setUpdatingStatus(serviceStatusLabel("Gateway detected — waiting for"));
        } else {
          setUpdatingStatus(serviceStatusLabel("Still waiting for"));
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
      recoverFromStuckOverlay();

      if (!isDashboardDocument()) {
        setUpdatingVisible(true);
        applyGatewayWaitingUi();
        scheduleRetry(attemptShowDashboard);
        return;
      }

      fetchDashboardPage(
        function (html) {
          handleRecoveredDashboardHtml(html);
        },
        function () {
          if (isDashboardDocument() && isDashboardReady()) {
            if (isOverlayVisible()) {
              fetchHealth(
                function () {
                  gatewayDetected = false;
                  revealDashboard();
                },
                function () {
                  setUpdatingVisible(true);
                  setUpdatingStatus(serviceStatusLabel("Still waiting for"));
                  scheduleRetry(attemptShowDashboard);
                }
              );
            }
            return;
          }

          setUpdatingVisible(true);
          applyGatewayWaitingUi();
          setUpdatingStatus(serviceStatusLabel("Gateway detected — waiting for"));
          scheduleRetry(attemptShowDashboard);
        }
      );
    }, monitorMs);
  }

  function startSoftRefresh() {
    var refreshMs = getRefreshInterval();

    if (!refreshMs || !isDashboardDocument()) {
      return;
    }

    window.setInterval(function () {
      fetchDashboardPage(
        function (html) {
          if (shouldReloadForHtml(html)) {
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
    serviceConfig = resolveServiceConfig();

    clearBrokenServiceWorkers();

    if (isGatewayErrorDocument()) {
      injectWaitingShell();
      setUpdatingStatus(serviceStatusLabel("Gateway detected — waiting for"));
      attemptShowDashboard();
      return;
    }

    if (isWaitDocument()) {
      attemptShowDashboard();
      return;
    }

    if (!isDashboardDocument()) {
      injectWaitingShell();
      setUpdatingStatus(serviceStatusLabel("Still waiting — verifying"));
      attemptShowDashboard();
      return;
    }

    if (!updatingEl) {
      injectWaitingShell();
    }

    setUpdatingVisible(true);
    setUpdatingStatus(serviceStatusLabel("Checking"));
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
