import { expect, test } from "@playwright/test";

test("Observe → Fork → Stress → Explain", async ({ page }) => {
  await page.goto("./");
  await expect(page.getByRole("heading", { name: "分岐する時間軸を読む。" })).toBeVisible();
  await expect(page.getByText("2032年に発動し、このモデルでは破滅条件を回避。")).toBeVisible();
  await page.getByLabel(/異議申立て制度を5年遅延/).check();
  await expect(page.getByText("発動が2037年となり、2036年に間に合いません。")).toBeVisible();
  await page.getByRole("button", { name: /根拠と限界を開く/ }).click();
  await expect(page.getByRole("dialog")).toContainText("FIXTURE / AI実測ではない");
  await expect(page.getByRole("dialog")).toContainText("5f3f88f0908b77962b02e19417a76f95b1ee73ea");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(page.getByRole("button", { name: /根拠と限界を開く/ })).toBeFocused();
});
