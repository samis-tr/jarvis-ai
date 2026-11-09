import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// In dev (npm run dev) API calls are proxied to the Python backend started with --server.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8765",
      "/ws": { target: "ws://127.0.0.1:8765", ws: true },
    },
  },
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 900 },
});
