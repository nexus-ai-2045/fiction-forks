import { parseReplayRun } from "./contract";
import type { ReplayRun } from "./types";

export type IdeaState = "draft" | "human_review" | "simulator_run" | "verified_artifact";
export type LocalProvider = "fixture" | "ollama" | "vertex";

export interface LocalRunRequest {
  schema_version: "fiction_forks_local_run_request.v1";
  worldline_id: "haruhi-world-observation";
  provider: LocalProvider;
  seed: number;
  confirm_live: boolean;
}

export interface VerifiedLocalRun {
  schema_version: "fiction_forks_local_run_response.v1";
  run_id: string;
  execution_id: string;
  provider: { name: LocalProvider; model: string | null };
  source_revision: string;
  result_sha256: string;
  bundle_sha256: string;
  result: Record<string, unknown>;
  replay: ReplayRun;
  bundle: Record<string, unknown>;
}

const sha256Pattern = /^[0-9a-f]{64}$/;
const commitPattern = /^[0-9a-f]{40}$/;

function record(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) throw new Error(`${label}が不正です`);
  return value as Record<string, unknown>;
}

function exactKeys(value: Record<string, unknown>, keys: string[], label: string): void {
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) throw new Error(`${label}の項目が契約と一致しません`);
}

function stableJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (typeof value === "object" && value !== null) {
    const item = value as Record<string, unknown>;
    return `{${Object.keys(item).sort().map((key) => `${JSON.stringify(key)}:${stableJson(item[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function buildLocalRunRequest(provider: LocalProvider, seed: number, confirmed: boolean): LocalRunRequest {
  if (!Number.isInteger(seed) || seed < 0 || seed > 2 ** 31 - 1) throw new Error("seedが範囲外です");
  if (provider === "fixture" && confirmed) throw new Error("fixtureはlive確認を要求しません");
  if (provider !== "fixture" && !confirmed) throw new Error("外部AI実行には明示確認が必要です");
  return { schema_version: "fiction_forks_local_run_request.v1", worldline_id: "haruhi-world-observation", provider, seed, confirm_live: provider !== "fixture" };
}

export async function parseLocalRunResponse(value: unknown): Promise<VerifiedLocalRun> {
  const response = record(value, "response");
  exactKeys(response, ["schema_version", "run_id", "execution_id", "provider", "source_revision", "result_sha256", "bundle_sha256", "result", "bundle"], "response");
  if (response.schema_version !== "fiction_forks_local_run_response.v1") throw new Error("未対応のresponse schemaです");
  if (typeof response.run_id !== "string" || !response.run_id.startsWith("ff-")) throw new Error("run_idが不正です");
  if (typeof response.execution_id !== "string" || !/^ffx-[0-9a-f]{32}$/.test(response.execution_id)) throw new Error("execution_idが不正です");
  if (typeof response.source_revision !== "string" || !commitPattern.test(response.source_revision)) throw new Error("source revisionが不正です");
  for (const key of ["result_sha256", "bundle_sha256"] as const) if (typeof response[key] !== "string" || !sha256Pattern.test(response[key])) throw new Error(`${key}が不正です`);
  const provider = record(response.provider, "provider");
  exactKeys(provider, ["name", "model"], "provider");
  if (!(["fixture", "ollama", "vertex"] as unknown[]).includes(provider.name) || (provider.model !== null && typeof provider.model !== "string")) throw new Error("providerが不正です");

  const result = record(response.result, "result");
  if (result.run_id !== response.run_id) throw new Error("resultのrun_idが一致しません");
  const replay = await parseReplayRun(result);
  const bundle = record(response.bundle, "bundle");
  if (bundle.schema !== "meta-security-run-bundle/v1") throw new Error("bundle schemaが不正です");
  const runRequest = record(bundle.run_request, "bundle.run_request");
  const bundleReplay = record(bundle.replay, "bundle.replay");
  const evidence = record(bundle.evidence, "bundle.evidence");
  for (const [label, part] of [["run_request", runRequest], ["replay", bundleReplay], ["evidence", evidence]] as const) if (part.run_id !== response.run_id) throw new Error(`bundle.${label}のrun_idが一致しません`);
  if (!Array.isArray(bundle.events) || bundle.events.length !== replay.events.length) throw new Error("bundle event数が一致しません");
  const actions = result.actions;
  if (!Array.isArray(actions)) throw new Error("result actionsが不正です");
  bundle.events.forEach((raw, index) => {
    const event = record(raw, `bundle.events[${index}]`);
    if (event.run_id !== response.run_id || event.sequence !== index) throw new Error("bundle event順序が不正です");
    const payload = record(event.payload, `bundle.events[${index}].payload`);
    if (stableJson(payload.receipt) !== stableJson(actions[index])) throw new Error("bundle eventとresult actionが一致しません");
  });
  if (bundleReplay.event_count !== replay.events.length || bundleReplay.seed !== replay.seed) throw new Error("bundle replayの件数またはseedが一致しません");
  return { ...response, provider, result, replay, bundle } as VerifiedLocalRun;
}

export async function requestLocalRun(request: LocalRunRequest, sessionToken: string): Promise<VerifiedLocalRun> {
  if (!sessionToken) throw new Error("adapter起動時に表示されたsession tokenを入力してください");
  const response = await fetch("/api/runs", { method: "POST", headers: { "Content-Type": "application/json", "X-Fiction-Forks-Session": sessionToken }, body: JSON.stringify(request) });
  if (!response.ok) {
    const messages: Record<number, string> = { 400: "実行要求またはprovider設定が契約と一致しません。", 403: "session token、origin、または実行許可を確認してください。", 413: "実行要求が大きすぎます。", 415: "実行要求の形式が不正です。" };
    throw new Error(messages[response.status] ?? "シミュレーターへ接続できませんでした。");
  }
  return parseLocalRunResponse(await response.json());
}
