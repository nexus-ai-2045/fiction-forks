import comparisonJson from "../../../artifacts/runs/haruhi-world-observation-comparison.json";
import delayJson from "../../../artifacts/runs/haruhi-world-observation-contestation-delay.json";
import interventionJson from "../../../interventions/haruhi-world-observation.json";
import manifestJson from "../../../artifacts/runs/haruhi-world-observation-fixture.manifest.json";
import { parseComparisonArtifact, parseInterventionArtifact, parseRunManifest } from "./contract";

export const comparison = parseComparisonArtifact(comparisonJson);
export const contestationDelay = parseComparisonArtifact(delayJson);
export const intervention = parseInterventionArtifact(interventionJson);
export const manifest = parseRunManifest(manifestJson);

if (intervention.id !== manifest.intervention_id) throw new Error("rendered intervention does not match the canonical manifest");

const nodeIds = new Set(intervention.technology_tree.nodes.map((node) => node.id));
if (nodeIds.size !== intervention.technology_tree.nodes.length) throw new Error("technology node IDs must be unique");
const dependencyIds = new Set([...nodeIds, ...intervention.prerequisites]);
for (const node of intervention.technology_tree.nodes) {
  if (node.depends_on.some((dependency) => !dependencyIds.has(dependency))) throw new Error(`unknown dependency for ${node.id}`);
}
if (intervention.technology_tree.activation_requires.some((nodeId) => !nodeIds.has(nodeId))) {
  throw new Error("activation_requires contains an unknown technology node");
}

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

if (comparison.comparison_year !== contestationDelay.comparison_year ||
    JSON.stringify(comparison.baseline) !== JSON.stringify(contestationDelay.baseline)) {
  throw new Error("named stress profiles must share an identical baseline and comparison year");
}
