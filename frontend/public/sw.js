const CACHE_VERSION = "phantom-vsa-v3";
const APP_SHELL_CACHE = `${CACHE_VERSION}:app-shell`;
const STATIC_CACHE = `${CACHE_VERSION}:static`;
const APP_SHELL = ["/", "/manifest.webmanifest", "/offline-cache-policy.json", "/pwa-icon.svg"];
const CACHE_POLICY = {
  app_shell: "cache-first",
  static_assets: "stale-while-revalidate",
  api: "network-only",
  api_read_fallback: "indexeddb-app-cache",
  writes_cached: false
};

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(APP_SHELL_CACHE).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith("phantom-vsa-") && !key.startsWith(CACHE_VERSION))
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(cacheFirst("/", APP_SHELL_CACHE));
    return;
  }

  if (url.origin === self.location.origin && isStaticAsset(url.pathname)) {
    event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
  }
});

function isStaticAsset(pathname) {
  return pathname.startsWith("/assets/") || pathname === "/manifest.webmanifest" || pathname === "/pwa-icon.svg";
}

async function cacheFirst(cacheKey, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(cacheKey);
  if (cached) return cached;
  const response = await fetch(cacheKey);
  if (response.ok) await cache.put(cacheKey, response.clone());
  return response;
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const network = fetch(request).then((response) => {
    if (response.ok) void cache.put(request, response.clone());
    return response;
  });
  return cached || network;
}

self.addEventListener("message", (event) => {
  if (event.data?.type !== "PHANTOM_CACHE_POLICY") return;
  event.source?.postMessage({ type: "PHANTOM_CACHE_POLICY", policy: CACHE_POLICY });
});
