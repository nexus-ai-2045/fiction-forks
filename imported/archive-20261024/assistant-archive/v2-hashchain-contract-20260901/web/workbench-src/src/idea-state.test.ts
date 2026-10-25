import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { ideaStateLabels, ideaStates } from "./idea-state";

// Idea Builder は静的HTMLなのでこの型を import できない。
// 型と実画面が黙って食い違わないよう、markup 側を読んで突き合わせる。
// 実行元が repoRoot / workbench-src のどちらでも解決できるようにする。
const ideaBuilderPath = [resolve(process.cwd(), "../index.html"), resolve(process.cwd(), "web/index.html")]
  .find((candidate) => existsSync(candidate));
if (!ideaBuilderPath) throw new Error("Idea Builder の index.html を解決できません");
const ideaBuilderHtml = readFileSync(ideaBuilderPath, "utf8");

describe("idea state vocabulary", () => {
  it("is separate from the wire contract", async () => {
    const wireContract = await import("./run-request");
    expect(Object.keys(wireContract)).not.toContain("IdeaState");
    expect(ideaStates[0]).toBe("draft");
  });

  it("matches the stepper rendered by the static Idea Builder", () => {
    const stepper = ideaBuilderHtml.match(/<ol class="idea-state-steps"[\s\S]*?<\/ol>/)?.[0];
    expect(stepper).toBeTruthy();
    const rendered = Array.from(stepper!.matchAll(/<b>([^<]+)<\/b><span>([^<]+)<\/span>/g));

    // 表示は "human review"、型は "human_review"。順序と語彙の対応だけを固定する。
    expect(rendered.map((match) => match[1].replace(/ /g, "_"))).toEqual([...ideaStates]);
    expect(rendered.map((match) => match[2].replace(/（.*）$/, ""))).toEqual(ideaStates.map((state) => ideaStateLabels[state]));
  });

  it("keeps draft as the only current step, so a posted idea never reads as executed", () => {
    const stepper = ideaBuilderHtml.match(/<ol class="idea-state-steps"[\s\S]*?<\/ol>/)?.[0] ?? "";
    const current = Array.from(stepper.matchAll(/<li aria-current="step"><b>([^<]+)<\/b>/g));
    expect(current).toHaveLength(1);
    expect(current[0][1]).toBe("draft");
  });
});
