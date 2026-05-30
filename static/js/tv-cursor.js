/**
 * Keep the pointer hidden on Samsung Tizen TV browsers (Chromium M56).
 * CSS cursor:none alone is often reset after a few seconds of idle or
 * remote movement — reapply via style injection, inline styles, and events.
 */
(function () {
  "use strict";

  var STYLE_ID = "tv-cursor-hide-style";
  var SHIELD_ID = "tv-cursor-shield";
  var REAPPLY_MS = 150;
  var TRANSPARENT_CURSOR =
    'url("data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"), none';

  var CURSOR_RULES =
    "html, body, #" +
    SHIELD_ID +
    ", html *, body * { cursor: " +
    TRANSPARENT_CURSOR +
    " !important; }";

  function injectStyle() {
    var styleEl = document.getElementById(STYLE_ID);

    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = STYLE_ID;
      styleEl.type = "text/css";

      var head = document.getElementsByTagName("head")[0];
      if (head) {
        head.appendChild(styleEl);
      }
    }

    if (styleEl.styleSheet) {
      styleEl.styleSheet.cssText = CURSOR_RULES;
    } else {
      styleEl.textContent = CURSOR_RULES;
    }
  }

  function applyInlineCursor() {
    var cursorValue = "none";
    var docEl = document.documentElement;
    var bodyEl = document.body;
    var shieldEl = document.getElementById(SHIELD_ID);

    if (docEl && docEl.style) {
      docEl.style.cursor = cursorValue;
    }

    if (bodyEl && bodyEl.style) {
      bodyEl.style.cursor = cursorValue;
    }

    if (shieldEl && shieldEl.style) {
      shieldEl.style.cursor = cursorValue;
    }
  }

  function ensureShield() {
    var shieldEl = document.getElementById(SHIELD_ID);

    if (shieldEl || !document.body) {
      return shieldEl;
    }

    shieldEl = document.createElement("div");
    shieldEl.id = SHIELD_ID;
    shieldEl.setAttribute("aria-hidden", "true");
    shieldEl.setAttribute("tabindex", "-1");
    document.body.appendChild(shieldEl);

    return shieldEl;
  }

  function hideCursor() {
    injectStyle();
    ensureShield();
    applyInlineCursor();
  }

  function bindActivityEvents() {
    var eventNames = [
      "mousemove",
      "mouseenter",
      "mouseover",
      "mouseout",
      "mousedown",
      "mouseup",
      "click",
      "scroll",
      "keydown",
      "keyup",
      "focus",
      "blur",
    ];
    var i;
    var name;

    for (i = 0; i < eventNames.length; i++) {
      name = eventNames[i];

      if (document.addEventListener) {
        document.addEventListener(name, hideCursor, true);
      } else if (document.attachEvent) {
        document.attachEvent("on" + name, hideCursor);
      }
    }
  }

  function start() {
    hideCursor();
    bindActivityEvents();
    window.setInterval(hideCursor, REAPPLY_MS);
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
