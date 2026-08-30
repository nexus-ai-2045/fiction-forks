import { expect, test } from "@playwright/test";

// Idea Builderはworkbenchの一つ上の階層で配信される静的ページ。
test.beforeEach(async ({ page }) => {
  await page.goto("../");
});

test("says up front that writing an idea is enough", async ({ page }) => {
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute("href", /favicon\.svg/);
  await expect(page.getByText("アイデアを書くだけでOK。")).toBeVisible();
  await expect(page.getByText(/実装と検証は、AIとcontributor（実装協力者）が引き受けます/)).toBeVisible();
});

test("a drafted idea stays in draft state and never claims execution", async ({ page }) => {
  await page.getByRole("textbox", { name: "作品名 必須" }).fill("ドラえもん");
  await page.getByRole("textbox", { name: "アイデア 必須" }).fill("どこでもドアのように、災害時でも離れた地域へ医療や物資を届けられる仕組み");
  await page.getByText("画像、台詞、ロゴ、音声、キャラクターの口調・外見の再現を入力していません。").click();
  await page.getByText("個人情報、秘密情報、実在システムへの攻撃手順を入力していません。").click();
  await page.getByRole("button", { name: /Issueを確認/ }).click();

  const steps = page.getByRole("list", { name: "このアイデアの現在の状態" }).getByRole("listitem");
  await expect(steps).toHaveCount(4);
  await expect(steps.nth(0)).toHaveAttribute("aria-current", "step");
  for (const index of [1, 2, 3]) {
    await expect(steps.nth(index)).not.toHaveAttribute("aria-current", "step");
  }
  await expect(page.getByText(/状態は「下書き」のままで、実装済み・実行済みにはなりません/)).toBeVisible();

  const runStatus = page.locator("#run-request-status");
  await expect(runStatus).toHaveAttribute("data-state", "pending");
  await expect(runStatus).toHaveText(/シミュレーション実行APIは準備中です/);
});

test("explains Issue / PR / fork vocabulary for first-time visitors", async ({ page }) => {
  const guide = page.locator(".term-guide");
  await guide.locator("summary").click();
  await expect(guide.getByText("Issue（イシュー）")).toBeVisible();
  await expect(guide.getByText("PR（Pull Request）")).toBeVisible();
  await expect(guide.getByText("fork（フォーク）")).toBeVisible();
  await expect(guide.getByText(/1つのPR = 1つの世界線/)).toBeVisible();
});
