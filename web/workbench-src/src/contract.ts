import { metricKeys, replayStances, type ComparisonArtifact, type InterventionArtifact, type ReplayEvent, type ReplayRun, type RunManifest } from "./types";

const sha256Pattern = /^[0-9a-f]{64}$/;
const commitPattern = /^[0-9a-f]{40}$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertNumber(record: Record<string, unknown>, key: string): void {
  if (typeof record[key] !== "number" || !Number.isFinite(record[key])) throw new Error(`${key} must be a finite number`);
}

function assertInteger(record: Record<string, unknown>, key: string): void {
  if (typeof record[key] !== "number" || !Number.isInteger(record[key])) throw new Error(`${key} must be an integer`);
}

function assertMetricState(value: unknown, path: string): void {
  if (!isRecord(value)) throw new Error(`${path} must be an object`);
  const actualKeys = Object.keys(value).sort();
  const expectedKeys = [...metricKeys].sort();
  if (actualKeys.length !== expectedKeys.length || actualKeys.some((key, index) => key !== expectedKeys[index])) {
    throw new Error(`${path} must contain exactly the canonical metric keys`);
  }
  metricKeys.forEach((key) => assertNumber(value, `${key}`));
}

function assertString(record: Record<string, unknown>, key: string): void {
  if (typeof record[key] !== "string" || record[key].length === 0) throw new Error(`${key} must be a non-empty string`);
}

function assertYearOrNull(record: Record<string, unknown>, key: string): void {
  if (record[key] !== null && (typeof record[key] !== "number" || !Number.isInteger(record[key]))) {
    throw new Error(`${key} must be an integer or null`);
  }
}

function assertIntegerRecord(value: unknown, path: string, minimum: number): void {
  if (!isRecord(value)) throw new Error(`${path} must be an object`);
  Object.entries(value).forEach(([key, item]) => {
    if (!key || typeof item !== "number" || !Number.isInteger(item) || item < minimum) {
      throw new Error(`${path}.${key} must be an integer greater than or equal to ${minimum}`);
    }
  });
}

function assertNonEmptyStringArray(value: unknown, path: string): void {
  if (!Array.isArray(value) || value.length === 0 ||
      !value.every((item) => typeof item === "string" && item.trim().length > 0)) {
    throw new Error(`${path} must be a non-empty array of non-blank strings`);
  }
}

function assertBoundedState(value: unknown, path: string): void {
  assertMetricState(value, path);
  for (const [key, item] of Object.entries(value as Record<string, number>)) {
    if (item < 0 || item > 100) throw new Error(`${path}.${key} must be between 0 and 100`);
  }
}

export function parseComparisonArtifact(value: unknown): ComparisonArtifact {
  if (!isRecord(value)) throw new Error("comparison artifact must be an object");
  if (value.schema_version !== "fiction_forks_comparison.v1") throw new Error("unsupported comparison schema_version");
  ["comparison_year", "seed"].forEach((key) => assertInteger(value, key));
  ["engine_version", "scenario_id", "intervention_id"].forEach((key) => assertString(value, key));
  if (!isRecord(value.baseline) || !isRecord(value.fork)) throw new Error("baseline and fork are required");
  [value.baseline, value.fork].forEach((world, index) => {
    if (typeof world.collapsed !== "boolean") throw new Error(`world ${index} collapsed must be boolean`);
    assertYearOrNull(world, "collapse_year");
    if (world.collapsed !== (world.collapse_year !== null)) throw new Error(`world ${index} collapse state is inconsistent`);
    assertBoundedState(world.final_state, `world ${index} final state`);
    assertBoundedState(world.state_at_comparison_year, `world ${index} state`);
  });
  assertInteger(value.fork, "activation_year");
  assertIntegerRecord(value.fork.technology_delays, "technology_delays", 0);
  assertIntegerRecord(value.fork.technology_schedule, "technology_schedule", 0);
  assertMetricState(value.state_delta_at_comparison_year, "delta");
  for (const key of ["declared_costs", "declared_failure_modes", "declared_side_effects"] as const) {
    assertNonEmptyStringArray(value[key], key);
  }
  return value as unknown as ComparisonArtifact;
}

