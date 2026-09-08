{% load static %}const CACHE_NAME = "mindrepo-static-v3";
const STATIC_ASSETS = [
  "/offline/",
  "{% static 'css/app.css' %}",
  "{% static 'js/app.js' %}",
  "{% static 'js/offline.js' %}",
  "{% static 'vendor/bootstrap/bootstrap.rtl.min.css' %}",
  "{% static 'vendor/bootstrap/bootstrap.bundle.min.js' %}",
  "{% static 'vendor/htmx/htmx.min.js' %}",
  "{% static 'vendor/alpine/alpine.min.js' %}",
  "{% static 'icons/mindrepo.svg' %}",
  "{% static 'icons/icon-192.png' %}",
  "{% static 'icons/icon-512.png' %}",
  "{% static 'icons/icon-maskable-512.png' %}"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((names) => Promise.all(
    names.filter((name) => name.startsWith("mindrepo-static-") && name !== CACHE_NAME).map((name) => caches.delete(name))
  )));
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;

  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(() => caches.match("/offline/")));
    return;
  }

  if (!STATIC_ASSETS.includes(url.pathname)) return;
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});
