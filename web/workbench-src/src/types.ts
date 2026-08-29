export const metricKeys = [
  "cognitive_sovereignty",
  "legitimacy",
  "living_systems",
  "repair_capacity",
  "strategic_autonomy",
] as const;

export type MetricKey = (typeof metricKeys)[number];
export type MetricState = Record<MetricKey, number>;

export interface WorldState {
  collapse_year: number | null;
  collapsed: boolean;
  final_state: MetricState;
  state_at_comparison_year: MetricState;
}

export interface ForkState extends WorldState {
  activation_year: number;
  technology_delays: Record<string, number>;
  technology_schedule: Record<string, number>;
}

export interface ComparisonArtifact {
  baseline: WorldState;
  comparison_year: number;
  declared_costs: string[];
  declared_failure_modes: string[];
  declared_side_effects: string[];
  engine_version: string;
  fork: ForkState;
  intervention_id: string;
  scenario_id: string;
  schema_version: "fiction_forks_comparison.v1";
  seed: number;
  state_delta_at_comparison_year: MetricState;
}

export interface TechnologyNode {
  id: string;
  label: string;
  kind: "technology" | "institution" | "operations";
  completion_evidence: string;
  depends_on: string[];
}

export interface InterventionArtifact {
  id: string;
  fiction_reference: string;
  extracted_function: string;
  implementation_hypothesis: string;
  realization_mode: string;
  prerequisites: string[];
  technology_tree: { nodes: TechnologyNode[]; activation_requires: string[] };
}

export interface RunManifest {
  schema_version: "fiction_forks_run_manifest.v1";
  run_kind: "fixture";
  ai_measured: false;
  engine_commit: string;
  engine_version: string;
  scenario_id: string;
  intervention_id: string;
  seed: number;
  artifact_sha256: string;
  comparison_artifact_sha256: string;
  delay_artifact_sha256: string;
  replay_equivalent: true;
}
