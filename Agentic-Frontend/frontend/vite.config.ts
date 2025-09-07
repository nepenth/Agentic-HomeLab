import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  define: {
    // Only expose VITE_ prefixed environment variables for security
    'process.env.VITE_API_BASE_URL': JSON.stringify(process.env.VITE_API_BASE_URL),
    'process.env.VITE_WS_URL': JSON.stringify(process.env.VITE_WS_URL),
    'process.env.VITE_APP_NAME': JSON.stringify(process.env.VITE_APP_NAME),
    'process.env.VITE_APP_VERSION': JSON.stringify(process.env.VITE_APP_VERSION),
  },
})
