import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

export default defineConfig({
  root: resolve(fileURLToPath(new URL(".", import.meta.url))),
  plugins: [react()],
  test: { globals: true, environment: "jsdom", setupFiles: "./src/test-setup.ts", include: ["src/**/*.test.{ts,tsx}"] },
});
