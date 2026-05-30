/**
 * Hide the magic-remote pointer on Samsung Tizen TV browsers (Chromium ~M56).
 *
 * CSS cursor:none alone is reset after idle. This module stacks:
 * - transparent 1x1 cursor (more reliable than "none" on old WebKit)
 * - injected !important rules
 * - a full-screen shield kept as the last DOM node
 * - rAF + interval reapply, MutationObserver, and visibility hooks
 */
(function () {
  "use strict";

  var STYLE_ID = "tv-cursor-hide-style";
  var SHIELD_ID = "tv-cursor-shield";
  var SHIELD_BACK_ID = "tv-cursor-shield-back";
  var INTERVAL_MS = 50;
  var DOM_SWEEP_MS = 2000;
  var TRANSPARENT_CURSOR =
    'url("data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"), none';

  var CURSOR_RULES =
    "html, body, #" +
    SHIELD_ID +
    ", #" +
    SHIELD_BACK_ID +
    ", html *, body * { cursor: " +
    TRANSPARENT_CURSOR +
    " !important; -webkit-user-select: none !important; user-select: none !important; } #" +
    SHIELD_ID +
    ", #" +
    SHIELD_BACK_ID +
    " { position: fixed !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; margin: 0 !important; padding: 0 !important; border: 0 !important; background: transparent !important; opacity: 0.001 !important; pointer-events: auto !important; touch-action: none !important; z-index: 2147483646 !important; } #" +
    SHIELD_BACK_ID +
    " { z-index: 2147483645 !important; }";

  var rafHandle = null;
  var intervalHandle = null;
  var sweepHandle = null;
  var focusHandle = null;
  var observer = null;
  var started = false;

  function injectStyle() {
    var styleEl = document.getElementById(STYLE_ID);
    var head;

    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = STYLE_ID;
      styleEl.type = "text/css";
      head = document.getElementsByTagName("head")[0];
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

  function setElementCursor(el) {
    if (!el || !el.style) {
      return;
    }

    try {
      el.style.setProperty("cursor", TRANSPARENT_CURSOR, "important");
    } catch (error) {
      el.style.cursor = TRANSPARENT_CURSOR;
    }
  }

  function applyInlineCursor() {
    setElementCursor(document.documentElement);
    setElementCursor(document.body);
    setElementCursor(document.getElementById(SHIELD_ID));
    setElementCursor(document.getElementById(SHIELD_BACK_ID));
  }

  function createShield(id) {
    var shieldEl = document.getElementById(id);

    if (shieldEl || !document.body) {
      return shieldEl;
    }

    shieldEl = document.createElement("div");
    shieldEl.id = id;
    shieldEl.setAttribute("aria-hidden", "true");
    shieldEl.setAttribute("tabindex", "-1");
    shieldEl.setAttribute("role", "presentation");
    document.body.appendChild(shieldEl);

    return shieldEl;
  }

  function ensureShieldsOnTop() {
    var back = createShield(SHIELD_BACK_ID);
    var front = createShield(SHIELD_ID);
    var parent = document.body;

    if (!parent) {
      return;
    }

    if (back) {
      parent.appendChild(back);
      setElementCursor(back);
    }

    if (front) {
      parent.appendChild(front);
      setElementCursor(front);
    }
  }

  function refocusShield() {
    var front = document.getElementById(SHIELD_ID);

    if (!front) {
      return;
    }

    try {
      front.focus();
    } catch (error) {
      /* ignore */
    }
  }

  function sweepDomCursors() {
    var nodes;
    var index;
    var node;

    if (!document.body) {
      return;
    }

    nodes = document.body.getElementsByTagName("*");

    for (index = 0; index < nodes.length; index += 1) {
      node = nodes[index];

      if (!node || !node.style) {
        continue;
      }

      if (node.id === SHIELD_ID || node.id === SHIELD_BACK_ID) {
        continue;
      }

      setElementCursor(node);
    }
  }

  function hideCursor() {
    injectStyle();
    applyInlineCursor();
    ensureShieldsOnTop();
  }

  function tick() {
    hideCursor();
    rafHandle = window.requestAnimationFrame
      ? window.requestAnimationFrame(tick)
      : null;
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
      "wheel",
      "keydown",
      "keyup",
      "keypress",
      "focus",
      "blur",
      "touchstart",
      "touchmove",
      "touchend",
      "pointerdown",
      "pointermove",
      "pointerup",
      "MSPointerDown",
      "MSPointerMove",
      "MSPointerUp",
    ];
    var index;
    var name;

    for (index = 0; index < eventNames.length; index += 1) {
      name = eventNames[index];

      if (document.addEventListener) {
        document.addEventListener(name, hideCursor, true);
      } else if (document.attachEvent) {
        document.attachEvent("on" + name, hideCursor);
      }
    }

    if (document.addEventListener) {
      document.addEventListener("visibilitychange", hideCursor, true);
      window.addEventListener("focus", hideCursor, true);
      window.addEventListener("pageshow", hideCursor, true);
      window.addEventListener("resize", hideCursor, true);
    }
  }

  function observeDom() {
    if (!window.MutationObserver || !document.body) {
      return;
    }

    observer = new MutationObserver(function () {
      hideCursor();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["class", "style"],
    });
  }

  function start() {
    if (started) {
      hideCursor();
      return;
    }

    started = true;
    hideCursor();
    sweepDomCursors();
    bindActivityEvents();
    observeDom();

    if (window.requestAnimationFrame) {
      rafHandle = window.requestAnimationFrame(tick);
    }

    intervalHandle = window.setInterval(hideCursor, INTERVAL_MS);
    sweepHandle = window.setInterval(sweepDomCursors, DOM_SWEEP_MS);
    focusHandle = window.setInterval(refocusShield, 5000);
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
