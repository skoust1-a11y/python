import { defineConfig } from "vite";

const api = process.env.API_PROXY || "http://127.0.0.1:8000";

export default defineConfig({
  esbuild: { jsx: "automatic" },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: api, changeOrigin: true },
      "/health": { target: api, changeOrigin: true },
      "/admin": { target: api, changeOrigin: true },
    },
  },
});
