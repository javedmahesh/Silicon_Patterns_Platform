import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

// The FastAPI backend serves routes at the root (/companies, /leads, ...). In dev
// we proxy /api -> http://127.0.0.1:8000 and strip the /api prefix, so the app can
// call `/api/companies` and avoid CORS. In prod, set VITE_API_BASE_URL to the API origin.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    // Polling watcher — reliable HMR on Windows / networked filesystems.
    watch: { usePolling: true, interval: 300 },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
