import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const API_ORIGIN = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/health": API_ORIGIN,
      "/dashboard": API_ORIGIN,
      "/portfolios": API_ORIGIN,
      "/stocks": API_ORIGIN,
      "/watchlist": API_ORIGIN,
      "/docs": API_ORIGIN,
      "/openapi.json": API_ORIGIN,
    },
  },
});
