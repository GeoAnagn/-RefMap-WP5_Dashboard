
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const host = process.env.HOST || 'localhost';
const port = process.env.PORT ? Number(process.env.PORT) : 4000;

export default defineConfig({
  plugins: [vue()],
  server: {
    host,
    port,
    proxy: {
      '/api/climate_impact': {
        target: `http://${host}:${port + 1}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/climate_impact/, '')
      },
      '/api/wind_assessment': {
        target: `http://${host}:${port + 2}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/wind_assessment/, '')
      },
      '/api/noise_assessment': {
        target: `http://${host}:${port + 3}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/noise_assessment/, '')
      },
      '/api/optimized_trajectories': {
        target: `http://${host}:${port + 4}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/optimized_trajectories/, '')
      },
      '/api/emissions': {
        target: `http://${host}:${port + 5}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/emissions/, '')
      },
      '/api/atmospheric_pollution': {
        target: `http://${host}:${port + 6}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/atmospheric_pollution/, '')
      }
    }
  }
})
