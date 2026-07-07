import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/health": "http://localhost:8000",
      "/upload": "http://localhost:8000",
      "/query": "http://localhost:8000",
      "/search": "http://localhost:8000",
      "/documents": "http://localhost:8000",
      "/document": "http://localhost:8000",
      "/feedback": "http://localhost:8000",
      "/handoff": "http://localhost:8000",
    },
  },
});