export function parseInterventionArtifact(value: unknown): InterventionArtifact {
  if (!isRecord(value) || !isRecord(value.technology_tree) || !Array.isArray(value.technology_tree.nodes)) {
    throw new Error("intervention technology_tree.nodes is required");
  }
  if (value.schema_version !== "fiction_forks_intervention.v1") throw new Error("unsupported intervention schema_version");
  for (const key of ["id", "fiction_reference", "extracted_function", "implementation_hypothesis", "realization_mode"]) {
    assertString(value, key);
  }
  for (const key of ["prerequisites", "costs", "side_effects", "failure_modes"] as const) {
    assertNonEmptyStringArray(value[key], key);
  }
  if (!Array.isArray(value.technology_tree.activation_requires) ||
      !value.technology_tree.activation_requires.every((item) => typeof item === "string")) {
    throw new Error("technology_tree.activation_requires must be a string array");
  }
  for (const node of value.technology_tree.nodes) {
    if (!isRecord(node) || typeof node.id !== "string" || typeof node.label !== "string" ||
      !["technology", "institution", "operations"].includes(String(node.kind)) ||
      typeof node.lead_time_years !== "number" || !Number.isInteger(node.lead_time_years) || node.lead_time_years < 0 ||
      typeof node.completion_evidence !== "string" || !Array.isArray(node.depends_on) ||
      !node.depends_on.every((item) => typeof item === "string")) {
      throw new Error("invalid technology node");
    }
  }
  return value as unknown as InterventionArtifact;
}

export function parseRunManifest(value: unknown): RunManifest {
  if (!isRecord(value) || value.schema_version !== "fiction_forks_run_manifest.v1") throw new Error("unsupported manifest schema_version");
  if (value.run_kind !== "fixture" || value.ai_measured !== false || value.replay_equivalent !== true) {
    throw new Error("workbench only accepts replay-equivalent fixture manifests");
  }
  ["engine_version", "scenario_id", "intervention_id"].forEach((key) => assertString(value, key));
  assertInteger(value, "seed");
  if (typeof value.engine_commit !== "string" || !commitPattern.test(value.engine_commit)) throw new Error("invalid engine_commit");
  for (const key of ["artifact_sha256", "comparison_artifact_sha256", "delay_artifact_sha256", "intervention_artifact_sha256"] as const) {
    if (typeof value[key] !== "string" || !sha256Pattern.test(value[key])) throw new Error(`invalid ${key}`);
  }
  return value as unknown as RunManifest;
}

function canonicalNumber(value: number): string {
  if (!Number.isFinite(value)) throw new Error("canonical JSON does not accept non-finite numbers");
  return JSON.stringify(value);
}

