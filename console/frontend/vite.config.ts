/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The backend listens on 127.0.0.1:8765. Proxying /api keeps the browser on one origin,
// so the page never needs the backend's CORS allowance in development.
const API = process.env.CTI_CONSOLE_API ?? "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": API },
  },
  preview: { host: "127.0.0.1", port: 5173, strictPort: true, proxy: { "/api": API } },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
