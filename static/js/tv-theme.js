/**
 * Time-based display brightness for Samsung Tizen TV browser (ES5 / M56).
 *
 * The TV ambient light sensor is not exposed to JavaScript on Tizen. Actual
 * panel brightness is controlled by Samsung TV Settings → General → Eco
 * Solution (Ambient Light Detection / Energy Saving), not by this script.
 * This module only adjusts on-screen colors for day/evening comfort.
 *
 * Always Auto — day/night follows San Francisco local time (America/Los_Angeles).
 */
(function () {
  "use strict";

  var DEFAULT_TIME_ZONE = "America/Los_Angeles";
  var DEFAULT_DAY_START = 7;
  var DEFAULT_DAY_END = 19;
  var AUTO_CHECK_MS = 60000;

  var bodyEl = null;
  var autoTimer = null;
  var timeZone = DEFAULT_TIME_ZONE;
  var dayStartHour = DEFAULT_DAY_START;
  var dayEndHour = DEFAULT_DAY_END;

  function readPositiveIntAttr(name, fallback) {
    var value = bodyEl && bodyEl.getAttribute ? parseInt(bodyEl.getAttribute(name), 10) : NaN;

    if (isNaN(value)) {
      return fallback;
    }

    return value;
  }

  function readConfig() {
    if (!bodyEl || !bodyEl.getAttribute) {
      return;
    }

    timeZone = bodyEl.getAttribute("data-theme-timezone") || DEFAULT_TIME_ZONE;
    dayStartHour = readPositiveIntAttr("data-theme-day-start", DEFAULT_DAY_START);
    dayEndHour = readPositiveIntAttr("data-theme-day-end", DEFAULT_DAY_END);
  }

  function getHourInTimeZone(date, zone) {
    var formatted;
    var hour;

    if (typeof Intl !== "undefined" && Intl.DateTimeFormat) {
      try {
        formatted = new Intl.DateTimeFormat("en-US", {
          timeZone: zone,
          hour: "numeric",
          hour12: false,
        }).format(date || new Date());
        hour = parseInt(formatted, 10);

        if (!isNaN(hour)) {
          return hour;
        }
      } catch (error) {
        /* fallback below */
      }
    }

    return (date || new Date()).getHours();
  }

  function isDaytime(date) {
    var hour = getHourInTimeZone(date, timeZone);

    return hour >= dayStartHour && hour < dayEndHour;
  }

  function resolveBrightness(date) {
    return isDaytime(date) ? "day" : "night";
  }

  function setBodyThemeClass() {
    if (!bodyEl || !bodyEl.className) {
      return;
    }

    bodyEl.className = bodyEl.className
      .replace(/\btheme-auto\b/g, "")
      .replace(/\btheme-day\b/g, "")
      .replace(/\btheme-night\b/g, "")
      .replace(/\s{2,}/g, " ")
      .replace(/^\s+|\s+$/g, "");

    bodyEl.className = (bodyEl.className + " theme-auto").replace(/\s{2,}/g, " ");
  }

  function applyTheme(date) {
    if (!bodyEl) {
      return;
    }

    setBodyThemeClass();

    if (bodyEl.setAttribute) {
      bodyEl.setAttribute("data-brightness", resolveBrightness(date));
    }
  }

  function refreshAutoTheme() {
    applyTheme(new Date());
  }

  function scheduleAutoCheck() {
    if (autoTimer) {
      window.clearInterval(autoTimer);
    }

    autoTimer = window.setInterval(refreshAutoTheme, AUTO_CHECK_MS);
  }

  function start() {
    bodyEl = document.body;
    readConfig();
    applyTheme(new Date());
    scheduleAutoCheck();
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
