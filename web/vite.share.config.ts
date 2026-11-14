import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Private friend-share instance. Tailscale Serve forwards only tailnet traffic here.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5174,
    strictPort: true,
    allowedHosts: [".ts.net", "localhost", "127.0.0.1"],
    proxy: {
      "/api": { target: "http://127.0.0.1:8001", changeOrigin: true },
    },
  },
});
