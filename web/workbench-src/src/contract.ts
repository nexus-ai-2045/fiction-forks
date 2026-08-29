import { metricKeys, type ComparisonArtifact, type InterventionArtifact, type RunManifest } from "./types";

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
    assertMetricState(world.final_state, `world ${index} final state`);
    assertMetricState(world.state_at_comparison_year, `world ${index} state`);
  });
  assertInteger(value.fork, "activation_year");
  assertIntegerRecord(value.fork.technology_delays, "technology_delays", 0);
  assertIntegerRecord(value.fork.technology_schedule, "technology_schedule", 0);
  assertMetricState(value.state_delta_at_comparison_year, "delta");
  for (const key of ["declared_costs", "declared_failure_modes", "declared_side_effects"] as const) {
    if (!Array.isArray(value[key]) || !(value[key] as unknown[]).every((item) => typeof item === "string")) {
      throw new Error(`${key} must be a string array`);
    }
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
    if (!Array.isArray(value[key]) || !value[key].every((item) => typeof item === "string")) {
      throw new Error(`${key} must be a string array`);
    }
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
  const delayEntries = Object.entries(delay.fork.technology_delays);
  if (delayEntries.length === 0 || delayEntries.some(([nodeId, years]) => !nodeIds.has(nodeId) || years <= 0)) {
    throw new Error("named delay profile must contain positive delays for canonical technology nodes");
  }
  const nodes = new Map(intervention.technology_tree.nodes.map((node) => [node.id, node]));
  const expectedSchedule = new Map<string, number>();
  const visiting = new Set<string>();
  const projectCompletionYear = (nodeId: string): number => {
    const cached = expectedSchedule.get(nodeId);
    if (cached !== undefined) return cached;
    const node = nodes.get(nodeId);
    const baselineYear = normal.fork.technology_schedule[nodeId];
    if (!node || baselineYear === undefined) throw new Error("normal technology schedule does not cover the canonical technology tree");
    if (visiting.has(nodeId)) throw new Error("canonical technology tree must not contain a cycle");
    visiting.add(nodeId);
    const delayedDependencies = node.depends_on
      .filter((dependencyId) => nodes.has(dependencyId))
      .map((dependencyId) => projectCompletionYear(dependencyId) + node.lead_time_years);
    visiting.delete(nodeId);
    const completionYear = Math.max(baselineYear, ...delayedDependencies) + (delay.fork.technology_delays[nodeId] ?? 0);
    expectedSchedule.set(nodeId, completionYear);
    return completionYear;
  };
  for (const nodeId of nodeIds) {
    if (delay.fork.technology_schedule[nodeId] !== projectCompletionYear(nodeId)) {
      throw new Error("named delay profile schedule does not match its declared technology delays");
    }
  }
  if (Object.keys(delay.fork.technology_schedule).length !== nodeIds.size) {
    throw new Error("named delay profile schedule does not cover exactly the canonical technology tree");
  }
  const expectedActivationYear = Math.max(
    ...intervention.technology_tree.activation_requires.map((nodeId) => projectCompletionYear(nodeId)),
  );
  if (delay.fork.activation_year !== expectedActivationYear) {
    throw new Error("named delay profile activation year does not match its technology schedule");
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
