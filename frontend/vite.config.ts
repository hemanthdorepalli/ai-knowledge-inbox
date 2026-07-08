import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API base is read at runtime from VITE_API_BASE (see .env.example).
// We deliberately keep frontend and backend as separate origins and rely on
// CORS rather than a dev proxy, so the same build works when the API is
// deployed elsewhere.
export default defineConfig({
  plugins: [react()],
  server: {
    // Honor a PORT env var (used by the preview tooling); default to 5173.
    port: Number(process.env.PORT) || 5173,
  },
});
