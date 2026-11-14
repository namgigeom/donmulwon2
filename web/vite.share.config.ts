import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Public friend-share instance exposed through a Cloudflare Quick Tunnel.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5174,
    strictPort: true,
    allowedHosts: [".trycloudflare.com", "localhost", "127.0.0.1"],
    proxy: {
      "/api": { target: "http://127.0.0.1:8001", changeOrigin: true },
    },
  },
});
