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
  lead_time_years: number;
  completion_evidence: string;
  depends_on: string[];
}

export interface InterventionArtifact {
  schema_version: "fiction_forks_intervention.v1";
  id: string;
  fiction_reference: string;
  extracted_function: string;
  implementation_hypothesis: string;
  realization_mode: string;
  prerequisites: string[];
  costs: string[];
  side_effects: string[];
  failure_modes: string[];
  technology_tree: { nodes: TechnologyNode[]; activation_requires: string[] };
}

export const replayStances = ["support", "condition", "oppose", "abstain"] as const;
export type ReplayStance = (typeof replayStances)[number];

export interface ReplayAction {
  schema_version: "fiction_forks_action.v1";
  run_id: string;
  turn: number;
  agent_id: string;
  action_id: string;
  stance: ReplayStance;
  responds_to: string[];
  target_ids: string[];
}

export interface ReplayEvent {
  /** 保存順 (1始まり)。表示専用で、event列の並びそのもの。 */
  sequence: number;
  intent_id: string;
  action: ReplayAction;
  valid: boolean;
  invalid_reason: string | null;
  event_hash: string;
}

export interface ReplayRun {
  run_id: string;
  seed: number;
  turn_count: number;
  final_event_hash: string;
  events: ReplayEvent[];
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
  intervention_artifact_sha256: string;
  replay_equivalent: true;
}
