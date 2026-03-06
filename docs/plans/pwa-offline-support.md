# PWA Offline Support for Hiking Route Planner

## Context

The site needs to work as an offline hiking guide on a phone. Must survive browser close (not just browser cache). The approach: make it an installable PWA with a service worker that precaches all local assets (~330K total). CalTopo iframes can't work offline, so we show cached static screenshots as fallback.

## New Files

1. **`html/manifest.json`** — PWA manifest (name, icons, display: standalone, theme color matching nav bar `#2c2c2c`, background matching body `#fafaf8`)
2. **`html/sw.js`** — Service worker: precache all local assets on install, cache-first fetch, versioned cache name (`hiking-v1`), delete old caches on activate
3. **`html/icons/icon-192.png`**, **`icon-512.png`**, **`apple-touch-icon.png`** — Generate simple placeholder icons (solid color squares). User can replace later.

## Modified Files

4. **`html/index.html`** — Add `<link rel="manifest">`, `<meta name="theme-color">`, `<link rel="apple-touch-icon">`, `<meta name="apple-mobile-web-app-capable">`, inline SW registration script
5. **`html/stevens-canyon/index.html`** — Same head tags + SW registration (no CalTopo changes needed, no iframes here)
6. **`html/muddy-creek/index.html`** — Same head tags + SW registration + CalTopo fallback:
   - Add `.caltopo-fallback` CSS styles
   - Convert all 7 CalTopo iframes from `src` to `data-src` (prevents loading when offline)
   - Add `<img class="caltopo-fallback">` sibling to each iframe pointing to screenshot files
   - Add `updateMaps()` JS: checks `navigator.onLine`, shows iframe or fallback image, hides `.map-controls` when offline
   - Listen to `online`/`offline` events for live swapping
7. **`docs/SPEC.md`** — Add PWA section documenting the offline architecture

## User-Provided Files (Later)

The user will need to take CalTopo screenshots and save them as:
- `html/muddy-creek/images/caltopo-overview.png`
- `html/muddy-creek/images/caltopo-day1.png` through `caltopo-day6.png`

Until these exist, offline mode shows everything except maps (which is still better than nothing). The SW asset list has them commented out until they're added.

## Implementation Checklist

- [ ] 1. Generate placeholder icons in `html/icons/` (ImageMagick or Python)
- [ ] 2. Create `html/manifest.json`
- [ ] 3. Add manifest/meta tags + SW registration to `html/index.html`
- [ ] 4. Add manifest/meta tags + SW registration to `html/stevens-canyon/index.html`
- [ ] 5. Add manifest/meta tags + SW registration to `html/muddy-creek/index.html`
- [ ] 6. Create `html/sw.js` with full asset list and cache-first strategy
- [ ] 7. Add `.caltopo-fallback` CSS to `html/muddy-creek/index.html`
- [ ] 8. Convert overview iframe (`.map-pair`) to `data-src` + add fallback img
- [ ] 9. Convert all 6 `.section-map` iframes to `data-src` + add fallback imgs
- [ ] 10. Add `updateMaps()` JS function and online/offline event listeners
- [ ] 11. Update `docs/SPEC.md` with PWA documentation

## Key Design Decisions

**Precache on install, not cache-on-fetch.** User visits one page at home, closes browser, goes hiking, opens another page — it must already be cached. Precaching guarantees this.

**JS-based iframe/image swap, not SW-based.** CalTopo loads in cross-origin iframes. The SW can't intercept cross-origin sub-resources. JS with `navigator.onLine` + `data-src` is simple and sufficient.

**Hand-maintained asset list.** No build tooling. When trips are added, dev updates the array in `sw.js` and bumps the cache version.

**Absolute paths for SW registration.** `navigator.serviceWorker.register('/sw.js')` from all pages. Scope covers `/` and all subdirectories.

## Verification

1. Serve `html/` with `python -m http.server 8000` and open `localhost:8000`
2. Check DevTools > Application > Service Workers — SW should be registered and active
3. Check Application > Cache Storage — all assets should be cached
4. Check Application > Manifest — should show installable PWA info
5. Toggle DevTools > Network > Offline — all pages should load, CalTopo iframes should hide (or show fallback images once screenshots exist), map controls should hide
6. On phone: visit site over HTTPS, "Add to Home Screen", close browser, toggle airplane mode, open app — everything should work
