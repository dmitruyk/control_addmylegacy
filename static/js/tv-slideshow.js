/**
 * Full-screen art slideshow with crossfade (Tizen M56 / ES5).
 */
(function () {
  "use strict";

  var slides = [];
  var slideIndex = 0;
  var slideTimer = null;
  var layerA = null;
  var layerB = null;
  var currentLayer = null;
  var alternateLayer = null;
  var captionEl = null;
  var started = false;
  var transitioning = false;
  var loadToken = 0;
  var loadFallbackMs = 8000;

  function readSlides() {
    var dataEl = document.getElementById("tv-slides-data");
    if (!dataEl || !dataEl.textContent) {
      return [];
    }

    try {
      return JSON.parse(dataEl.textContent);
    } catch (error) {
      return [];
    }
  }

  function readNumberAttr(name, fallback) {
    var body = document.body;
    var value = body && body.getAttribute ? parseFloat(body.getAttribute(name)) : NaN;
    if (isNaN(value) || value <= 0) {
      return fallback;
    }
    return value;
  }

  function ensureSlideImage(layer, slide) {
    var img = layer.getElementsByTagName("img")[0];

    if (!img) {
      img = document.createElement("img");
      img.className = "tv-slide-img";
      img.alt = slide.title || "Artwork";
      layer.appendChild(img);
    }

    if (slide.title) {
      img.alt = slide.title;
    }

    return img;
  }

  function updateCaption(slide) {
    if (!captionEl || !slide) {
      return;
    }

    captionEl.textContent = slide.title || "";
  }

  function syncLayersFromDom() {
    if (layerA && layerA.className.indexOf("tv-slide-active") !== -1) {
      currentLayer = layerA;
      alternateLayer = layerB;
      return;
    }

    if (layerB && layerB.className.indexOf("tv-slide-active") !== -1) {
      currentLayer = layerB;
      alternateLayer = layerA;
      return;
    }

    currentLayer = layerA;
    alternateLayer = layerB;
    layerA.className = "tv-slide tv-slide-active";
    layerB.className = "tv-slide";
  }

  function activateIncoming(incoming, outgoing) {
    incoming.className = "tv-slide tv-slide-active";
    outgoing.className = "tv-slide";
    currentLayer = incoming;
    alternateLayer = outgoing;
  }

  function whenImageReady(img, token, callback) {
    var finished = false;

    function finish() {
      if (finished || token !== loadToken) {
        return;
      }

      finished = true;
      img.onload = null;
      img.onerror = null;
      callback();
    }

    if (img.complete && img.naturalWidth > 0) {
      finish();
      return;
    }

    img.onload = finish;
    img.onerror = finish;

    window.setTimeout(finish, loadFallbackMs);
  }

  function swapSlide(index, done) {
    var slide = slides[index];
    var incoming;
    var outgoing;
    var img;
    var token;

    if (!slide || !currentLayer || !alternateLayer) {
      if (done) {
        done();
      }
      return;
    }

    if (transitioning) {
      window.setTimeout(function () {
        swapSlide(index, done);
      }, 120);
      return;
    }

    transitioning = true;
    loadToken += 1;
    token = loadToken;
    incoming = alternateLayer;
    outgoing = currentLayer;
    img = ensureSlideImage(incoming, slide);

    if (img.getAttribute("src") !== slide.url) {
      img.onload = null;
      img.onerror = null;
      img.setAttribute("src", slide.url);
    }

    whenImageReady(img, token, function () {
      if (token !== loadToken) {
        transitioning = false;
        return;
      }

      activateIncoming(incoming, outgoing);
      updateCaption(slide);
      transitioning = false;

      if (done) {
        done();
      }
    });
  }

  function scheduleNextSlide(durationMs) {
    if (slideTimer) {
      window.clearTimeout(slideTimer);
    }

    slideTimer = window.setTimeout(function () {
      slideIndex = (slideIndex + 1) % slides.length;
      swapSlide(slideIndex, function () {
        scheduleNextSlide(durationMs);
      });
    }, durationMs);
  }

  function applyTransitionSeconds(seconds) {
    var value = String(seconds || 2) + "s";

    if (layerA && layerA.style) {
      layerA.style.webkitTransitionDuration = value;
      layerA.style.transitionDuration = value;
    }

    if (layerB && layerB.style) {
      layerB.style.webkitTransitionDuration = value;
      layerB.style.transitionDuration = value;
    }
  }

  function beginSlideshow(durationMs) {
    syncLayersFromDom();
    updateCaption(slides[slideIndex]);

    if (slides.length > 1) {
      scheduleNextSlide(durationMs);
    }
  }

  function start() {
    var durationSeconds = readNumberAttr("data-slide-duration", 12);
    var transitionSeconds = readNumberAttr("data-transition-seconds", 2);
    var durationMs = durationSeconds * 1000;

    if (started) {
      return;
    }

    started = true;
    layerA = document.querySelector(".tv-slide-a");
    layerB = document.querySelector(".tv-slide-b");
    captionEl = document.getElementById("tv-slide-caption");
    slides = readSlides();

    applyTransitionSeconds(transitionSeconds);

    if (!slides.length || !layerA || !layerB) {
      started = false;
      return;
    }

    syncLayersFromDom();
    ensureSlideImage(currentLayer, slides[0]);
    slideIndex = 0;
    beginSlideshow(durationMs);
  }

  function bindReadyEvent() {
    if (document.addEventListener) {
      document.addEventListener("tv-dashboard-ready", start);
    } else if (document.attachEvent) {
      document.attachEvent("ontv-dashboard-ready", start);
    }

    if (document.body && document.body.getAttribute("data-dashboard-ready") === "true") {
      start();
    }
  }

  if (document.readyState === "loading") {
    if (document.addEventListener) {
      document.addEventListener("DOMContentLoaded", bindReadyEvent);
    } else {
      window.attachEvent("onload", bindReadyEvent);
    }
  } else {
    bindReadyEvent();
  }
})();
