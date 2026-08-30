import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(fileURLToPath(new URL(".", import.meta.url)), "../..");

export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://127.0.0.1:4173/workbench/", trace: "retain-on-failure" },
  webServer: {
    command: "npm run preview",
    cwd: repoRoot,
    url: "http://127.0.0.1:4173/workbench/",
    reuseExistingServer: true,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 5"] } },
  ],
});
