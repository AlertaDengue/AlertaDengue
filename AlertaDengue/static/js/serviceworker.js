/* global self, caches, fetch */

const CACHE_NAME = "infodengue-pwa-v1";

const OFFLINE_URLS = [
  "/",                   // home
  "/informacoes",       // about / info
  "/report",            // reports entry
  "/equipe",            // team
  "/services/api",      // API page
  "/report",           // reports entry
  // "/report/AC/city",   // city-level report
  // "/report/AC/1200013/202551", // specific report
  "/services/tutorial", // API tutorials page
  "/services/tutorial/R", // R tutorial
  "/services/tutorial/Python", // Python tutorial
  // add /participe/ if needed
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
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
          return null;
        })
      )
    )
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  if (request.method !== "GET") {
    return;
  }

  if (request.url.includes("/services/api")) {
    // network-first for API
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

  // default: cache-first for everything else
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
