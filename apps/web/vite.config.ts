import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const API = process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    // один origin для браузера: cookie, CSRF и WebSocket работают без CORS
    proxy: { "/api": { target: API, changeOrigin: false, ws: true } },
  },
  preview: { proxy: { "/api": { target: API, changeOrigin: false, ws: true } } },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
