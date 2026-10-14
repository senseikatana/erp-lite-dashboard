import { fileURLToPath } from 'node:url'

export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  devtools: { enabled: true },
  ssr: true,

  modules: ['@nuxtjs/i18n', '@pinia/nuxt'],

  css: ['~/assets/css/main.css'],

  i18n: {
    strategy: 'no_prefix',
    defaultLocale: 'es',
    locales: [
      { code: 'es', name: 'Español', file: 'es.json' },
      { code: 'ca', name: 'Català', file: 'ca.json' },
      { code: 'en', name: 'English', file: 'en.json' },
    ],
    lazy: true,
    // Resolved relative to `i18n/`, so message catalogues live in `i18n/locales/`.
    langDir: 'locales',
    bundle: {
      // The v$translation directive is not used here, and the built-in
      // optimiser is deprecated in @nuxtjs/i18n v10.
      optimizeTranslationDirective: false,
    },
    detectBrowserLanguage: {
      // Do not auto-switch on the first visit: the operator picks the language
      // deliberately, and a wrong auto-detect on a shared warehouse terminal
      // is confusing.
      useCookie: true,
      cookieKey: 'erp_locale',
      redirectOn: 'root',
      alwaysRedirect: false,
    },
  },

  runtimeConfig: {
    // Server-side only. The public block is exposed to the browser bundle.
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1',
    },
  },

  app: {
    head: {
      title: 'ERP-Lite',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
      htmlAttrs: { lang: 'es' },
    },
  },

  typescript: {
    strict: true,
    typeCheck: false,
  },
})