import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const sourceRoot = fileURLToPath(new URL(".", import.meta.url));
const publicRoot = resolve(sourceRoot, "..");

export default defineConfig(({ isPreview }) => ({
  root: isPreview ? publicRoot : resolve(sourceRoot),
  base: "./",
  plugins: [
    {
      name: "fiction-forks-development-csp",
      apply: "serve",
      transformIndexHtml(html) {
        // Vite's development runtime injects component styles into a <style>
        // element. Keep the published build strict while allowing that one
        // development-only mechanism on the loopback server.
        return isPreview
          ? html
          : html.replace("style-src 'self'", "style-src 'self' 'unsafe-inline'");
      },
    },
    react(),
  ],
  build: {
    outDir: isPreview ? publicRoot : resolve(publicRoot, "workbench"),
    emptyOutDir: true,
  },
}));
