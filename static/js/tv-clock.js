/**
 * HUD date/time for TV gallery (Tizen M56 / ES5).
 */
(function () {
  "use strict";

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

  function pad2(value) {
    return value < 10 ? "0" + value : String(value);
  }

  function formatWeekday(date) {
    if (typeof Intl !== "undefined" && Intl.DateTimeFormat) {
      try {
        return new Intl.DateTimeFormat(undefined, { weekday: "long" }).format(date);
      } catch (error) {
        /* fallback below */
      }
    }
    return weekdays[date.getDay()];
  }

  function formatDate(date) {
    if (typeof Intl !== "undefined" && Intl.DateTimeFormat) {
      try {
        return new Intl.DateTimeFormat(undefined, {
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

  function scheduleRefresh() {
    var bodyEl = document.body;
    var refreshSeconds = 0;

    if (bodyEl && bodyEl.getAttribute) {
      refreshSeconds = parseInt(bodyEl.getAttribute("data-refresh-seconds"), 10);
    }

    if (!refreshSeconds || refreshSeconds < 1) {
      return;
    }

    window.setTimeout(function () {
      window.location.reload();
    }, refreshSeconds * 1000);
  }

  function start() {
    weekdayEl = document.getElementById("tv-hud-weekday");
    dateEl = document.getElementById("tv-hud-date");
    timeEl = document.getElementById("tv-hud-time");
    ampmEl = document.getElementById("tv-hud-ampm");

    if (!weekdayEl || !dateEl || !timeEl || !ampmEl) {
      return;
    }

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
