/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The backend listens on 127.0.0.1:8765. Proxying /api keeps the browser on one origin,
// so the page never needs the backend's CORS allowance in development.
const API = process.env.CTI_CONSOLE_API ?? "http://127.0.0.1:8765";
const HOST = "127.0.0.1";
const PORT = 5173;

// The reader shows HTML made from documents full of web links, so the page may load
// nothing from anywhere but itself: no remote scripts, styles, images or connections.
// Images are allowed as data: URIs because mammoth embeds a document's pictures that way.
const policy = (dev: boolean): string =>
  [
    "default-src 'self'",
    // Vite's dev server injects an inline React refresh script and inline styles, and
    // talks to the page over a websocket. The built page needs none of that.
    dev ? "script-src 'self' 'unsafe-inline'" : "script-src 'self'",
    dev ? "style-src 'self' 'unsafe-inline'" : "style-src 'self'",
    dev ? `connect-src 'self' ws://${HOST}:${PORT}` : "connect-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    // The reader frames the branded PDF from its own origin. Chrome shows a framed PDF
    // without plugin rights, so object-src stays 'none' (checked in Chrome).
    "frame-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'none'",
  ].join("; ");

const headers = (dev: boolean) => ({
  "Content-Security-Policy": policy(dev),
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
});

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { host: HOST, port: PORT, strictPort: true, headers: headers(true), proxy: { "/api": API } },
  preview: {
    host: HOST,
    port: PORT,
    strictPort: true,
    headers: headers(false),
    proxy: { "/api": API },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
