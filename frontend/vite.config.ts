import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy: /api -> FastAPI on :8000 (prefix kept, backend is mounted at /api),
// /ws -> WebSocket on :8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/ws": { target: "ws://localhost:8000", ws: true, changeOrigin: true },
    },
  },
  preview: { port: 4173 },
  build: { chunkSizeWarningLimit: 1500 },
});
