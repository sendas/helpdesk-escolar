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
        VITE_API_URL: process.env.VITE_API_URL || 'http://localhost:8089',
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
    pwa: { workboxMode: 'GenerateSW' },

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
