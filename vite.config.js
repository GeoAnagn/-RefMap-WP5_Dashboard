import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '147.102.37.172',
    port: 4000,
    proxy: {
      '/api/climate_impact': {
        target: 'http://147.102.37.172:4001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/climate_impact/, '')
      },
      '/api/wind_assessment': {
        target: 'http://147.102.37.172:4002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/wind_assessment/, '')
      },
      '/api/noise_assessment': {
        target: 'http://147.102.37.172:4003',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/noise_assessment/, '')
      },
      '/api/optimized_trajectories': {
        target: 'http://147.102.37.172:4004',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/optimized_trajectories/, '')
      },
      '/api/emissions': {
        target: 'http://147.102.37.172:4005',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/emissions/, '')
      }
    }
  }
})
