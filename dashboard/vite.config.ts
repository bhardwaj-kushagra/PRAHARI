/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" so the static build works from any folder or static host (SPEC §6.1, P8).
export default defineConfig({
  base: "./",
  plugins: [react()],
  test: { environment: "node" },
});
