/* One-time kill switch: remove a previously registered service worker that blocked the dashboard. */
(function () {
  "use strict";

  self.addEventListener("install", function (event) {
    event.waitUntil(self.skipWaiting());
  });

  self.addEventListener("activate", function (event) {
    event.waitUntil(
      self.registration.unregister().then(function () {
        return self.clients.matchAll();
      }).then(function (clients) {
        var index;

        for (index = 0; index < clients.length; index += 1) {
          if (clients[index].url) {
            clients[index].navigate(clients[index].url);
          }
        }
      })
    );
  });

  self.addEventListener("fetch", function () {
    /* no-op */
  });
})();
