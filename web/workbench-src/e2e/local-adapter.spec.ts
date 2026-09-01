import { expect, test } from "@playwright/test";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(fileURLToPath(new URL(".", import.meta.url)), "../../..");

async function startAdapter(origin: string): Promise<{ child: ChildProcessWithoutNullStreams; token: string }> {
  const child = spawn(
    process.env.PYTHON ?? "python",
    ["-u", "-m", "fiction_forks.local_adapter", "--repo-root", ".", "--origin", origin],
    {
      cwd: repoRoot,
      env: { ...process.env, PYTHONPATH: resolve(repoRoot, "src") },
      windowsHide: true,
    },
  );
  const token = await new Promise<string>((resolveToken, reject) => {
    let output = "";
    const timeout = setTimeout(() => reject(new Error(`local adapter did not become ready: ${output}`)), 10_000);
    const read = (chunk: Buffer) => {
      output += chunk.toString("utf8");
      const match = output.match(/X-Fiction-Forks-Session: ([A-Za-z0-9_-]+)/);
      if (match) {
        clearTimeout(timeout);
        resolveToken(match[1]);
      }
    };
    child.stdout.on("data", read);
    child.stderr.on("data", read);
    child.once("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error(`local adapter exited before readiness (${code}): ${output}`));
    });
  });
  return { child, token };
}

test("real adapter: execute fixture, verify evidence, and replay generated events", async ({ page, isMobile }, testInfo) => {
  test.skip(isMobile, "実adapterはdesktopで一度だけ実行する");
  test.setTimeout(90_000);
  const baseURL = String(testInfo.project.use.baseURL);
  const { child, token } = await startAdapter(new URL(baseURL).origin);
  try {
    await page.goto("./");
    // 既定templateは明示固定なので、選択せずに押しても15行動の世界線になる。
    await expect(page.getByLabel("世界線template")).toHaveValue("contested-world-observation.v1");
    await page.getByLabel("Session token").fill(token);
    await page.getByRole("button", { name: "シミュレーションを実行" }).click();

    const result = page.locator(".local-run .run-success");
    const alert = page.locator(".local-run [role=alert]");
    await expect(result.or(alert)).toBeVisible({ timeout: 60_000 });
    if (await alert.isVisible()) throw new Error(`local adapter UI error: ${await alert.innerText()}`);
    await expect(result).toContainText("15 events / hash-chain PASS / bundle PASS");
    await expect(result).toContainText(/run_id ff-[0-9a-f]{16}/);
    await expect(result).toContainText(/execution_id ffx-[0-9a-f]{32}/);

    const replay = page.locator(".local-run .replay");
    await expect(replay.getByRole("heading", { name: "いま実行した15行動を、一手ずつ再生する。" })).toBeVisible();
    await expect(replay.getByText("行動 1 / 15", { exact: true })).toBeVisible();
    await replay.getByRole("button", { name: "次へ" }).click();
    await expect(replay.getByText("行動 2 / 15", { exact: true })).toBeVisible();
    await replay.getByRole("button", { name: /^行動15:/ }).click();
    await expect(replay.getByText("行動 15 / 15", { exact: true })).toBeVisible();
  } finally {
    child.kill();
  }
});
