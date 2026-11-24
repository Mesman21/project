import { defineConfig } from "vite";
import { mockApi } from "./mock-api.js";

export default defineConfig(({ mode }) => ({
  plugins: mode === "mock" ? [mockApi()] : [],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: mode === "mock" ? undefined : { "/api": "http://127.0.0.1:8000" },
  },
}));
