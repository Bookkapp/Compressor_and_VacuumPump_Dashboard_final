import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  root: resolve(__dirname),
  plugins: [react()],
  publicDir: "public",
  build: {
    outDir: resolve(__dirname, "../public"),
    emptyOutDir: true,
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom"],
          echarts: ["echarts"],
          icons: ["lucide-react"],
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:5001",
      "/ws": {
        target: "ws://127.0.0.1:5001",
        ws: true,
      },
    },
  },
});
