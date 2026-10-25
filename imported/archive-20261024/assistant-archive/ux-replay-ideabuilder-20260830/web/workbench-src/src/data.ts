import comparisonJson from "../../../artifacts/runs/haruhi-world-observation-comparison.json";
import delayJson from "../../../artifacts/runs/haruhi-world-observation-contestation-delay.json";
import fixtureJson from "../../../artifacts/runs/haruhi-world-observation-fixture.json";
import interventionRaw from "../../../interventions/haruhi-world-observation.json?raw";
import manifestJson from "../../../artifacts/runs/haruhi-world-observation-fixture.manifest.json";
import { parseComparisonArtifact, parseInterventionArtifact, parseReplayRun, parseRunManifest, validateWorkbenchRelationships } from "./contract";

async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export const comparison = parseComparisonArtifact(comparisonJson);
export const contestationDelay = parseComparisonArtifact(delayJson);
export const manifest = parseRunManifest(manifestJson);

export const replayRun = parseReplayRun(fixtureJson);
if (replayRun.seed !== manifest.seed) throw new Error("replay run seed does not match the canonical manifest");
if (replayRun.events[replayRun.events.length - 1].event_hash !== replayRun.final_event_hash) {
  throw new Error("replay run final_event_hash does not match the stored event stream");
}

const interventionDigest = await sha256Hex(interventionRaw);
if (interventionDigest !== manifest.intervention_artifact_sha256) {
  throw new Error("rendered intervention digest does not match the canonical manifest");
}

export const intervention = parseInterventionArtifact(JSON.parse(interventionRaw));
if (intervention.id !== manifest.intervention_id) throw new Error("rendered intervention does not match the canonical manifest");
validateWorkbenchRelationships(comparison, contestationDelay, intervention, manifest);

const nodeIds = new Set(intervention.technology_tree.nodes.map((node) => node.id));
if (nodeIds.size !== intervention.technology_tree.nodes.length) throw new Error("technology node IDs must be unique");
const dependencyIds = new Set([...nodeIds, ...intervention.prerequisites]);
for (const node of intervention.technology_tree.nodes) {
  if (node.depends_on.some((dependency) => !dependencyIds.has(dependency))) throw new Error(`unknown dependency for ${node.id}`);
}
if (intervention.technology_tree.activation_requires.some((nodeId) => !nodeIds.has(nodeId))) {
  throw new Error("activation_requires contains an unknown technology node");
}

const technologyLabels = new Map(intervention.technology_tree.nodes.map((node) => [node.id, node.label]));
const technologyKinds = new Map(intervention.technology_tree.nodes.map((node) => [node.id, node.kind]));
const namedDelayEntries = Object.entries(contestationDelay.fork.technology_delays);
if (namedDelayEntries.length === 0 || namedDelayEntries.some(([nodeId, years]) => !nodeIds.has(nodeId) || years <= 0)) {
  throw new Error("named delay profile must contain positive delays for canonical technology nodes");
}
export const contestationDelayLabel = namedDelayEntries
  .map(([nodeId, years]) => `${technologyLabels.get(nodeId)}を${years}年遅延`)
  .join("・");
const kindLabels = { technology: "技術", institution: "制度", operations: "運用" } as const;
const delayedKinds = [...new Set(namedDelayEntries.map(([nodeId]) => technologyKinds.get(nodeId)))];
const delayedKindLabel = delayedKinds.map((kind) => kindLabels[kind!]).join("・");
export function describeActivationDelay(kindLabel: string, normalYear: number, delayYear: number): string {
  const activationDelayYears = delayYear - normalYear;
  return activationDelayYears === 0
    ? `${kindLabel}を遅らせても、発動年は変わらない。`
    : `${kindLabel}の遅延が、発動を${activationDelayYears}年遅らせる。`;
}
export const contestationDelayHeading = describeActivationDelay(
  delayedKindLabel,
  comparison.fork.activation_year,
  contestationDelay.fork.activation_year,
);

for (const artifact of [comparison, contestationDelay]) {
  if (artifact.engine_version !== manifest.engine_version || artifact.scenario_id !== manifest.scenario_id ||
      artifact.intervention_id !== manifest.intervention_id || artifact.seed !== manifest.seed) {
    throw new Error("artifact provenance does not match the canonical manifest");
  }
  const scheduleIds = Object.keys(artifact.fork.technology_schedule);
  if (scheduleIds.length !== nodeIds.size || scheduleIds.some((nodeId) => !nodeIds.has(nodeId))) {
    throw new Error("artifact technology schedule does not cover the canonical technology tree");
  }
  for (const key of Object.keys(artifact.state_delta_at_comparison_year) as Array<keyof typeof artifact.state_delta_at_comparison_year>) {
    const expectedDelta = Number((artifact.fork.state_at_comparison_year[key] - artifact.baseline.state_at_comparison_year[key]).toFixed(2));
    if (artifact.state_delta_at_comparison_year[key] !== expectedDelta) throw new Error(`artifact delta is inconsistent for ${key}`);
  }
}
