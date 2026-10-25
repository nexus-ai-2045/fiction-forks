import { parseReplayRun } from "./contract";
import type { ReplayRun } from "./types";

export type IdeaState = "draft" | "human_review" | "simulator_run" | "verified_artifact";
export type LocalProvider = "fixture" | "ollama" | "vertex";

export const DEFAULT_TEMPLATE_ID = "contested-world-observation.v1";
export const LOCAL_DELAY_PROFILE = "none";

export interface LocalRunTemplate {
  template_id: string;
  template_version: number;
  scenario_id: string;
  intervention_id: string;
  intervention_sha256: string;
  abstract_function: string;
  allowed_seeds: number[];
  delay_profiles: string[];
}

export interface LocalRunCatalog {
  catalog_id: string;
  catalog_version: number;
  providers: string[];
  templates: LocalRunTemplate[];
}

export interface ProvisionalRunRequest {
  schema_version: "fiction_forks_provisional_run_request.v1";
  scenario_id: string;
  template_id: string;
  template_version: number;
  catalog_id: string;
  catalog_version: number;
  intervention_id: string;
  intervention_sha256: string;
  seed: number;
  delay_profile: string;
  user_confirmed: true;
}

export interface LocalRunRequest {
  schema_version: "fiction_forks_local_run_request.v2";
  run_request: ProvisionalRunRequest;
  execution: { provider_id: LocalProvider; confirm_live: boolean };
}

export interface VerifiedLocalRun {
  schema_version: "fiction_forks_local_run_response.v1";
  run_id: string;
  execution_id: string;
  provider: { name: LocalProvider; model: string | null };
  source_revision: string;
  result_sha256: string;
  bundle_sha256: string;
  result_artifact_base64: string;
  bundle_artifact_base64: string;
  event_stream_base64: string;
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

function decodeBase64(value: unknown, label: string): Uint8Array {
  if (typeof value !== "string" || !/^[A-Za-z0-9+/]*={0,2}$/.test(value)) throw new Error(`${label}が不正です`);
  let decoded: string;
  try {
    decoded = atob(value);
  } catch {
    throw new Error(`${label}が不正です`);
  }
  return Uint8Array.from(decoded, (character) => character.charCodeAt(0));
}

async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes as BufferSource);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function verifiedArtifact(value: unknown, expectedDigest: unknown, label: string): Promise<unknown> {
  const bytes = decodeBase64(value, `${label} artifact`);
  if (typeof expectedDigest !== "string" || await sha256Hex(bytes) !== expectedDigest) throw new Error(`${label} artifact SHA-256が一致しません`);
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch {
    throw new Error(`${label} artifact JSONが不正です`);
  }
}

function template(value: unknown, label: string): LocalRunTemplate {
  const item = record(value, label);
  exactKeys(item, ["template_id", "template_version", "scenario_id", "intervention_id", "intervention_sha256", "abstract_function", "allowed_seeds", "delay_profiles"], label);
  for (const key of ["template_id", "scenario_id", "intervention_id", "abstract_function"] as const) if (typeof item[key] !== "string" || !item[key]) throw new Error(`${label}の${key}が不正です`);
  const version = item.template_version;
  const digest = item.intervention_sha256;
  const seeds = item.allowed_seeds;
  const profiles = item.delay_profiles;
  if (typeof version !== "number" || !Number.isInteger(version) || version < 1) throw new Error(`${label}のtemplate_versionが不正です`);
  if (typeof digest !== "string" || !sha256Pattern.test(digest)) throw new Error(`${label}のintervention_sha256が不正です`);
  if (!Array.isArray(seeds) || seeds.length === 0 || !seeds.every((seed) => typeof seed === "number" && Number.isInteger(seed))) throw new Error(`${label}のallowed_seedsが不正です`);
  if (!Array.isArray(profiles) || profiles.length === 0 || !profiles.every((profile) => typeof profile === "string")) throw new Error(`${label}のdelay_profilesが不正です`);
  return item as unknown as LocalRunTemplate;
}

export function parseLocalRunCatalog(value: unknown): LocalRunCatalog {
  const health = record(value, "health");
  const { status, providers, catalog_id: catalogId, catalog_version: catalogVersion, templates } = health;
  if (status !== "ready") throw new Error("adapterがreadyではありません");
  if (!Array.isArray(providers) || !providers.includes("fixture")) throw new Error("providersが不正です");
  if (typeof catalogId !== "string" || !catalogId) throw new Error("catalog_idが不正です");
  if (typeof catalogVersion !== "number" || !Number.isInteger(catalogVersion) || catalogVersion < 1) throw new Error("catalog_versionが不正です");
  if (!Array.isArray(templates) || templates.length === 0) throw new Error("preview可能なtemplateがありません");
  return {
    catalog_id: catalogId,
    catalog_version: catalogVersion,
    providers: providers.filter((item): item is string => typeof item === "string"),
    templates: templates.map((item, index) => template(item, `templates[${index}]`)),
  };
}

