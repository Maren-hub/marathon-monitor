import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteStaticCopy } from 'vite-plugin-static-copy'

const cesiumBuild = 'node_modules/cesium/Build/Cesium'

export default defineConfig({
  plugins: [
    vue(),
    viteStaticCopy({
      targets: [
        { src: `${cesiumBuild}/Workers`, dest: 'cesium' },
        { src: `${cesiumBuild}/Assets`, dest: 'cesium' },
        { src: `${cesiumBuild}/ThirdParty`, dest: 'cesium' },
        { src: `${cesiumBuild}/Widgets`, dest: 'cesium' }
      ]
    })
  ],
  define: {
    CESIUM_BASE_URL: JSON.stringify('/cesium')
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: ['.trycloudflare.com'],
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true
      }
    }
  }
})