/** RFC 8785/JCS serialization used by meta-security-run-bundle event streams. */
export function canonicalizeRfc8785(value: unknown): string {
  if (typeof value === "number") return canonicalNumber(value);
  if (Array.isArray(value)) return `[${value.map(canonicalizeRfc8785).join(",")}]`;
  if (isRecord(value)) {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalizeRfc8785(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

const pythonFloatMarker = Symbol("python-float");
type PythonFloat = { [pythonFloatMarker]: number };

function pythonFloat(value: number): PythonFloat {
  return { [pythonFloatMarker]: value };
}

export function pythonFloatRepr(value: number): string {
  if (!Number.isFinite(value)) throw new Error("canonical event JSON does not accept non-finite numbers");
  if (Object.is(value, -0)) return "-0.0";
  if (value === 0) return "0.0";
  const exponent = Math.floor(Math.log10(Math.abs(value)));
  if (exponent < -4 || exponent >= 16) {
    return value.toExponential().replace(/e([+-])(\d+)$/, (_match, sign: string, digits: string) => `e${sign}${digits.padStart(2, "0")}`);
  }
  const rendered = value.toString();
  return rendered.includes(".") ? rendered : `${rendered}.0`;
}

function canonicalizePythonEvent(value: unknown): string {
  if (typeof value === "object" && value !== null && pythonFloatMarker in value) {
    return pythonFloatRepr((value as PythonFloat)[pythonFloatMarker]);
  }
  if (typeof value === "number") return canonicalNumber(value);
  if (Array.isArray(value)) return `[${value.map(canonicalizePythonEvent).join(",")}]`;
  if (isRecord(value)) {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalizePythonEvent(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

async function sha256PythonEvent(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalizePythonEvent(value));
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function parseReplayRun(value: unknown): Promise<ReplayRun> {
  if (!isRecord(value)) throw new Error("fixture run must be an object");
  assertString(value, "run_id");
  assertInteger(value, "seed");
  assertInteger(value, "turn_count");
  if (typeof value.final_event_hash !== "string" || !sha256Pattern.test(value.final_event_hash)) {
    throw new Error("invalid final_event_hash");
  }
  if (!Array.isArray(value.actions) || value.actions.length === 0) throw new Error("fixture actions must be a non-empty array");
  // 保存順をそのまま採用する。並べ替え・再計算はしない。
  let previousEventHash: string | null = null;
  const events: ReplayEvent[] = [];
  for (const [index, entry] of value.actions.entries()) {
    if (!isRecord(entry) || !isRecord(entry.action)) throw new Error(`event ${index} must contain an action`);
    const action = entry.action;
    if (action.schema_version !== "fiction_forks_action.v1") throw new Error(`event ${index} has an unsupported action schema`);
    if (action.run_id !== value.run_id) throw new Error(`event ${index} does not belong to this run`);
    ["agent_id", "action_id"].forEach((key) => assertString(action, key));
    assertInteger(action, "turn");
    if (typeof action.turn !== "number" || action.turn < 1 || action.turn > (value.turn_count as number)) {
      throw new Error(`event ${index} turn is out of range`);
    }
    if (!replayStances.includes(action.stance as (typeof replayStances)[number])) {
      throw new Error(`event ${index} has an unknown stance`);
    }
    for (const key of ["responds_to", "target_ids"] as const) {
      if (!Array.isArray(action[key]) || !(action[key] as unknown[]).every((item) => typeof item === "string" && item.length > 0)) {
        throw new Error(`event ${index} ${key} must be a string array`);
      }
    }
    if (typeof entry.valid !== "boolean") throw new Error(`event ${index} valid must be boolean`);
    if (entry.invalid_reason !== null && typeof entry.invalid_reason !== "string") {
      throw new Error(`event ${index} invalid_reason must be a string or null`);
    }
    if (entry.valid !== (entry.invalid_reason === null)) throw new Error(`event ${index} validity is inconsistent`);
    if (typeof entry.intent_id !== "string" || entry.intent_id.length === 0) throw new Error(`event ${index} intent_id is required`);
    if (typeof entry.event_hash !== "string" || !sha256Pattern.test(entry.event_hash)) {
      throw new Error(`event ${index} event_hash must be a SHA-256 hex digest`);
    }
    for (const key of ["previous_event_hash", "state_before_hash", "state_after_hash"] as const) {
      if (typeof entry[key] !== "string" || !sha256Pattern.test(entry[key])) {
        throw new Error(`event ${index} ${key} must be a SHA-256 hex digest`);
      }
    }
    if (previousEventHash !== null && entry.previous_event_hash !== previousEventHash) {
      throw new Error(`event ${index} previous_event_hash breaks the hash chain`);
    }
    const receiptAction = { ...entry.action };
    if (typeof receiptAction.confidence !== "number" || !Number.isFinite(receiptAction.confidence)) {
      throw new Error(`event ${index} confidence must be a finite number`);
    }
    const confidence = receiptAction.confidence;
    const receiptFor = (canonicalConfidence: unknown) => ({
      intent_id: entry.intent_id,
      action: { ...receiptAction, confidence: canonicalConfidence },
      valid: entry.valid,
      invalid_reason: entry.invalid_reason,
      state_before_hash: entry.state_before_hash,
      state_after_hash: entry.state_after_hash,
    });
    // JSON.parse cannot distinguish Python's `1` from `1.0`. Rebuild every
    // representation that could have produced this numeric value and require
    // the stored digest to match one of them. This also preserves -0.0 and
    // Python's padded exponent spelling without trusting the declared hash.
    const confidenceCandidates: unknown[] = [pythonFloat(confidence)];
    if (Number.isInteger(confidence)) confidenceCandidates.push(confidence);
    const expectedHashes = await Promise.all(confidenceCandidates.map((candidate) => sha256PythonEvent({
      previous_event_hash: entry.previous_event_hash,
      receipt: receiptFor(candidate),
    })));
    if (!expectedHashes.includes(entry.event_hash)) throw new Error(`event ${index} event_hash mismatch`);
    const parsed: ReplayEvent = {
      sequence: index + 1,
      intent_id: entry.intent_id,
      action: {
        schema_version: "fiction_forks_action.v1",
        run_id: action.run_id as string,
        turn: action.turn as number,
        agent_id: action.agent_id as string,
        action_id: action.action_id as string,
        stance: action.stance as ReplayEvent["action"]["stance"],
        responds_to: action.responds_to as string[],
        target_ids: action.target_ids as string[],
      },
      valid: entry.valid,
      invalid_reason: entry.invalid_reason,
      previous_event_hash: entry.previous_event_hash as string,
      state_before_hash: entry.state_before_hash as string,
      state_after_hash: entry.state_after_hash as string,
      event_hash: entry.event_hash,
    };
    events.push(parsed);
    previousEventHash = parsed.event_hash;
  }
  if (previousEventHash !== value.final_event_hash) throw new Error("final_event_hash does not match the hash chain");
  return {
    run_id: value.run_id as string,
    seed: value.seed as number,
    turn_count: value.turn_count as number,
    final_event_hash: value.final_event_hash,
    events,
  };
}

/**
 * production のロード経路が持つのは、engineロジックの複製にならない関係検査だけ。
 * すなわちscenarioとprofileの同一性、canonical technology treeとの参照整合、
 * 2つのnamed profileが同じ実験を指していること、宣言リストがinterventionと一致すること。
 *
 * 完成年と発動年をTypeScript側で再計算する検査はここに置かない。engineの
 * スケジューリング仕様が変わったとき、正しいPython出力を誤ってrejectするか、
 * 変更に気づかず古い仕様のまま通すかのどちらかに倒れるため。
 * 再計算による突合は`contract.test.ts`のcross-language contract testが持つ。
 */
export function validateWorkbenchRelationships(
  normal: ComparisonArtifact,
  delay: ComparisonArtifact,
  intervention: InterventionArtifact,
  manifest: RunManifest,
): void {
  if (manifest.scenario_id !== "japan-2036-centralization") {
    throw new Error("the Japan workbench only accepts the canonical Japan scenario");
  }
  if (Object.keys(normal.fork.technology_delays).length !== 0) {
    throw new Error("the normal profile must not contain technology delays");
  }
  const nodeIds = new Set(intervention.technology_tree.nodes.map((node) => node.id));
  const normalScheduleIds = Object.keys(normal.fork.technology_schedule);
  if (normalScheduleIds.length !== nodeIds.size || normalScheduleIds.some((nodeId) => !nodeIds.has(nodeId))) {
    throw new Error("normal technology schedule does not cover exactly the canonical technology tree");
  }
  const delayScheduleIds = Object.keys(delay.fork.technology_schedule);
  if (delayScheduleIds.length !== nodeIds.size || delayScheduleIds.some((nodeId) => !nodeIds.has(nodeId))) {
    throw new Error("named delay profile schedule does not cover exactly the canonical technology tree");
  }
  const delayEntries = Object.entries(delay.fork.technology_delays);
  if (delayEntries.length === 0 || delayEntries.some(([nodeId, years]) => !nodeIds.has(nodeId) || years <= 0)) {
    throw new Error("named delay profile must contain positive delays for canonical technology nodes");
  }
  if (normal.comparison_year !== delay.comparison_year || JSON.stringify(normal.baseline) !== JSON.stringify(delay.baseline)) {
    throw new Error("named stress profiles must share an identical baseline and comparison year");
  }
  for (const artifact of [normal, delay]) {
    for (const [artifactKey, interventionKey] of [
      ["declared_costs", "costs"],
      ["declared_side_effects", "side_effects"],
      ["declared_failure_modes", "failure_modes"],
    ] as const) {
      if (JSON.stringify(artifact[artifactKey]) !== JSON.stringify(intervention[interventionKey])) {
        throw new Error(`${artifactKey} does not match the canonical intervention`);
      }
    }
  }
}