export function buildLocalRunRequest(catalog: LocalRunCatalog, selected: LocalRunTemplate, provider: LocalProvider, seed: number, confirmed: boolean): LocalRunRequest {
  if (!selected.allowed_seeds.includes(seed)) throw new Error("catalogで許可されたseedを選択してください");
  if (!selected.delay_profiles.includes(LOCAL_DELAY_PROFILE)) throw new Error("local transportはこのdelay profileを実行できません");
  if (provider === "fixture" && confirmed) throw new Error("fixtureはlive確認を要求しません");
  if (provider !== "fixture" && !confirmed) throw new Error("外部AI実行には明示確認が必要です");
  return {
    schema_version: "fiction_forks_local_run_request.v2",
    run_request: {
      schema_version: "fiction_forks_provisional_run_request.v1",
      scenario_id: selected.scenario_id,
      template_id: selected.template_id,
      template_version: selected.template_version,
      catalog_id: catalog.catalog_id,
      catalog_version: catalog.catalog_version,
      intervention_id: selected.intervention_id,
      intervention_sha256: selected.intervention_sha256,
      seed,
      delay_profile: LOCAL_DELAY_PROFILE,
      user_confirmed: true,
    },
    execution: { provider_id: provider, confirm_live: provider !== "fixture" },
  };
}

export async function parseLocalRunResponse(value: unknown): Promise<VerifiedLocalRun> {
  const response = record(value, "response");
  exactKeys(response, ["schema_version", "run_id", "execution_id", "provider", "source_revision", "result_sha256", "bundle_sha256", "result_artifact_base64", "bundle_artifact_base64", "event_stream_base64", "result", "bundle"], "response");
  if (response.schema_version !== "fiction_forks_local_run_response.v1") throw new Error("未対応のresponse schemaです");
  if (typeof response.run_id !== "string" || !response.run_id.startsWith("ff-")) throw new Error("run_idが不正です");
  if (typeof response.execution_id !== "string" || !/^ffx-[0-9a-f]{32}$/.test(response.execution_id)) throw new Error("execution_idが不正です");
  if (typeof response.source_revision !== "string" || !commitPattern.test(response.source_revision)) throw new Error("source revisionが不正です");
  for (const key of ["result_sha256", "bundle_sha256"] as const) if (typeof response[key] !== "string" || !sha256Pattern.test(response[key])) throw new Error(`${key}が不正です`);
  const provider = record(response.provider, "provider");
  exactKeys(provider, ["name", "model"], "provider");
  if (!(["fixture", "ollama", "vertex"] as unknown[]).includes(provider.name) || (provider.model !== null && typeof provider.model !== "string")) throw new Error("providerが不正です");

  const result = record(response.result, "result");
  const artifactResult = record(await verifiedArtifact(response.result_artifact_base64, response.result_sha256, "result"), "result artifact");
  if (stableJson(artifactResult) !== stableJson(result)) throw new Error("result artifactとresponseが一致しません");
  if (result.run_id !== response.run_id) throw new Error("resultのrun_idが一致しません");
  const replay = await parseReplayRun(result);
  const bundle = record(response.bundle, "bundle");
  const artifactBundle = record(await verifiedArtifact(response.bundle_artifact_base64, response.bundle_sha256, "bundle"), "bundle artifact");
  if (stableJson(artifactBundle) !== stableJson(bundle)) throw new Error("bundle artifactとresponseが一致しません");
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
  if (typeof bundleReplay.event_stream_sha256 !== "string" || !sha256Pattern.test(bundleReplay.event_stream_sha256)) throw new Error("bundle replay event digestが不正です");
  if (evidence.event_stream_sha256 !== bundleReplay.event_stream_sha256) throw new Error("bundle evidence event digestが一致しません");
  const streamBytes = decodeBase64(response.event_stream_base64, "event stream");
  if (await sha256Hex(streamBytes) !== bundleReplay.event_stream_sha256) throw new Error("event stream SHA-256が一致しません");
  let streamEvents: unknown[];
  try {
    const stream = new TextDecoder("utf-8", { fatal: true }).decode(streamBytes);
    if (!stream.endsWith("\n")) throw new Error();
    streamEvents = stream.slice(0, -1).split("\n").map((line) => JSON.parse(line));
  } catch {
    throw new Error("event stream artifactが不正です");
  }
  if (stableJson(streamEvents) !== stableJson(bundle.events)) throw new Error("event stream artifactとbundleが一致しません");
  return { ...response, provider, result, replay, bundle } as VerifiedLocalRun;
}

export async function requestLocalRun(request: LocalRunRequest, sessionToken: string): Promise<VerifiedLocalRun> {
  if (!sessionToken) throw new Error("adapter起動時に表示されたsession tokenを入力してください");
  const response = await fetch("/api/runs", { method: "POST", headers: { "Content-Type": "application/json", "X-Fiction-Forks-Session": sessionToken }, body: JSON.stringify(request) });
  if (!response.ok) {
    const messages: Record<number, string> = { 400: "実行要求またはprovider設定が契約と一致しません。", 403: "session tokenの期限、origin、または実行許可を確認してください。", 409: "別のシミュレーションが実行中です。完了してから再実行してください。", 413: "実行要求が大きすぎます。", 415: "実行要求の形式が不正です。", 500: "シミュレーター側で実行に失敗しました。要求ではなくadapterを起動した環境を確認してください。" };
    throw new Error(messages[response.status] ?? "シミュレーターへ接続できませんでした。");
  }
  return parseLocalRunResponse(await response.json());
}
