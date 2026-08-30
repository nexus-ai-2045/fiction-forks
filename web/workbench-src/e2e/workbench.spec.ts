import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import fixture from "../../../artifacts/runs/haruhi-world-observation-fixture.json" with { type: "json" };

test("Observe → Fork → Stress → Explain", async ({ page }) => {
  await page.goto("./");
  await expect(page.locator('link[rel="stylesheet"]')).toHaveCount(1);
  await expect(page.locator("body")).not.toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  await expect(page.locator('meta[http-equiv="Content-Security-Policy"]')).not.toHaveAttribute(
    "content",
    /unsafe-inline/,
  );
  await expect(page.getByRole("heading", { name: "想像力で、破滅ルートをひっくり返せ。" })).toBeVisible();
  await expect(page.getByText("2032年に発動し、2036年の比較時点で破滅条件を回避。", { exact: true })).toBeVisible();
  await page.getByLabel(/証拠来歴と対立仮説の公開検証手続を5年遅延/).check();
  await expect(page.getByText("発動が2037年となり、2036年の破滅条件に間に合いません。", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /根拠と限界を開く/ }).click();
  await expect(page.getByRole("dialog")).toContainText("FIXTURE / AI実測ではない");
  await expect(page.getByRole("dialog")).toContainText("5f3f88f0908b77962b02e19417a76f95b1ee73ea");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(page.getByRole("button", { name: /根拠と限界を開く/ })).toBeFocused();
});

test("keyboard focus, profile announcement, and dialog containment", async ({ page }) => {
  await page.goto("./");

  await page.keyboard.press("Tab");
  const skipLink = page.getByRole("link", { name: "比較結果へ移動" });
  await expect(skipLink).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#comparison")).toBeFocused();

  const normal = page.getByLabel(/遅延なし/);
  await normal.focus();
  await page.keyboard.press("ArrowDown");
  await expect(page.getByLabel(/証拠来歴と対立仮説の公開検証手続を5年遅延/)).toBeChecked();
  await expect(page.getByText(/発動が2037年となり、2036年の破滅条件に間に合いません/)).toHaveCount(2);

  const summary = page.locator("summary").first();
  await summary.focus();
  await page.keyboard.press("Enter");
  await expect(summary.locator("..")).toHaveAttribute("open", "");

  const trigger = page.getByRole("button", { name: /根拠と限界を開く/ });
  await trigger.focus();
  await page.keyboard.press("Enter");
  const close = page.getByRole("button", { name: "根拠を閉じる" });
  await expect(close).toBeFocused();
  const target = await close.boundingBox();
  expect(target?.width).toBeGreaterThanOrEqual(44);
  expect(target?.height).toBeGreaterThanOrEqual(44);
  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(close).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
});

test("replay steps through stored events with keyboard-operable controls", async ({ page }) => {
  await page.goto("./");

  await expect(page.locator('link[rel="icon"]')).toHaveAttribute("href", /favicon\.svg/);
  await expect(page.getByText("これは検証済みrunのreplayです。いまAIが生成しているのではなく、保存済みeventを保存順のまま表示します。")).toBeVisible();
  await expect(page.getByText("行動 1 / 15", { exact: true })).toBeVisible();

  const first = page.getByRole("button", { name: "最初" });
  const previous = page.getByRole("button", { name: "前へ" });
  const next = page.getByRole("button", { name: "次へ" });
  const play = page.getByRole("button", { name: "自動再生" });
  const stop = page.getByRole("button", { name: "停止" });

  await expect(first).toBeDisabled();
  await expect(previous).toBeDisabled();
  await expect(stop).toBeDisabled();

  await next.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("行動 2 / 15", { exact: true })).toBeVisible();

  await play.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("行動 3 / 15", { exact: true })).toBeVisible({ timeout: 8000 });
  await stop.focus();
  await page.keyboard.press("Enter");
  await expect(play).toBeEnabled();

  await page.getByRole("button", { name: /^行動15:/ }).click();
  await expect(page.getByText("行動 15 / 15", { exact: true })).toBeVisible();
  await expect(next).toBeDisabled();
  await first.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("行動 1 / 15", { exact: true })).toBeVisible();
});

test("mobile live-run table keeps every column header accessible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("./");

  const table = page.getByRole("table", { name: "実モデルの行動一覧" });
  for (const name of ["TURN", "ROLE", "ACTION", "判定"]) {
    await expect(table.getByRole("columnheader", { name })).toHaveCount(1);
  }
});

test("network fixture: exact local adapter response is verified and double submit is blocked", async ({ page }) => {
  let requests = 0;
  await page.route("**/api/health", (route) => route.fulfill({ json: { status: "ready", providers: ["fixture"], worldlines: ["haruhi-world-observation"] } }));
  await page.route("**/api/runs", async (route) => {
    requests += 1;
    await new Promise((resolve) => setTimeout(resolve, 150));
    const runId = fixture.run_id;
    const events = fixture.actions.map((receipt, sequence) => ({ run_id: runId, sequence, payload: { receipt } }));
    const eventStream = Buffer.from(events.map((event) => JSON.stringify(event)).join("\n") + "\n");
    const eventStreamDigest = createHash("sha256").update(eventStream).digest("hex");
    const bundle = {
      schema: "meta-security-run-bundle/v1", run_request: { run_id: runId },
      events,
      replay: { run_id: runId, seed: fixture.seed, event_count: fixture.actions.length, event_stream_sha256: eventStreamDigest },
      evidence: { run_id: runId, event_stream_sha256: eventStreamDigest },
    };
    const resultBytes = Buffer.from(JSON.stringify(fixture));
    const bundleBytes = Buffer.from(JSON.stringify(bundle));
    await route.fulfill({ json: {
      schema_version: "fiction_forks_local_run_response.v1", run_id: runId,
      execution_id: `ffx-${"1".repeat(32)}`, provider: { name: "fixture", model: null },
      source_revision: "2".repeat(40),
      result_sha256: createHash("sha256").update(resultBytes).digest("hex"),
      bundle_sha256: createHash("sha256").update(bundleBytes).digest("hex"),
      result_artifact_base64: resultBytes.toString("base64"),
      bundle_artifact_base64: bundleBytes.toString("base64"),
      event_stream_base64: eventStream.toString("base64"),
      result: fixture,
      bundle,
    } });
  });
  await page.goto("./");
  await page.getByLabel("Session token").fill("test-only-token");
  const run = page.getByRole("button", { name: "シミュレーションを実行" });
  await run.dblclick();
  await expect(page.getByText(/hash-chain PASS \/ bundle PASS/)).toBeVisible();
  expect(requests).toBe(1);
});
