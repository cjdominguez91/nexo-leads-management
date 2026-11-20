import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: true,
    port: 5173,
    // Vite rechaza por defecto cualquier Host desconocido (protección
    // anti DNS-rebinding). Sin esto, acceder por un túnel (VS Code Ports /
    // GitHub Codespaces) responde "Blocked request. This host is not allowed".
    allowedHosts: true,
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
})
