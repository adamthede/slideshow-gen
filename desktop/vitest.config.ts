import { defineConfig } from "vitest/config";
import path from "node:path";

// Vitest reuses the project's path aliases. Pure-logic tests run in the
// default node environment — no jsdom needed (no React rendering here).
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    include: ["src/**/*.test.ts"],
  },
});
