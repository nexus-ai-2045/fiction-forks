/**
 * Idea Builder → シミュレーション実行API (Web実行アダプター / 残務#5) の要求契約。
 *
 * 実行APIは未確定のため、この file は型と状態遷移の宣言だけを持つ。
 * UI側 (web/app.js の #run-request-status) は pending / error のみを描画し、
 * running / verified を実APIの応答なしに表示してはならない。
 * 実装側がこの契約を変更する場合は、この file を更新して UI と同じ commit で合わせる。
 */

/** アイデアの公開状態。draft から順にしか進まない。 */
export type IdeaState = "draft" | "human_review" | "simulator_run" | "verified_artifact";

/** UI が描画してよい実行要求の状態。verified は verified な artifact の提示が必須。 */
export type RunRequestStatus =
  | { kind: "pending"; reason: "api_not_connected" | "queued" }
  | { kind: "running"; run_id: string; started_at_iso: string }
  | { kind: "error"; message: string; retryable: boolean }
  | { kind: "verified"; receipt: RunReceipt };

/** Idea Builder が実行APIへ送る要求。自由数値は持たず、named profile だけを指す。 */
export interface RunRequest {
  schema_version: "fiction_forks_run_request.v1";
  /** 対象の Idea Issue URL (https://github.com/nexus-ai-2045/fiction-forks/issues/N)。 */
  issue_url: string;
  /** 実装済み intervention の id。未実装アイデアでは実行を要求できない。 */
  intervention_id: string;
  scenario_id: string;
  seed: number;
  /** 検証済み遅延条件 (named profile) の id。自由入力は不可。 */
  named_profile_id: string | null;
}

/** 実行APIが返すべき受領証。UIはこの値を加工せず表示する。 */
export interface RunReceipt {
  schema_version: "fiction_forks_run_receipt.v1";
  run_id: string;
  run_kind: "fixture" | "live";
  result_sha256: string;
  event_stream_sha256: string;
  replay_verified: boolean;
  bundle_contract_verified: boolean;
  /** 生成された比較artifactへの repo 内パス。 */
  artifact_paths: string[];
}
