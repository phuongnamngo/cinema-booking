import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    host: true, // nghe 0.0.0.0 để truy cập được từ ngoài container
    port: 5173,
    // KHÔNG bật changeOrigin: giữ Host = localhost:5173 (xem lý thuyết mục 2)
    proxy: {
      "/api": "http://backend:8000",
      "/mock-gateway": "http://backend:8000",
      "/ws": { target: "ws://backend:8000", ws: true },
    },
  },
  test: { environment: "jsdom" },
});