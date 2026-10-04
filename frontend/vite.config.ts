import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command, mode }) => {
  // Without this a deployed build silently calls http://localhost:8000.
  if (command === "build" && !loadEnv(mode, process.cwd(), "VITE_").VITE_API_BASE_URL) {
    throw new Error("VITE_API_BASE_URL must be set for production builds.");
  }

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "src"),
      },
    },
    server: {
      port: 5173,
      host: true,
      watch: {
        // Needed for reliable HMR when the project lives on a bind-mounted volume.
        usePolling: true,
      },
    },
  };
});
