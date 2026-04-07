import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// Ports chosen to avoid clashing with other local apps on 8000 / 5173.
// Default the dev proxy to 8002 because 8001 is currently polluted by stale
// FastAPI reload listeners on this machine.
const API_PORT = process.env.VITE_PROXY_API_PORT ?? '8002'

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.VITE_DEV_PORT ?? 5174),
    strictPort: true,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${API_PORT}`,
        changeOrigin: true,
        configure(proxy) {
          proxy.on('error', (err) => {
            console.error(
              `\n[vite] /api proxy -> 127.0.0.1:${API_PORT} failed (${err.message}).`,
              `Is the FastAPI app running on that port?`,
              `(override with VITE_PROXY_API_PORT)\n`,
            )
          })
        },
      },
    },
  },
})
