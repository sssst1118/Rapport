import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Rapport 前端构建配置
// - tailwindcss(): Tailwind v4 的 Vite 插件（CSS-first，主题写在 styles/tokens.css 的 @theme 里）
// - proxy: 开发时把 /api 透传给本机 8000 端口上的 FastAPI 后端
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 后端会托管这一目录
    outDir: 'dist',
  },
})
