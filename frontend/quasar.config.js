import { defineConfig } from '#q-app/wrappers'

export default defineConfig((ctx) => {
  return {
    boot: ['pinia', 'axios', 'auth'],
    css: ['app.scss'],
    extras: ['roboto-font', 'material-icons'],

    build: {
      target: { browser: ['es2019', 'edge88', 'firefox78', 'chrome87', 'safari13.1'] },
      vueRouterMode: 'history',
      env: {
        VITE_API_URL: process.env.VITE_API_URL || '',
        VITE_LDAP_ENABLED: process.env.VITE_LDAP_ENABLED || process.env.LDAP_ENABLED || 'true',
      },
    },

    devServer: {
      port: 9000,
      proxy: {
        '/api': {
          target: 'http://localhost:8089',
          changeOrigin: true,
        },
      },
    },

    framework: {
      config: {},
      plugins: ['Notify', 'Dialog', 'Loading'],
    },

    animations: [],

    ssr: { pwa: false, prodPort: 3000, middlewares: ['render'] },
    pwa: {
      workboxMode: 'GenerateSW',
      injectPwaMetaTags: true,
      swFilename: 'sw.js',
      manifestFilename: 'manifest.json',
      useCredentialsForManifestTag: false,
      extendManifestJson (json) {
        json.name = 'Helpdesk Escolar'
        json.short_name = 'Helpdesk'
        json.description = 'Sistema de tickets do Agrupamento de Escolas Eça de Queirós'
        json.display = 'standalone'
        json.orientation = 'portrait'
        json.background_color = '#ffffff'
        json.theme_color = '#1565C0'
        json.start_url = '/'
        json.scope = '/'
        json.lang = 'pt'
        json.icons = [
          { src: 'icons/icon-72x72.png',   sizes: '72x72',   type: 'image/png' },
          { src: 'icons/icon-96x96.png',   sizes: '96x96',   type: 'image/png' },
          { src: 'icons/icon-128x128.png', sizes: '128x128', type: 'image/png' },
          { src: 'icons/icon-144x144.png', sizes: '144x144', type: 'image/png' },
          { src: 'icons/icon-152x152.png', sizes: '152x152', type: 'image/png' },
          { src: 'icons/icon-192x192.png', sizes: '192x192', type: 'image/png', purpose: 'any maskable' },
          { src: 'icons/icon-384x384.png', sizes: '384x384', type: 'image/png' },
          { src: 'icons/icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ]
      },
      extendGenerateSWOptions (cfg) {
        cfg.skipWaiting = true
        cfg.clientsClaim = true
        cfg.runtimeCaching = [
          {
            urlPattern: /^https:\/\/fonts\.(googleapis|gstatic)\.com\/.*/i,
            handler: 'CacheFirst',
            options: { cacheName: 'google-fonts', expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 } },
          },
        ]
      },
    },

    cordova: {},
    capacitor: { hideSplashscreen: true },

    electron: {
      inspectPort: 5858,
      bundler: 'packager',
      packager: {},
      builder: { appId: 'teacher-tickets-ui' },
    },

    bex: { contentScripts: ['my-content-script'] },
  }
})
