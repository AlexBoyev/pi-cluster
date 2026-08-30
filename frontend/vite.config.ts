import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// BACKEND_URL defaults to localhost for running outside Docker.
// docker-compose sets it to http://backend:8000 via the environment block.
const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: [".pi-cluster.lan"],
    proxy: {
      "/api": {
        target: backendUrl,
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
