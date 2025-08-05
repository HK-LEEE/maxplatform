import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Load environment variables
  const env = process.env;
  const apiBaseUrl = env.VITE_API_BASE_URL;
  
  return {
    plugins: [react()],
    server: {
      port: 3000,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: apiBaseUrl,
          changeOrigin: true
        },
        '/admin': {
          target: apiBaseUrl,
          changeOrigin: true
        }
      }
    },
    build: {
      outDir: 'dist',
      sourcemap: true
    }
  }
}) 