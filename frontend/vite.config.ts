import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(),tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'https://youtubenotebooks.onrender.com', // Backend server URL
        changeOrigin: true,
        secure: false,
        // *** THIS IS THE KEY CHANGE ***
        rewrite: (path) => path.replace(/^\/api/, ''), // Removes '/api' from the start of the path
      },
    },
  },
})
