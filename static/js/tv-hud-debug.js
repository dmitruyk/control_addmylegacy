(function () {
  "use strict";

  var search = String(window.location && window.location.search ? window.location.search : "");
  var enabled =
    search.indexOf("tv_debug=1") !== -1 || search.indexOf("hud_debug=1") !== -1;

  if (!enabled) {
    return;
  }

  var COLORS = {
    viewport: "#ff3b30",
    safe: "#34c759",
    widgets: "#ffcc00",
    weather: "#32ade6",
    datetime: "#bf5af2",
  };

  function hudInsets() {
    var wide = window.matchMedia && window.matchMedia("(min-width: 1600px)").matches;

    if (wide) {
      return { top: 42, right: 56, bottom: 42, left: 56 };
    }

    return { top: 36, right: 48, bottom: 36, left: 48 };
  }

  function widgetBottomInset() {
    var widgets = document.querySelector(".tv-hud-widgets");
    if (widgets && window.getComputedStyle) {
      var bottom = parseFloat(window.getComputedStyle(widgets).bottom);
      if (!isNaN(bottom)) {
        return bottom;
      }
    }

    var wide = window.matchMedia && window.matchMedia("(min-width: 1600px)").matches;
    return wide ? 28 : 24;
  }

  function stackGap() {
    var weather = document.querySelector(".tv-hud-weather");
    if (weather && window.getComputedStyle) {
      var margin = parseFloat(window.getComputedStyle(weather).marginBottom);
      if (!isNaN(margin)) {
        return margin;
      }
    }

    return 24;
  }

  function rect(el) {
    if (!el || !el.getBoundingClientRect) {
      return null;
    }

    var box = el.getBoundingClientRect();

    return {
      top: box.top,
      left: box.left,
      width: box.width,
      height: box.height,
    };
  }

  function strokeRect(ctx, color, x, y, w, h, lineWidth) {
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth || 2;
    ctx.strokeRect(x + 0.5, y + 0.5, Math.max(0, w - 1), Math.max(0, h - 1));
  }

  function drawDomRect(ctx, color, r, lineWidth) {
    if (!r || r.width <= 0 || r.height <= 0) {
      return;
    }

    strokeRect(ctx, color, r.left, r.top, r.width, r.height, lineWidth || 2);
  }

  function drawLabel(ctx, x, y, text) {
    ctx.font = "bold 14px Helvetica, Arial, sans-serif";
    ctx.fillStyle = "rgba(0, 0, 0, 0.72)";
    ctx.fillRect(x, y - 16, ctx.measureText(text).width + 10, 20);
    ctx.fillStyle = "#ffffff";
    ctx.fillText(text, x + 5, y);
  }

  function draw() {
    var canvas = document.getElementById("tv-hud-debug-canvas");
    var ctx = canvas && canvas.getContext ? canvas.getContext("2d") : null;
    var w = window.innerWidth || 0;
    var h = window.innerHeight || 0;
    var inset = hudInsets();
    var bottomWidgets = widgetBottomInset();

    if (!ctx || !canvas) {
      return;
    }

    canvas.width = w;
    canvas.height = h;
    ctx.clearRect(0, 0, w, h);

    /* RED — full browser viewport (what CSS sees as 100% / innerWidth × innerHeight) */
    strokeRect(ctx, COLORS.viewport, 0, 0, w, h, 3);
    drawLabel(ctx, 8, 22, "RED = viewport " + w + "×" + h);

    /* GREEN — HUD safe inset (datetime top/left + widget bottom/left/right) */
    var safeTop = inset.top;
    var safeLeft = inset.left;
    var safeRight = w - inset.right;
    var safeBottom = h - bottomWidgets;
    strokeRect(
      ctx,
      COLORS.safe,
      safeLeft,
      safeTop,
      safeRight - safeLeft,
      safeBottom - safeTop,
      2
    );
    drawLabel(
      ctx,
      safeLeft + 4,
      safeTop + 18,
      "GREEN = HUD safe (" +
        inset.left +
        " L / " +
        inset.top +
        " T / " +
        inset.right +
        " R / " +
        bottomWidgets +
        " B)"
    );

    /* PURPLE — datetime block */
    drawDomRect(ctx, COLORS.datetime, rect(document.querySelector(".tv-hud-datetime")), 2);

    /* YELLOW — widget stack anchor */
    drawDomRect(ctx, COLORS.widgets, rect(document.querySelector(".tv-hud-widgets")), +2);

    /* CYAN — weather row (top of stack — clips here if overflow hidden) */
    drawDomRect(ctx, COLORS.weather, rect(document.querySelector(".tv-hud-weather")), 3);

    var weatherBox = rect(document.querySelector(".tv-hud-weather"));
    var binanceBox = rect(document.querySelector(".tv-hud-binance"));
    var gap = stackGap();

    if (weatherBox && binanceBox) {
      var eqBox = rect(document.querySelector(".tv-hud-earthquake"));
      if (eqBox) {
        var gapWeatherEq = Math.round(eqBox.top - weatherBox.top - weatherBox.height);
        drawLabel(
          ctx,
          Math.min(weatherBox.left + 4, w - 280),
          weatherBox.top + weatherBox.height + 14,
          "gap weather→eq " + gapWeatherEq + "px (expect " + gap + ")"
        );
      }
      var gapBinanceBottom = Math.round(h - binanceBox.top - binanceBox.height);
      drawLabel(
        ctx,
        Math.min(binanceBox.left + 4, w - 280),
        binanceBox.top + binanceBox.height + 14,
        "gap binance→screen " + gapBinanceBottom + "px (expect " + bottomWidgets + ")"
      );
    }

    /* Small crosshair at viewport center */
    ctx.strokeStyle = "rgba(255, 255, 255, 0.45)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(w / 2 - 12, h / 2);
    ctx.lineTo(w / 2 + 12, h / 2);
    ctx.moveTo(w / 2, h / 2 - 12);
    ctx.lineTo(w / 2, h / 2 + 12);
    ctx.stroke();

    /* Legend */
    var legendY = h - 8;
    var lines = [
      "tv_debug=1 — remove from URL when done",
      "RED viewport | GREEN safe | PURPLE clock | YELLOW widgets | CYAN weather",
    ];
    ctx.font = "12px Helvetica, Arial, sans-serif";
    ctx.textAlign = "right";
    for (var i = lines.length - 1; i >= 0; i -= 1) {
      legendY -= 16;
      ctx.fillStyle = "rgba(0, 0, 0, 0.65)";
      var tw = ctx.measureText(lines[i]).width;
      ctx.fillRect(w - tw - 16, legendY - 12, tw + 12, 16);
      ctx.fillStyle = "#fff";
      ctx.fillText(lines[i], w - 10, legendY);
    }
    ctx.textAlign = "left";
  }

  function mount() {
    var canvas = document.createElement("canvas");
    canvas.id = "tv-hud-debug-canvas";
    canvas.className = "tv-hud-debug-canvas";
    canvas.setAttribute("aria-hidden", "true");
    document.body.appendChild(canvas);

    draw();

    if (window.addEventListener) {
      window.addEventListener("resize", draw);
      window.addEventListener("orientationchange", draw);
    }

    /* Redraw after fonts/layout settle (Tizen is slow). */
    setTimeout(draw, 500);
    setTimeout(draw, 2000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
