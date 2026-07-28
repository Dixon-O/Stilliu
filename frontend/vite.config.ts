import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// Where the FastAPI backend lives.
//   • Native (Windows/macOS/Linux): defaults to localhost:8000.
//   • Docker Compose: set VITE_API_TARGET=http://backend:8000 so the dev server
//     proxies to the backend *service* rather than to its own container.
const API_TARGET = process.env.VITE_API_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    // Bind 0.0.0.0 so the port is reachable from outside a container.
    // Harmless natively — it just also answers on your LAN address.
    host: true,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/health': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
    watch: {
      // Bind-mounted volumes on Windows and macOS don't deliver inotify events
      // into the container, so HMR silently stops working. Polling is slower but
      // actually fires. Only enabled when running under Compose.
      usePolling: process.env.VITE_USE_POLLING === 'true',
    },
  },
})
