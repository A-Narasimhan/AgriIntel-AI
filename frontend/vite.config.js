import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/advisory': 'http://localhost:8000',
      '/retrieve': 'http://localhost:8000',
      '/weather': 'http://localhost:8000',
      '/crops': 'http://localhost:8000',
      '/interactions': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})
