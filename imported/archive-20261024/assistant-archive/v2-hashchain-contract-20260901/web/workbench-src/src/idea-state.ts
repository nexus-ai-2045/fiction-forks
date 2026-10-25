/**
 * Idea Builder（`web/index.html` の静的ページ）が表示するアイデアの状態。
 *
 * wire contract (`run-request.ts`) とは別物。adapterのrequest/responseには現れず、
 * 人間のレビュー工程を表すUI語彙でしかない。同じfileに置くと
 * 「実行APIがdraft状態を返す」と読めてしまうため分離している。
 *
 * 静的ページ側のステッパー表記と、この並び順を一致させること。
 */
export const ideaStates = ["draft", "human_review", "simulator_run", "verified_artifact"] as const;

export type IdeaState = (typeof ideaStates)[number];

export const ideaStateLabels: Record<IdeaState, string> = {
  draft: "下書き",
  human_review: "人間レビュー",
  simulator_run: "シミュレーター実行",
  verified_artifact: "検証済みartifact",
};
