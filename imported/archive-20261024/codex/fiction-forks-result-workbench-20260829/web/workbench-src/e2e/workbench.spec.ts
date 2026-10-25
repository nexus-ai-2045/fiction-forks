import { expect, test } from "@playwright/test";

test("Observe → Fork → Stress → Explain", async ({ page }, testInfo) => {
  await page.goto("./");
  await expect(page.getByRole("heading", { name: "分岐する時間軸を読む。" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "同じ2036年、二つの世界" })).toBeVisible();
  if (testInfo.project.name === "mobile") {
    await expect(page.getByRole("columnheader")).toHaveCount(4);
    const headerDisplay = await page.locator(".metric-head").evaluate((element) => getComputedStyle(element).display);
    expect(headerDisplay).not.toBe("none");
  }
  const avoidedColor = await page
    .locator(".fork-world .state-mark.is-avoided")
    .evaluate((element) => getComputedStyle(element).color);
  expect(avoidedColor).toBe("rgb(5, 118, 109)");
  await expect(page.getByText("2032年に発動し、2036年の比較時点で破滅条件を回避。")).toBeVisible();
  await page.getByLabel(/異議申立て制度を5年遅延/).check();
  await expect(page.getByText("発動が2037年となり、2036年の破滅条件に間に合いません。")).toBeVisible();
  await page.getByRole("button", { name: /根拠と限界を開く/ }).click();
  await expect(page.getByRole("dialog")).toContainText("FIXTURE / AI実測ではない");
  await expect(page.getByRole("dialog")).toContainText("5f3f88f0908b77962b02e19417a76f95b1ee73ea");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(page.getByRole("button", { name: /根拠と限界を開く/ })).toBeFocused();
  const focusOutline = await page
    .getByRole("button", { name: /根拠と限界を開く/ })
    .evaluate((element) => getComputedStyle(element).outlineColor);
  expect(focusOutline).toBe("rgb(18, 37, 35)");
});
