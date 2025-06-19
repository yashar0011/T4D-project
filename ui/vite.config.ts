import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "url";

// __dirname is undefined in ESM modules; reconstruct it
const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),          // Tailwind CSS v3 plugin for Vite
  ],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",   // proxy API requests to FastAPI
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"), // allows imports like '@/components/...'
    },
  },
});