/* global self, caches, fetch */

const CACHE_NAME = "infodengue-pwa-v1";

const OFFLINE_URLS = [
  "/",                      // home
  "/informacoes/",          // info / about
  "/equipe/",               // team
  "/participe/",            // participate
  "/report/",               // reports entry
  "/services/",             // data/services landing
  "/services/api",          // API page (no trailing slash in URLconf)
  "/services/tutorial",     // tutorials index
  "/services/tutorial/R",   // R tutorial
  "/services/tutorial/Python", // Python tutorial
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(OFFLINE_URLS))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => (key !== CACHE_NAME ? caches.delete(key) : null))
      )
    )
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  if (request.method !== "GET") {
    return;
  }

  // Network-first for API
  if (request.url.includes("/services/api")) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Cache-first for everything else
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(request).then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        return response;
      });
    })
  );
});
