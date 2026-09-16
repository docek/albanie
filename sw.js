/* Albánie 4x4 – offline service worker */
const VERSION = 'v3';
const CORE = ['./', 'index.html', 'pujcovny.html', 'ubytovani.html', 'assets/style.css', 'assets/places.json', 'assets/routes.json',
  'Doporucena-trasa-D.gpx', 'Varianty-D.gpx', 'Alternativa-B.gpx',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'];
const CACHE = 'albanie-' + VERSION, IMG = 'albanie-img';

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.allSettled(CORE.map(u => c.add(u)))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('albanie-') && k !== CACHE && k !== IMG).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  const isImg = u.hostname.endsWith('wikimedia.org') || u.hostname.endsWith('openstreetmap.org') || u.hostname.endsWith('opentopomap.org') || u.hostname.endsWith('arcgisonline.com');
  if (isImg) {
    e.respondWith(caches.open(IMG).then(async c => {
      const hit = await c.match(e.request); if (hit) return hit;
      try { const r = await fetch(e.request); if (r.ok || r.type === 'opaque') c.put(e.request, r.clone()); return r; } catch (err) { return hit || Response.error(); }
    }));
    return;
  }
  // same-origin and CDN: stale-while-revalidate
  e.respondWith(caches.open(CACHE).then(async c => {
    const hit = await c.match(e.request, { ignoreSearch: true });
    const net = fetch(e.request).then(r => { if (r.ok) c.put(e.request, r.clone()); return r; }).catch(() => null);
    return hit || (await net) || Response.error();
  }));
});
self.addEventListener('message', async e => {
  if (!e.data || e.data.type !== 'PRECACHE') return;
  const urls = e.data.urls || [], c = await caches.open(IMG);
  let done = 0, failed = 0;
  const port = e.source; const say = m => { try { if (port) port.postMessage(m); } catch (err) {} };
  const worker = async () => {
    while (urls.length) {
      const u = urls.shift();
      try { if (!(await c.match(u))) { const r = await fetch(u, { mode: 'no-cors' }); await c.put(u, r); } } catch (err) { failed++; }
      done++; if (done % 10 === 0 || !urls.length) say({ type: 'PROGRESS', done, failed, total: e.data.total });
    }
  };
  await Promise.all([worker(), worker(), worker(), worker()]);
  say({ type: 'DONE', done, failed, total: e.data.total });
});
