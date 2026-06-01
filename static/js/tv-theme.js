/**
 * TV display theme — Samsung Tizen TV browser (ES5 / M56).
 *
 * Gallery HUD always uses high-contrast dark mode for readable widgets over photos.
 * Panel brightness is still controlled by Samsung TV Settings → Eco Solution.
 */
(function () {
  "use strict";

  var bodyEl = null;

  function applyDarkTheme() {
    if (!bodyEl) {
      return;
    }

    if (bodyEl.className) {
      bodyEl.className = bodyEl.className
        .replace(/\btheme-auto\b/g, "")
        .replace(/\btheme-day\b/g, "")
        .replace(/\btheme-night\b/g, "")
        .replace(/\s{2,}/g, " ")
        .replace(/^\s+|\s+$/g, "");
      bodyEl.className = (bodyEl.className + " theme-night").replace(/\s{2,}/g, " ");
    }

    if (bodyEl.setAttribute) {
      bodyEl.setAttribute("data-brightness", "night");
    }
  }

  function start() {
    bodyEl = document.body;
    applyDarkTheme();
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
