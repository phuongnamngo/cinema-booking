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
    // Dạng chuỗi của Vite tự bật changeOrigin, Host thành "backend" và trình duyệt không mở được link.
    // Giữ Host gốc (localhost:5173) để Django dựng URL cổng giả lập đúng máy đang mở trang.
    proxy: {
      "/api": { target: "http://backend:8000", changeOrigin: false },
      "/mock-gateway": { target: "http://backend:8000", changeOrigin: false },
      "/ws": { target: "ws://backend:8000", ws: true },
    },
  },
  test: { environment: "jsdom" },
});