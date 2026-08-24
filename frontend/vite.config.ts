import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  optimizeDeps: {
    include: [
      "cytoscape",
      "cytoscape-fcose",
      "cytoscape-cola",
      "cytoscape-cose-bilkent",
      "leaflet",
      "recharts",
      "sigma",
      "graphology",
      "graphology-layout-forceatlas2",
    ],
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test-setup.ts",
    exclude: ["**/node_modules/**", "**/tests/e2e/**", "**/e2e/**", "**/playwright.config.*"],
    testTimeout: 20000,
    hookTimeout: 20000,
  },
  build: {
    target: "es2022",
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          sigma: ["sigma", "graphology", "graphology-layout-forceatlas2"],
        },
      },
    },
  },
});
