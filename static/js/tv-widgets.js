/**
 * Async HUD widget refresh (Tizen M56 / ES5). Each widget polls its own endpoint.
 * Restricted widgets (wealth, Binance) show/hide when device allow status changes.
 */
(function () {
  "use strict";

  var wealthIntervalId = null;
  var binanceIntervalId = null;
  var deviceAccessIntervalId = null;
  var restrictedWidgetsActive = false;

  function readPollMs(attr) {
    var body = document.body;
    var seconds = body && body.getAttribute ? parseInt(body.getAttribute(attr), 10) : 0;

    if (!seconds || seconds < 1) {
      return 0;
    }

    return seconds * 1000;
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

  function fetchFragment(url, onSuccess, onFailure) {
    var xhr = createXhr();
    var requestUrl = String(url || "");

    if (!xhr || !requestUrl) {
      return;
    }

    requestUrl += (requestUrl.indexOf("?") === -1 ? "?" : "&") + "_=" + new Date().getTime();

    xhr.open("GET", requestUrl, true);
    xhr.timeout = 15000;

    try {
      xhr.setRequestHeader("Cache-Control", "no-cache");
      xhr.setRequestHeader("Pragma", "no-cache");
    } catch (headerError) {
      /* ignore */
    }

    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) {
        return;
      }

      if (xhr.status === 200) {
        if (onSuccess) {
          onSuccess(xhr.responseText || "");
        }
        return;
      }

      if (onFailure) {
        onFailure(xhr.status);
      }
    };

    try {
      xhr.send(null);
    } catch (error) {
      if (onFailure) {
        onFailure(0);
      }
    }
  }

  function fetchJson(url, onSuccess) {
    fetchFragment(
      url,
      function (body) {
        var data;

        try {
          data = JSON.parse(body || "");
        } catch (error) {
          return;
        }

        if (onSuccess) {
          onSuccess(data);
        }
      },
      function () {
        /* ignore */
      }
    );
  }

  function replaceContainerHtml(containerId, html) {
    var container = document.getElementById(containerId);

    if (!container || !html) {
      return;
    }

    container.innerHTML = html;
  }

  function scheduleWidgetPoll(containerId, url, intervalMs) {
    if (!intervalMs || !url || !containerId) {
      return null;
    }

    function refresh() {
      fetchFragment(url, function (html) {
        replaceContainerHtml(containerId, html);
      });
    }

    return window.setInterval(refresh, intervalMs);
  }

  function clearIntervalSafe(intervalId) {
    if (intervalId) {
      window.clearInterval(intervalId);
    }

    return null;
  }

  function setDeviceWidgetsAllowed(allowed) {
    var body = document.body;

    if (body && body.setAttribute) {
      body.setAttribute("data-device-widgets-allowed", allowed ? "true" : "false");
    }
  }

  function deviceWidgetsAllowed() {
    var body = document.body;

    if (!body || !body.getAttribute) {
      return false;
    }

    return body.getAttribute("data-device-widgets-allowed") === "true";
  }

  function setContainerHidden(containerId, hidden) {
    var container = document.getElementById(containerId);

    if (!container) {
      return;
    }

    if (hidden) {
      container.innerHTML = "";
      container.setAttribute("hidden", "hidden");
      return;
    }

    container.removeAttribute("hidden");
  }

  function hideRestrictedWidgets() {
    setContainerHidden("tv-widget-wealth", true);
    setContainerHidden("tv-widget-binance", true);
    wealthIntervalId = clearIntervalSafe(wealthIntervalId);
    binanceIntervalId = clearIntervalSafe(binanceIntervalId);
    restrictedWidgetsActive = false;
    setDeviceWidgetsAllowed(false);
  }

  function refreshRestrictedWidget(containerId, url) {
    fetchFragment(
      url,
      function (html) {
        replaceContainerHtml(containerId, html);
      },
      function (status) {
        if (status === 403) {
          hideRestrictedWidgets();
        }
      }
    );
  }

  function startRestrictedWidgetPolling(wealthPollMs, binancePollMs) {
    var body = document.body;
    var wealthUrl = body.getAttribute("data-wealth-widget-url");
    var binanceUrl = body.getAttribute("data-binance-widget-url");

    wealthIntervalId = clearIntervalSafe(wealthIntervalId);
    binanceIntervalId = clearIntervalSafe(binanceIntervalId);

    if (wealthPollMs && wealthUrl) {
      wealthIntervalId = window.setInterval(function () {
        refreshRestrictedWidget("tv-widget-wealth", wealthUrl);
      }, wealthPollMs);
    }

    if (binancePollMs && binanceUrl) {
      binanceIntervalId = window.setInterval(function () {
        refreshRestrictedWidget("tv-widget-binance", binanceUrl);
      }, binancePollMs);
    }
  }

  function enableRestrictedWidgets(wealthPollMs, binancePollMs, fetchNow) {
    var body = document.body;
    var wealthUrl = body.getAttribute("data-wealth-widget-url");
    var binanceUrl = body.getAttribute("data-binance-widget-url");

    setContainerHidden("tv-widget-wealth", false);
    setContainerHidden("tv-widget-binance", false);

    if (fetchNow) {
      refreshRestrictedWidget("tv-widget-wealth", wealthUrl);
      refreshRestrictedWidget("tv-widget-binance", binanceUrl);
    }

    startRestrictedWidgetPolling(wealthPollMs, binancePollMs);
    restrictedWidgetsActive = true;
    setDeviceWidgetsAllowed(true);
  }

  function pollSecondsToMs(seconds) {
    var value = parseInt(seconds, 10);

    if (!value || value < 1) {
      return 0;
    }

    return value * 1000;
  }

  function applyDeviceAccessFromConfig(data) {
    var allowed = !!(data && data.device_widgets_allowed);
    var wealthPollMs = pollSecondsToMs(data && data.wealth_poll_seconds);
    var binancePollMs = pollSecondsToMs(data && data.binance_poll_seconds);

    if (allowed && !restrictedWidgetsActive) {
      enableRestrictedWidgets(wealthPollMs, binancePollMs, true);
      return;
    }

    if (!allowed && restrictedWidgetsActive) {
      hideRestrictedWidgets();
    }
  }

  function pollDeviceAccessConfig() {
    var url = document.body.getAttribute("data-display-config-url");

    if (!url) {
      return;
    }

    fetchJson(url, applyDeviceAccessFromConfig);
  }

  function startDeviceAccessMonitor() {
    var pollMs = readPollMs("data-display-poll-seconds");

    if (!pollMs || deviceAccessIntervalId) {
      return;
    }

    deviceAccessIntervalId = window.setInterval(pollDeviceAccessConfig, pollMs);
  }

  function start() {
    scheduleWidgetPoll(
      "tv-widget-weather",
      document.body.getAttribute("data-weather-widget-url"),
      readPollMs("data-weather-poll-seconds")
    );
    scheduleWidgetPoll(
      "tv-widget-earthquake",
      document.body.getAttribute("data-earthquake-widget-url"),
      readPollMs("data-earthquake-poll-seconds")
    );

    if (deviceWidgetsAllowed()) {
      enableRestrictedWidgets(
        readPollMs("data-wealth-poll-seconds"),
        readPollMs("data-binance-poll-seconds"),
        false
      );
    } else {
      hideRestrictedWidgets();
    }

    startDeviceAccessMonitor();
  }

  if (document.readyState === "loading") {
    if (document.addEventListener) {
      document.addEventListener("DOMContentLoaded", start);
    } else {
      window.attachEvent("onload", start);
    }
  } else {
    start();
  }
})();
