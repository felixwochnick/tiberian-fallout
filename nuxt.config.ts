// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  // The game runs entirely in the browser (WebGL, Web Audio, OPFS)
  ssr: false,

  modules: [
    // installable, works offline (service worker + precached assets)
    '@vite-pwa/nuxt',
  ],

  css: ['~/assets/css/main.css', '~/assets/css/menu.css'],

  app: {
    head: {
      htmlAttrs: { lang: 'de' },
      meta: [
        { name: 'theme-color', content: '#000000' },
      ],
      link: [
        { rel: 'icon', href: '/favicon.ico' },
        { rel: 'apple-touch-icon', href: '/apple-touch-icon-180x180.png' },
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800&family=Rajdhani:wght@400;600&family=Nunito:wght@700;800&display=swap' },
      ],
    },
  },

  nitro: {
    // the app shell the service worker serves for every page (also offline)
    prerender: { routes: ['/'] },
  },

  pwa: {
    registerType: 'prompt',
    manifest: {
      name: 'Command & Conquer: Tiberian Fallout',
      short_name: 'Tiberian Fallout',
      description: 'Fan-Remake von Command & Conquer: Tiberian Sun im Browser, mit den Original-Spieldaten.',
      lang: 'de',
      theme_color: '#000000',
      background_color: '#000000',
      display: 'fullscreen',
      orientation: 'landscape',
      start_url: '/',
      icons: [
        { src: '/pwa-64x64.png', sizes: '64x64', type: 'image/png' },
        { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
        { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
        { src: '/maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
      ],
    },
    workbox: {
      // everything the game needs offline: app code, models, map data, logos (the game data
      // of Tiberian Sun lies in the browser's own storage, not in the service worker)
      globPatterns: ['**/*.{js,css,html,ico,png,svg,webp,jpg,json,glb}'],
      maximumFileSizeToCacheInBytes: 16 * 1024 * 1024,
      navigateFallback: '/',
      runtimeCaching: [
        {
          // the fonts from Google, kept once loaded
          urlPattern: ({ url }) => url.origin === 'https://fonts.googleapis.com' || url.origin === 'https://fonts.gstatic.com',
          handler: 'CacheFirst',
          options: { cacheName: 'google-fonts', expiration: { maxEntries: 30, maxAgeSeconds: 365 * 24 * 60 * 60 }, cacheableResponse: { statuses: [0, 200] } },
        },
      ],
    },
    client: {
      // keeps the browser's install event for the "Spiel installieren" button on the start page
      installPrompt: true,
      // checked again every hour while the game is open
      periodicSyncForUpdates: 60 * 60,
    },
  },
})
