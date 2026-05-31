/**
 * HUD date/time for TV gallery (Tizen M56 / ES5).
 * Uses San Francisco / Bay Area timezone from data-theme-timezone on body.
 */
(function () {
  "use strict";

  var DEFAULT_TIME_ZONE = "America/Los_Angeles";

  var weekdays = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
  ];

  var months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  var weekdayEl = null;
  var dateEl = null;
  var timeEl = null;
  var ampmEl = null;
  var timeZone = DEFAULT_TIME_ZONE;

  function readTimeZone() {
    var bodyEl = document.body;

    if (bodyEl && bodyEl.getAttribute) {
      timeZone = bodyEl.getAttribute("data-theme-timezone") || DEFAULT_TIME_ZONE;
    }
  }

  function pad2(value) {
    return value < 10 ? "0" + value : String(value);
  }

  function formatWeekday(date) {
    if (typeof Intl !== "undefined" && Intl.DateTimeFormat) {
      try {
        return new Intl.DateTimeFormat("en-US", { weekday: "long", timeZone: timeZone }).format(date);
      } catch (error) {
        /* fallback below */
      }
    }
    return weekdays[date.getDay()];
  }

  function formatDate(date) {
    if (typeof Intl !== "undefined" && Intl.DateTimeFormat) {
      try {
        return new Intl.DateTimeFormat("en-US", {
          timeZone: timeZone,
          month: "long",
          day: "numeric",
          year: "numeric",
        }).format(date);
      } catch (error) {
        /* fallback below */
      }
    }

    return months[date.getMonth()] + " " + date.getDate() + ", " + date.getFullYear();
  }

  function formatClock(date) {
    var formatted;
    var match;

    if (typeof Intl !== "undefined" && Intl.DateTimeFormat) {
      try {
        formatted = new Intl.DateTimeFormat("en-US", {
          timeZone: timeZone,
          hour: "numeric",
          minute: "2-digit",
          hour12: true,
        }).format(date);
        match = formatted.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);

        if (match) {
          return {
            time: match[1] + ":" + match[2],
            ampm: match[3].toUpperCase(),
          };
        }
      } catch (error) {
        /* fallback below */
      }
    }

    var hours = date.getHours();
    var minutes = date.getMinutes();
    var period = hours >= 12 ? "PM" : "AM";
    var hour12 = hours % 12;

    if (hour12 === 0) {
      hour12 = 12;
    }

    return {
      time: hour12 + ":" + pad2(minutes),
      ampm: period,
    };
  }

  function setText(el, value) {
    if (!el) {
      return;
    }

    if (el.textContent !== undefined) {
      el.textContent = value;
    } else {
      el.innerText = value;
    }
  }

  function tick() {
    var now = new Date();
    var clock = formatClock(now);

    setText(weekdayEl, formatWeekday(now));
    setText(dateEl, formatDate(now));
    setText(timeEl, clock.time);
    setText(ampmEl, clock.ampm);
  }

  function readPositiveIntAttr(name, fallback) {
    var bodyEl = document.body;
    var value = bodyEl && bodyEl.getAttribute ? parseInt(bodyEl.getAttribute(name), 10) : NaN;

    if (isNaN(value) || value < 1) {
      return fallback || 0;
    }

    return value;
  }

  function scheduleRefresh() {
    var refreshSeconds = readPositiveIntAttr("data-refresh-seconds", 0);
    var slideDurationSeconds = readPositiveIntAttr("data-slide-duration", 12);

    if (!refreshSeconds) {
      return;
    }

    window.setTimeout(function () {
      window.location.reload();
    }, Math.max(refreshSeconds, slideDurationSeconds) * 1000);
  }

  function start() {
    weekdayEl = document.getElementById("tv-hud-weekday");
    dateEl = document.getElementById("tv-hud-date");
    timeEl = document.getElementById("tv-hud-time");
    ampmEl = document.getElementById("tv-hud-ampm");

    if (!weekdayEl || !dateEl || !timeEl || !ampmEl) {
      return;
    }

    readTimeZone();
    tick();
    window.setInterval(tick, 1000);
    scheduleRefresh();
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
