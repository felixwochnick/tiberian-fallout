// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  // The game runs entirely in the browser (WebGL, Web Audio, OPFS)
  ssr: false,

  css: ['~/assets/css/main.css', '~/assets/css/menu.css'],

  app: {
    head: {
      htmlAttrs: { lang: 'de' },
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800&family=Rajdhani:wght@400;600&family=Nunito:wght@700;800&display=swap' },
      ],
    },
  },
})
