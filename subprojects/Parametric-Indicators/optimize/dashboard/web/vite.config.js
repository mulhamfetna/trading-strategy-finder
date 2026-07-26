import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// The control plane serves the built SPA from web/dist as static files mounted at '/'.
// `base: './'` keeps asset URLs relative so it works behind the VPN IP without a fixed host.
// The dev proxy lets `npm run dev` talk to a locally-running control plane on 8350.
export default defineConfig({
  plugins: [vue()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8350', changeOrigin: true },
    },
  },
})
