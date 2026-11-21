import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// SPA раздаётся backend'ом с того же домена; в разработке /api проксируется на uvicorn.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
  build: {
    outDir: 'dist',
    // CSP backend'а разрешает шрифты и картинки только с 'self' — не инлайним ассеты в data:.
    assetsInlineLimit: 0,
    sourcemap: false,
    target: 'es2020',
  },
});
