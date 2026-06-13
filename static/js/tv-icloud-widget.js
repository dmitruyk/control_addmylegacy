/**
 * Lower-left iCloud shared album widget slideshow (Tizen M56 / ES5).
 */
(function () {
  "use strict";

  var photos = [];
  var photoIndex = 0;
  var slideTimer = null;
  var pollTimer = null;
  var layerA = null;
  var layerB = null;
  var currentLayer = null;
  var alternateLayer = null;
  var widgetEl = null;
  var slideshowEl = null;
  var frameEl = null;
  var started = false;
  var transitioning = false;
  var loadToken = 0;
  var loadFallbackMs = 12000;
  var imageCache = {};

  function readNumberAttr(name, fallback) {
    var body = document.body;
    var value = body && body.getAttribute ? parseFloat(body.getAttribute(name)) : NaN;

    if (isNaN(value) || value <= 0) {
      return fallback;
    }

    return value;
  }

  function readSlideDurationMs() {
    return readNumberAttr("data-icloud-slide-duration", 8) * 1000;
  }

  function readTransitionSeconds() {
    return readNumberAttr("data-icloud-transition-seconds", 1.5);
  }

  function readSizeScalePercent() {
    var body = document.body;
    var scale = body && body.getAttribute ? parseInt(body.getAttribute("data-icloud-size-scale-percent"), 10) : 100;

    if (isNaN(scale)) {
      return 100;
    }

    if (scale < 0) {
      return 0;
    }

    if (scale > 300) {
      return 300;
    }

    return scale;
  }

  function applySizeScalePercent(scale) {
    var body = document.body;
    var normalized = scale;

    if (normalized === undefined || normalized === null || isNaN(normalized)) {
      normalized = 100;
    }

    normalized = parseInt(normalized, 10);
    if (isNaN(normalized)) {
      normalized = 100;
    }
    if (normalized < 0) {
      normalized = 0;
    }
    if (normalized > 300) {
      normalized = 300;
    }

    if (body && body.setAttribute) {
      body.setAttribute("data-icloud-size-scale-percent", String(normalized));
    }

    if (normalized < 1) {
      setWidgetHidden(true);
      return false;
    }

    setWidgetHidden(false);
    schedulePinWidgetFrame();
    return true;
  }

  function readCssVarPx(element, name, fallback) {
    var style;
    var value;

    if (!element || !window.getComputedStyle) {
      return fallback;
    }

    style = window.getComputedStyle(element);
    value = parseFloat(style.getPropertyValue(name));

    if (isNaN(value) || value <= 0) {
      return fallback;
    }

    return value;
  }

  function readFrameLimits() {
    var root = frameEl || widgetEl;
    var scale = readSizeScalePercent() / 100;
    var baseMaxWidth = readCssVarPx(root, "--tv-icloud-max-width", 336);
    var baseMaxHeight = readCssVarPx(root, "--tv-icloud-max-height", 252);

    if (scale <= 0) {
      return {
        maxWidth: 0,
        maxHeight: 0,
      };
    }

    return {
      maxWidth: Math.max(1, Math.round(baseMaxWidth * scale)),
      maxHeight: Math.max(1, Math.round(baseMaxHeight * scale)),
    };
  }

  function readCornerInset() {
    var inset = readCssVarPx(frameEl || widgetEl, "--tv-icloud-inset", 0);

    if (inset > 0) {
      return inset;
    }

    if (window.matchMedia) {
      if (window.matchMedia("(max-width: 960px)").matches) {
        return 24;
      }

      if (window.matchMedia("(min-width: 1600px)").matches) {
        return 56;
      }
    }

    return 48;
  }

  function pinWidgetFrame() {
    var inset;
    var box;
    var vh;
    var topPx;

    if (!frameEl || frameEl.getAttribute("hidden") === "hidden") {
      return;
    }

    inset = readCornerInset();
    frameEl.style.position = "absolute";
    frameEl.style.left = inset + "px";
    frameEl.style.right = "auto";
    frameEl.style.bottom = inset + "px";
    frameEl.style.top = "auto";

    if (!frameEl.getBoundingClientRect) {
      return;
    }

    box = frameEl.getBoundingClientRect();
    vh = window.innerHeight || document.documentElement.clientHeight || 0;

    /* Tizen M56: bottom is ignored for some layouts — anchor with explicit top. */
    if (vh > 0 && box.height > 0 && box.top < vh * 0.45) {
      topPx = Math.max(0, Math.round(vh - box.height - inset));
      frameEl.style.bottom = "auto";
      frameEl.style.top = topPx + "px";
    }
  }

  function schedulePinWidgetFrame() {
    pinWidgetFrame();

    window.setTimeout(pinWidgetFrame, 0);
    window.setTimeout(pinWidgetFrame, 120);
  }

  function photoAspect(photo, img) {
    var width = photo && photo.width ? parseInt(photo.width, 10) : 0;
    var height = photo && photo.height ? parseInt(photo.height, 10) : 0;

    if (img && img.naturalWidth > 0 && img.naturalHeight > 0) {
      width = img.naturalWidth;
      height = img.naturalHeight;
    }

    if (!width || !height || width < 1 || height < 1) {
      return 4 / 3;
    }

    return width / height;
  }

  function computeFrameSize(photo, img) {
    var limits = readFrameLimits();
    var aspect = photoAspect(photo, img);
    var width = limits.maxWidth;
    var height = width / aspect;

    if (limits.maxWidth <= 0 || limits.maxHeight <= 0) {
      return {
        width: 0,
        height: 0,
      };
    }

    if (height > limits.maxHeight) {
      height = limits.maxHeight;
      width = height * aspect;
    }

    return {
      width: Math.max(1, Math.round(width)),
      height: Math.max(1, Math.round(height)),
    };
  }

  function readFrameResizeMs() {
    return readTransitionSeconds() * 1000;
  }

  function setFrameTransitionEnabled(enabled) {
    if (!widgetEl) {
      return;
    }

    if (enabled) {
      widgetEl.className = widgetEl.className.replace(/\btv-icloud-no-frame-transition\b/g, "").replace(/\s+/g, " ").replace(/^\s|\s$/g, "");
      return;
    }

    if (widgetEl.className.indexOf("tv-icloud-no-frame-transition") === -1) {
      widgetEl.className += " tv-icloud-no-frame-transition";
    }
  }

  function applyPhotoFrame(photo, img) {
    var size;
    var widthPx;
    var heightPx;

    if (!widgetEl || !slideshowEl) {
      return;
    }

    size = computeFrameSize(photo, img);
    widthPx = size.width + "px";
    heightPx = size.height + "px";

    if (widgetEl.style.width === widthPx && slideshowEl.style.width === widthPx && slideshowEl.style.height === heightPx) {
      return size;
    }

    widgetEl.style.width = widthPx;
    slideshowEl.style.width = widthPx;
    slideshowEl.style.height = heightPx;
    schedulePinWidgetFrame();
    return size;
  }

  function frameSizeFromElement() {
    var width = parseInt(slideshowEl && slideshowEl.style.width, 10) || 0;
    var height = parseInt(slideshowEl && slideshowEl.style.height, 10) || 0;
    var computed;

    if ((!width || !height) && slideshowEl && window.getComputedStyle) {
      computed = window.getComputedStyle(slideshowEl);
      width = Math.round(parseFloat(computed.width)) || width;
      height = Math.round(parseFloat(computed.height)) || height;
    }

    return {
      width: width,
      height: height,
    };
  }

  function frameSizesMatch(a, b) {
    return !!(a && b && a.width === b.width && a.height === b.height);
  }

  function animatePhotoFrame(photo, img, onComplete) {
    var nextSize;
    var currentSize;
    var resizeMs;
    var finished = false;

    if (!widgetEl || !slideshowEl) {
      if (onComplete) {
        onComplete();
      }
      return;
    }

    nextSize = computeFrameSize(photo, img);
    currentSize = frameSizeFromElement();

    if (frameSizesMatch(currentSize, nextSize)) {
      if (onComplete) {
        onComplete();
      }
      return;
    }

    resizeMs = readFrameResizeMs();

    function finish() {
      if (finished) {
        return;
      }

      finished = true;

      if (slideshowEl.removeEventListener) {
        slideshowEl.removeEventListener("transitionend", handleTransitionEnd);
      } else if (slideshowEl.detachEvent) {
        slideshowEl.detachEvent("ontransitionend", handleTransitionEnd);
      }

      if (onComplete) {
        onComplete();
      }

      schedulePinWidgetFrame();
    }

    function handleTransitionEnd(event) {
      if (!event) {
        finish();
        return;
      }

      if (event.target === slideshowEl && (event.propertyName === "width" || event.propertyName === "height")) {
        finish();
      }
    }

    setFrameTransitionEnabled(true);
    applyPhotoFrame(photo, img);

    if (slideshowEl.addEventListener) {
      slideshowEl.addEventListener("transitionend", handleTransitionEnd);
    } else if (slideshowEl.attachEvent) {
      slideshowEl.attachEvent("ontransitionend", handleTransitionEnd);
    }

    window.setTimeout(finish, resizeMs + 80);
  }

  function applyDefaultFrame() {
    var limits = readFrameLimits();
    var width = limits.maxWidth;
    var height = Math.round(Math.min(limits.maxHeight, width * 0.75));

    if (!widgetEl || !slideshowEl) {
      return;
    }

    widgetEl.style.width = width + "px";
    slideshowEl.style.width = width + "px";
    slideshowEl.style.height = height + "px";
    schedulePinWidgetFrame();
  }

  function parsePhotosPayload(raw) {
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

  function readInitialPhotos() {
    var dataEl = document.getElementById("tv-icloud-photos-data");

    if (!dataEl) {
      return [];
    }

    if (dataEl.textContent) {
      return parsePhotosPayload(dataEl.textContent);
    }

    if (dataEl.innerText) {
      return parsePhotosPayload(dataEl.innerText);
    }

    return [];
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

  function applyConfigFromPayload(data) {
    var body = document.body;
    var enabled = !!(data && data.enabled);
    var scaleValue = data && data.size_scale_percent !== undefined ? data.size_scale_percent : readSizeScalePercent();

    if (!enabled) {
      setWidgetHidden(true);
      return false;
    }

    if (body && body.setAttribute) {
      if (data && data.slide_duration_seconds) {
        body.setAttribute("data-icloud-slide-duration", String(data.slide_duration_seconds));
      }
      if (data && data.transition_seconds) {
        body.setAttribute("data-icloud-transition-seconds", String(data.transition_seconds));
      }
    }

    if (!applySizeScalePercent(scaleValue)) {
      return false;
    }

    applyTransitionSeconds(readTransitionSeconds());
    return true;
  }

  function fetchJson(url, onSuccess, onFailure) {
    var xhr = createXhr();
    var requestUrl = String(url || "");

    if (!xhr || !requestUrl) {
      if (onFailure) {
        onFailure(0);
      }
      return;
    }

    requestUrl += (requestUrl.indexOf("?") === -1 ? "?" : "&") + "_=" + new Date().getTime();

    xhr.open("GET", requestUrl, true);
    xhr.timeout = 15000;

    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) {
        return;
      }

      if (xhr.status !== 200) {
        if (onFailure) {
          onFailure(xhr.status);
        }
        return;
      }

      var data;

      try {
        data = JSON.parse(xhr.responseText || "");
      } catch (error) {
        if (onFailure) {
          onFailure(0);
        }
        return;
      }

      if (onSuccess) {
        onSuccess(data);
      }
    };

    try {
      xhr.send(null);
    } catch (error) {
      if (onFailure) {
        onFailure(0);
      }
    }
  }

  function refreshWidgetConfig(onReady) {
    var url = document.body.getAttribute("data-icloud-widget-url");
    var finished = false;

    function finish(ok) {
      if (finished) {
        return;
      }

      finished = true;

      if (onReady) {
        onReady(!!ok);
      }
    }

    if (!url) {
      finish(true);
      return;
    }

    fetchJson(
      url,
      function (data) {
        var nextPhotos = data && data.photos ? data.photos : null;
        var available = !!(data && data.available);

        if (!applyConfigFromPayload(data)) {
          finish(false);
          return;
        }

        if (available && nextPhotos && nextPhotos.length) {
          photos = nextPhotos;
          if (photoIndex >= photos.length) {
            photoIndex = 0;
          }
        }

        finish(true);
      },
      function () {
        finish(true);
      }
    );
  }

  function readPollMs() {
    var body = document.body;
    var seconds = body && body.getAttribute ? parseInt(body.getAttribute("data-icloud-poll-seconds"), 10) : 0;

    if (!seconds || seconds < 1) {
      return 0;
    }

    return seconds * 1000;
  }

  function setWidgetHidden(hidden) {
    if (!widgetEl) {
      return;
    }

    if (hidden) {
      widgetEl.setAttribute("hidden", "hidden");
      stopSlideshow();
      return;
    }

    widgetEl.removeAttribute("hidden");
  }

  function setEmptyState(message) {
    if (!slideshowEl) {
      return;
    }

    slideshowEl.innerHTML =
      '<div class="tv-icloud-empty"><p class="tv-icloud-empty-label">' +
      String(message || "No photos to show") +
      "</p></div>";
    layerA = null;
    layerB = null;
    currentLayer = null;
    alternateLayer = null;
    setFrameTransitionEnabled(false);
    applyDefaultFrame();
    setFrameTransitionEnabled(true);
    stopSlideshow();
  }

  function ensureSlideLayers() {
    if (!slideshowEl) {
      return false;
    }

    layerA = slideshowEl.querySelector(".tv-icloud-slide-a");
    layerB = slideshowEl.querySelector(".tv-icloud-slide-b");

    if (!layerA || !layerB) {
      slideshowEl.innerHTML =
        '<div class="tv-icloud-slide tv-icloud-slide-a tv-icloud-slide-active"></div>' +
        '<div class="tv-icloud-slide tv-icloud-slide-b"></div>';
      layerA = slideshowEl.querySelector(".tv-icloud-slide-a");
      layerB = slideshowEl.querySelector(".tv-icloud-slide-b");
    }

    syncLayersFromDom();
    applyTransitionSeconds(readTransitionSeconds());
    return !!(layerA && layerB);
  }

  function syncLayersFromDom() {
    if (layerA && layerA.className.indexOf("tv-icloud-slide-active") !== -1) {
      currentLayer = layerA;
      alternateLayer = layerB;
      return;
    }

    if (layerB && layerB.className.indexOf("tv-icloud-slide-active") !== -1) {
      currentLayer = layerB;
      alternateLayer = layerA;
      return;
    }

    currentLayer = layerA;
    alternateLayer = layerB;
    layerA.className = "tv-icloud-slide tv-icloud-slide-a tv-icloud-slide-active";
    layerB.className = "tv-icloud-slide tv-icloud-slide-b";
  }

  function activateIncoming(incoming, outgoing) {
    incoming.className = incoming.className.indexOf("tv-icloud-slide-a") !== -1
      ? "tv-icloud-slide tv-icloud-slide-a tv-icloud-slide-active"
      : "tv-icloud-slide tv-icloud-slide-b tv-icloud-slide-active";
    outgoing.className = outgoing.className.indexOf("tv-icloud-slide-a") !== -1
      ? "tv-icloud-slide tv-icloud-slide-a"
      : "tv-icloud-slide tv-icloud-slide-b";
    currentLayer = incoming;
    alternateLayer = outgoing;
  }

  function applyTransitionSeconds(seconds) {
    var value = String(seconds || 1.5) + "s";
    var frameTransition = "width " + value + " ease, height " + value + " ease";
    var widthTransition = "width " + value + " ease";

    if (layerA && layerA.style) {
      layerA.style.webkitTransitionDuration = value;
      layerA.style.transitionDuration = value;
    }

    if (layerB && layerB.style) {
      layerB.style.webkitTransitionDuration = value;
      layerB.style.transitionDuration = value;
    }

    if (widgetEl && widgetEl.style) {
      widgetEl.style.webkitTransition = widthTransition;
      widgetEl.style.transition = widthTransition;
    }

    if (slideshowEl && slideshowEl.style) {
      slideshowEl.style.webkitTransition = frameTransition;
      slideshowEl.style.transition = frameTransition;
    }
  }

  function ensureSlideImage(layer, photo) {
    var img = layer.getElementsByTagName("img")[0];
    var altText = photo.caption || "Photo";

    if (!img) {
      img = document.createElement("img");
      img.className = "tv-icloud-slide-img";
      layer.appendChild(img);
    }

    img.alt = altText;
    return img;
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

  function showPhoto(index, done, onFail) {
    var photo = photos[index];
    var incoming;
    var outgoing;
    var img;
    var token;

    if (!photo || !photo.url || !currentLayer || !alternateLayer) {
      transitioning = false;
      if (done) {
        done();
      }
      return;
    }

    incoming = alternateLayer;
    outgoing = currentLayer;
    img = ensureSlideImage(incoming, photo);
    transitioning = true;
    loadToken += 1;
    token = loadToken;

    function reveal(resolvedImg) {
      var refImg = resolvedImg || img;
      var nextSize;
      var currentSize;

      if (token !== loadToken) {
        transitioning = false;
        return;
      }

      nextSize = computeFrameSize(photo, refImg);
      currentSize = frameSizeFromElement();

      function finishReveal() {
        if (token !== loadToken) {
          transitioning = false;
          return;
        }

        setDomImageSrc(img, photo.url);
        incoming.style.opacity = "";
        activateIncoming(incoming, outgoing);
        outgoing.style.opacity = "";
        photoIndex = index;
        transitioning = false;

        if (done) {
          done();
        }
      }

      if (!frameSizesMatch(currentSize, nextSize)) {
        outgoing.style.opacity = "0";
        incoming.style.opacity = "0";
        animatePhotoFrame(photo, refImg, finishReveal);
        return;
      }

      finishReveal();
    }

    if (isCached(photo.url)) {
      reveal(isImageLoaded(img) ? img : null);
      return;
    }

    loadImageUrl(
      photo.url,
      token,
      function (loader) {
        reveal(loader && loader.naturalWidth > 0 ? loader : null);
      },
      function () {
        transitioning = false;
        if (onFail) {
          onFail();
        }
      }
    );
  }

  function swapPhoto(index, done, attemptsLeft) {
    attemptsLeft = attemptsLeft === undefined ? photos.length : attemptsLeft;

    if (!photos.length || attemptsLeft < 1) {
      transitioning = false;
      if (done) {
        done();
      }
      return;
    }

    if (transitioning) {
      window.setTimeout(function () {
        swapPhoto(index, done, attemptsLeft);
      }, 120);
      return;
    }

    refreshWidgetConfig(function (ok) {
      if (!ok) {
        transitioning = false;
        if (done) {
          done();
        }
        return;
      }

      showPhoto(
        index,
        function () {
          if (done) {
            done();
          }
        },
        function () {
          swapPhoto((index + 1) % photos.length, done, attemptsLeft - 1);
        }
      );
    });
  }

  function scheduleNextPhoto() {
    var durationMs = readSlideDurationMs();

    if (slideTimer) {
      window.clearTimeout(slideTimer);
      slideTimer = null;
    }

    if (photos.length < 2) {
      return;
    }

    slideTimer = window.setTimeout(function () {
      var nextIndex = (photoIndex + 1) % photos.length;
      swapPhoto(nextIndex, function () {
        scheduleNextPhoto();
      });
    }, durationMs);
  }

  function stopSlideshow() {
    if (slideTimer) {
      window.clearTimeout(slideTimer);
      slideTimer = null;
    }

    transitioning = false;
    started = false;
  }

  function beginSlideshow() {
    if (!ensureSlideLayers()) {
      return;
    }

    scheduleNextPhoto();
  }

  function startWithFirstPhoto() {
    var firstPhoto = photos[0];
    var firstImg;

    if (!firstPhoto || !firstPhoto.url || !ensureSlideLayers()) {
      started = false;
      return;
    }

    firstImg = ensureSlideImage(currentLayer, firstPhoto);
    setFrameTransitionEnabled(false);
    applyPhotoFrame(firstPhoto, null);

    function afterFirstReady() {
      imageCache[firstPhoto.url] = true;
      if (isImageLoaded(firstImg)) {
        setFrameTransitionEnabled(false);
        applyPhotoFrame(firstPhoto, firstImg);
      }
      setFrameTransitionEnabled(true);
      applyTransitionSeconds(readTransitionSeconds());
      photoIndex = 0;
      beginSlideshow();
    }

    if (isImageLoaded(firstImg) && firstImg.getAttribute("src") === firstPhoto.url) {
      afterFirstReady();
      return;
    }

    setDomImageSrc(firstImg, firstPhoto.url);
    loadToken += 1;
    loadImageUrl(
      firstPhoto.url,
      loadToken,
      function (loader) {
        if (loader && loader.naturalWidth > 0) {
          applyPhotoFrame(firstPhoto, loader);
        }
        afterFirstReady();
      },
      function () {
        if (photos.length > 1) {
          swapPhoto(1, function () {
            beginSlideshow();
          });
          return;
        }
        started = false;
      }
    );
  }

  function applyPayload(data) {
    var nextPhotos = data && data.photos ? data.photos : [];
    var available = !!(data && data.available);

    if (!applyConfigFromPayload(data)) {
      return;
    }

    if (!available || !nextPhotos.length) {
      setEmptyState((data && data.error_label) || "No photos to show");
      return;
    }

    photos = nextPhotos;

    if (started) {
      if (photoIndex >= photos.length) {
        photoIndex = 0;
      }
      animatePhotoFrame(photos[photoIndex], null, function () {
        scheduleNextPhoto();
      });
      return;
    }

    started = true;
    startWithFirstPhoto();
  }

  function pollWidgetData() {
    var url = document.body.getAttribute("data-icloud-widget-url");

    if (!url) {
      return;
    }

    fetchJson(url, applyPayload);
  }

  function startPolling() {
    var pollMs = readPollMs();

    if (!pollMs || pollTimer) {
      return;
    }

    pollTimer = window.setInterval(pollWidgetData, pollMs);
  }

  function start() {
    widgetEl = document.getElementById("tv-icloud-widget");
    slideshowEl = document.getElementById("tv-icloud-slideshow");
    frameEl = document.getElementById("tv-widget-icloud");

    if (window.addEventListener) {
      window.addEventListener("resize", schedulePinWidgetFrame);
    } else if (window.attachEvent) {
      window.attachEvent("onresize", schedulePinWidgetFrame);
    }

    if (!widgetEl || widgetEl.getAttribute("hidden") === "hidden") {
      startPolling();
      return;
    }

    if (!applySizeScalePercent(readSizeScalePercent())) {
      startPolling();
      return;
    }

    photos = readInitialPhotos();

    if (!photos.length) {
      setFrameTransitionEnabled(false);
      applyDefaultFrame();
      setFrameTransitionEnabled(true);
      schedulePinWidgetFrame();
      startPolling();
      return;
    }

    setFrameTransitionEnabled(false);
    applyPhotoFrame(photos[0], null);
    setFrameTransitionEnabled(true);
    applyTransitionSeconds(readTransitionSeconds());
    started = true;
    schedulePinWidgetFrame();
    startWithFirstPhoto();
    startPolling();
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
