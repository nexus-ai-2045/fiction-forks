import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const sourceRoot = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root: resolve(sourceRoot),
  base: "./",
  plugins: [react()],
  build: {
    outDir: resolve(sourceRoot, "../workbench"),
    emptyOutDir: true,
  },
});
