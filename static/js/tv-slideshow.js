/**
 * Full-screen art slideshow with crossfade (Tizen M56 / ES5).
 * Tizen: decode via off-DOM Image(), warm cache serially, one load at a time.
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
  var loadFallbackMs = 15000;
  var imageCache = {};
  var warming = false;
  var SLIDE_INDEX_KEY = "aml-tv-slide-index";
  var SLIDE_LIST_KEY = "aml-tv-slide-list-key";

  function parseSlidesPayload(raw) {
    var data;
    var text = String(raw || "").trim();

    if (!text) {
      return [];
    }

    try {
      data = JSON.parse(text);
    } catch (error) {
      return [];
    }

    if (typeof data === "string") {
      try {
        data = JSON.parse(data);
      } catch (innerError) {
        return [];
      }
    }

    if (!data || data.length === undefined) {
      return [];
    }

    return data;
  }

  function readSlidesRaw() {
    var dataEl = document.getElementById("tv-slides-data");

    if (!dataEl) {
      return "";
    }

    if (dataEl.textContent) {
      return dataEl.textContent;
    }

    if (dataEl.innerText) {
      return dataEl.innerText;
    }

    if (dataEl.innerHTML) {
      return dataEl.innerHTML;
    }

    return "";
  }

  function readSlides() {
    var parsed = parseSlidesPayload(readSlidesRaw());
    var expected = 0;
    var body = document.body;

    if (body && body.getAttribute) {
      expected = parseInt(body.getAttribute("data-slide-count"), 10);
    }

    if (expected > 0 && parsed.length > 0 && parsed.length < expected) {
      return parseSlidesPayload(readSlidesRaw());
    }

    return parsed;
  }

  function readNumberAttr(name, fallback) {
    var body = document.body;
    var value = body && body.getAttribute ? parseFloat(body.getAttribute(name)) : NaN;

    if (isNaN(value) || value <= 0) {
      return fallback;
    }

    return value;
  }

  function readSlideDurationMs() {
    return readNumberAttr("data-slide-duration", 12) * 1000;
  }

  function slidesListKey() {
    var body = document.body;
    var count = body && body.getAttribute ? body.getAttribute("data-slide-count") : "";
    var duration = body && body.getAttribute ? body.getAttribute("data-slide-duration") : "";

    return String(count) + ":" + String(duration);
  }

  function readSavedSlideIndex() {
    var savedList;
    var savedIndex;

    try {
      savedList = localStorage.getItem(SLIDE_LIST_KEY);
      if (savedList !== slidesListKey()) {
        return 0;
      }

      savedIndex = parseInt(localStorage.getItem(SLIDE_INDEX_KEY), 10);
      if (isNaN(savedIndex) || savedIndex < 0) {
        return 0;
      }

      return savedIndex;
    } catch (error) {
      return 0;
    }
  }

  function saveSlideIndex(index) {
    try {
      localStorage.setItem(SLIDE_LIST_KEY, slidesListKey());
      localStorage.setItem(SLIDE_INDEX_KEY, String(index));
    } catch (error) {
      /* ignore — private mode / Tizen storage limits */
    }
  }

  function applyTimingFromDom() {
    applyTransitionSeconds(readNumberAttr("data-transition-seconds", 2));

    if (started && slides.length > 1) {
      scheduleNextSlide();
    }
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
    layerA.className = "tv-slide tv-slide-a tv-slide-active";
    layerB.className = "tv-slide tv-slide-b";
  }

  function activateIncoming(incoming, outgoing) {
    incoming.className = incoming.className.indexOf("tv-slide-a") !== -1
      ? "tv-slide tv-slide-a tv-slide-active"
      : "tv-slide tv-slide-b tv-slide-active";
    outgoing.className = outgoing.className.indexOf("tv-slide-a") !== -1
      ? "tv-slide tv-slide-a"
      : "tv-slide tv-slide-b";
    currentLayer = incoming;
    alternateLayer = outgoing;
  }

  function isImageLoaded(img) {
    return !!(img && img.complete && img.naturalWidth > 0);
  }

  function setDomImageSrc(domImg, url) {
    if (!domImg || !url) {
      return;
    }

    if (domImg.getAttribute("src") !== url) {
      domImg.onload = null;
      domImg.onerror = null;
      domImg.setAttribute("src", url);
    }
  }

  function isCached(url) {
    return imageCache[url] === true;
  }

  function loadImageUrl(url, token, onSuccess, onFailure) {
    var loader = new Image();
    var finished = false;

    if (isCached(url)) {
      if (onSuccess) {
        onSuccess(null);
      }
      return;
    }

    function finish(ok) {
      if (finished || token !== loadToken) {
        return;
      }

      finished = true;
      loader.onload = null;
      loader.onerror = null;

      if (ok && isImageLoaded(loader)) {
        imageCache[url] = true;
        if (onSuccess) {
          onSuccess(loader);
        }
        return;
      }

      imageCache[url] = false;
      if (onFailure) {
        onFailure();
      }
    }

    loader.onload = function () {
      finish(true);
    };
    loader.onerror = function () {
      finish(false);
    };
    loader.src = url;

    window.setTimeout(function () {
      finish(false);
    }, loadFallbackMs);
  }

  function warmSlideAt(index, onDone) {
    var slide = slides[index];

    if (!slide || !slide.url) {
      if (onDone) {
        onDone();
      }
      return;
    }

    if (isCached(slide.url)) {
      if (onDone) {
        onDone();
      }
      return;
    }

    loadToken += 1;
    loadImageUrl(
      slide.url,
      loadToken,
      function () {
        if (onDone) {
          onDone();
        }
      },
      function () {
        if (onDone) {
          onDone();
        }
      }
    );
  }

  function warmSlidesSequential(startIndex, onDone) {
    var position = 0;

    if (warming || slides.length < 1) {
      if (onDone) {
        onDone();
      }
      return;
    }

    warming = true;

    function step() {
      var index;

      if (position >= slides.length) {
        warming = false;
        if (onDone) {
          onDone();
        }
        return;
      }

      index = (startIndex + position) % slides.length;
      position += 1;

      warmSlideAt(index, function () {
        window.setTimeout(step, 60);
      });
    }

    step();
  }

  function showSlide(index, done, onFail) {
    var slide = slides[index];
    var incoming;
    var outgoing;
    var img;
    var token;

    if (!slide || !slide.url || !currentLayer || !alternateLayer) {
      transitioning = false;
      if (done) {
        done();
      }
      return;
    }

    incoming = alternateLayer;
    outgoing = currentLayer;
    img = ensureSlideImage(incoming, slide);
    transitioning = true;
    loadToken += 1;
    token = loadToken;

    function reveal() {
      if (token !== loadToken) {
        transitioning = false;
        return;
      }

      setDomImageSrc(img, slide.url);
      activateIncoming(incoming, outgoing);
      updateCaption(slide);
      slideIndex = index;
      saveSlideIndex(index);
      transitioning = false;

      warmSlideAt((index + 1) % slides.length, function () {});
      warmSlideAt((index + 2) % slides.length, function () {});

      if (done) {
        done();
      }
    }

    if (isCached(slide.url)) {
      reveal();
      return;
    }

    loadImageUrl(
      slide.url,
      token,
      function () {
        reveal();
      },
      function () {
        transitioning = false;
        if (onFail) {
          onFail();
        }
      }
    );
  }

  function swapSlide(index, done, attemptsLeft) {
    attemptsLeft = attemptsLeft === undefined ? slides.length : attemptsLeft;

    if (!slides.length || attemptsLeft < 1) {
      transitioning = false;
      if (done) {
        done();
      }
      return;
    }

    if (transitioning) {
      window.setTimeout(function () {
        swapSlide(index, done, attemptsLeft);
      }, 120);
      return;
    }

    showSlide(
      index,
      function () {
        if (done) {
          done();
        }
      },
      function () {
        swapSlide((index + 1) % slides.length, done, attemptsLeft - 1);
      }
    );
  }

  function scheduleNextSlide() {
    var durationMs = readSlideDurationMs();

    if (slideTimer) {
      window.clearTimeout(slideTimer);
      slideTimer = null;
    }

    if (slides.length < 2) {
      return;
    }

    slideTimer = window.setTimeout(function () {
      var nextIndex = (slideIndex + 1) % slides.length;
      swapSlide(nextIndex, function () {
        scheduleNextSlide();
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

  function beginSlideshow() {
    syncLayersFromDom();
    updateCaption(slides[slideIndex]);
    warmSlidesSequential((slideIndex + 1) % slides.length, function () {});
    scheduleNextSlide();
  }

  function startWithFirstSlide() {
    var firstSlide = slides[0];
    var firstImg;

    if (!firstSlide || !firstSlide.url) {
      started = false;
      return;
    }

    firstImg = ensureSlideImage(currentLayer, firstSlide);

    function afterFirstReady() {
      imageCache[firstSlide.url] = true;
      slideIndex = 0;
      saveSlideIndex(0);
      updateCaption(firstSlide);
      beginSlideshow();
    }

    if (isImageLoaded(firstImg) && firstImg.getAttribute("src") === firstSlide.url) {
      afterFirstReady();
      return;
    }

    setDomImageSrc(firstImg, firstSlide.url);
    loadToken += 1;
    loadImageUrl(
      firstSlide.url,
      loadToken,
      function () {
        afterFirstReady();
      },
      function () {
        if (slides.length > 1) {
          swapSlide(1, function () {
            beginSlideshow();
          });
          return;
        }
        started = false;
      }
    );
  }

  function startAtSavedSlide() {
    var savedIndex = readSavedSlideIndex();

    if (savedIndex < 0 || savedIndex >= slides.length) {
      savedIndex = 0;
    }

    slideIndex = savedIndex;

    if (savedIndex === 0) {
      startWithFirstSlide();
      return;
    }

    syncLayersFromDom();
    swapSlide(savedIndex, function () {
      beginSlideshow();
    });
  }

  function start() {
    if (started && slideTimer) {
      return;
    }

    started = true;
    layerA = document.querySelector(".tv-slide-a");
    layerB = document.querySelector(".tv-slide-b");
    captionEl = document.getElementById("tv-slide-caption");
    slides = readSlides();

    applyTimingFromDom();

    if (!slides.length || !layerA || !layerB) {
      started = false;
      return;
    }

    if (captionEl && slides.length) {
      captionEl.setAttribute("data-slide-total", String(slides.length));
      captionEl.setAttribute("data-slide-index", String(readSavedSlideIndex()));
    }

    syncLayersFromDom();
    startAtSavedSlide();
  }

  function galleryVisibleInDom() {
    var root = document.getElementById("tv-root");

    if (!root || !root.className) {
      return false;
    }

    return root.className.indexOf("tv-content-hidden") === -1;
  }

  function bindReadyEvent() {
    if (document.addEventListener) {
      document.addEventListener("tv-dashboard-ready", start);
    } else if (document.attachEvent) {
      document.attachEvent("ontv-dashboard-ready", start);
    }

    if (
      (document.body && document.body.getAttribute("data-dashboard-ready") === "true") ||
      galleryVisibleInDom()
    ) {
      start();
    }
  }

  window.amlTvSlideshowStart = start;
  window.amlTvSlideshowApplyConfig = applyTimingFromDom;

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
