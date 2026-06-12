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

    return {
      maxWidth: readCssVarPx(root, "--tv-icloud-max-width", 280),
      maxHeight: readCssVarPx(root, "--tv-icloud-max-height", 210),
    };
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

    if (height > limits.maxHeight) {
      height = limits.maxHeight;
      width = height * aspect;
    }

    return {
      width: Math.max(1, Math.round(width)),
      height: Math.max(1, Math.round(height)),
    };
  }

  function applyPhotoFrame(photo, img) {
    var size;

    if (!widgetEl || !slideshowEl) {
      return;
    }

    size = computeFrameSize(photo, img);
    widgetEl.style.width = size.width + "px";
    slideshowEl.style.width = size.width + "px";
    slideshowEl.style.height = size.height + "px";
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

  function fetchJson(url, onSuccess) {
    var xhr = createXhr();
    var requestUrl = String(url || "");

    if (!xhr || !requestUrl) {
      return;
    }

    requestUrl += (requestUrl.indexOf("?") === -1 ? "?" : "&") + "_=" + new Date().getTime();

    xhr.open("GET", requestUrl, true);
    xhr.timeout = 15000;

    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4 || xhr.status !== 200) {
        return;
      }

      var data;

      try {
        data = JSON.parse(xhr.responseText || "");
      } catch (error) {
        return;
      }

      if (onSuccess) {
        onSuccess(data);
      }
    };

    try {
      xhr.send(null);
    } catch (error) {
      /* ignore */
    }
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
    applyDefaultFrame();
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

    if (layerA && layerA.style) {
      layerA.style.webkitTransitionDuration = value;
      layerA.style.transitionDuration = value;
    }

    if (layerB && layerB.style) {
      layerB.style.webkitTransitionDuration = value;
      layerB.style.transitionDuration = value;
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

    function reveal() {
      if (token !== loadToken) {
        transitioning = false;
        return;
      }

      setDomImageSrc(img, photo.url);
      applyPhotoFrame(photo, img);
      activateIncoming(incoming, outgoing);
      photoIndex = index;
      transitioning = false;

      if (done) {
        done();
      }
    }

    if (isCached(photo.url)) {
      applyPhotoFrame(photo, img);
      reveal();
      return;
    }

    loadImageUrl(
      photo.url,
      token,
      function (loader) {
        if (loader && loader.naturalWidth > 0) {
          applyPhotoFrame(photo, loader);
        }
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
    applyPhotoFrame(firstPhoto, firstImg);

    function afterFirstReady() {
      imageCache[firstPhoto.url] = true;
      applyPhotoFrame(firstPhoto, firstImg);
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
    var body = document.body;
    var nextPhotos = data && data.photos ? data.photos : [];
    var enabled = !!(data && data.enabled);
    var available = !!(data && data.available);

    if (!enabled) {
      setWidgetHidden(true);
      return;
    }

    setWidgetHidden(false);

    if (body && body.setAttribute) {
      if (data && data.slide_duration_seconds) {
        body.setAttribute("data-icloud-slide-duration", String(data.slide_duration_seconds));
      }
      if (data && data.transition_seconds) {
        body.setAttribute("data-icloud-transition-seconds", String(data.transition_seconds));
      }
    }

    applyTransitionSeconds(readTransitionSeconds());

    if (!available || !nextPhotos.length) {
      setEmptyState((data && data.error_label) || "No photos to show");
      return;
    }

    photos = nextPhotos;

    if (started) {
      if (photoIndex >= photos.length) {
        photoIndex = 0;
      }
      applyPhotoFrame(photos[photoIndex], null);
      scheduleNextPhoto();
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

    if (!widgetEl || widgetEl.getAttribute("hidden") === "hidden") {
      startPolling();
      return;
    }

    photos = readInitialPhotos();

    if (!photos.length) {
      applyDefaultFrame();
      startPolling();
      return;
    }

    applyPhotoFrame(photos[0], null);
    started = true;
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
