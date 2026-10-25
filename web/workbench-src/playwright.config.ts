import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(fileURLToPath(new URL(".", import.meta.url)), "../..");

const port = Number(process.env.FF_WEB_PORT ?? 4173);
const baseURL = `http://127.0.0.1:${port}/workbench/`;

export default defineConfig({
  testDir: "./e2e",
  use: { baseURL, trace: "retain-on-failure" },
  webServer: {
    command: `npm run build && npx vite preview --config web/workbench-src/vite.config.ts --host 127.0.0.1 --port ${port} --strictPort`,
    cwd: repoRoot,
    url: baseURL,
    reuseExistingServer: false,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 5"] } },
  ],
});
