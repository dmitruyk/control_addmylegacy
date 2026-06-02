/**
 * Async HUD widget refresh (Tizen M56 / ES5). Each widget polls its own endpoint.
 */
(function () {
  "use strict";

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

  function fetchFragment(url, onSuccess) {
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
      if (xhr.readyState !== 4 || xhr.status !== 200) {
        return;
      }

      if (onSuccess) {
        onSuccess(xhr.responseText || "");
      }
    };

    try {
      xhr.send(null);
    } catch (error) {
      /* ignore */
    }
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
      return;
    }

    function refresh() {
      fetchFragment(url, function (html) {
        replaceContainerHtml(containerId, html);
      });
    }

    window.setInterval(refresh, intervalMs);
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
    scheduleWidgetPoll(
      "tv-widget-wealth",
      document.body.getAttribute("data-wealth-widget-url"),
      readPollMs("data-wealth-poll-seconds")
    );
    scheduleWidgetPoll(
      "tv-widget-binance",
      document.body.getAttribute("data-binance-widget-url"),
      readPollMs("data-binance-poll-seconds")
    );
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
