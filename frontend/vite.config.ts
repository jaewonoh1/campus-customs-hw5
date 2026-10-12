import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dashboard talks to the FastAPI backend directly at this origin. The
// backend allows this page's origin (localhost:5173) via CORS.
export default defineConfig({
  plugins: [react()],
  // Honor a PORT from the environment (e.g. the preview harness) and fall back to 5173.
  server: { port: Number(process.env.PORT) || 5173 },
});
