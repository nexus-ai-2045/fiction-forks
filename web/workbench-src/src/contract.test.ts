import comparisonJson from "../../../artifacts/runs/haruhi-world-observation-comparison.json";
import delayJson from "../../../artifacts/runs/haruhi-world-observation-contestation-delay.json";
import fixtureJson from "../../../artifacts/runs/haruhi-world-observation-fixture.json";
import interventionJson from "../../../interventions/haruhi-world-observation.json";
import manifestJson from "../../../artifacts/runs/haruhi-world-observation-fixture.manifest.json";
import { canonicalizeRfc8785, parseComparisonArtifact, parseInterventionArtifact, parseReplayRun, parseRunManifest, pythonFloatRepr, validateWorkbenchRelationships } from "./contract";

describe("canonical comparison artifacts", () => {
  it("accepts the normal and named-delay fixtures", () => {
    expect(parseComparisonArtifact(comparisonJson).fork.activation_year).toBe(2032);
    expect(parseComparisonArtifact(delayJson).fork.activation_year).toBe(2037);
  });

  it("fails closed for unknown contracts", () => {
    expect(() => parseComparisonArtifact({ ...comparisonJson, schema_version: "v2" })).toThrow(/schema_version/);
    expect(() => parseInterventionArtifact({ ...interventionJson, schema_version: "v2" })).toThrow(/schema_version/);
    expect(() => parseInterventionArtifact({ ...interventionJson, costs: [] })).toThrow(/non-empty/);
    expect(() => parseInterventionArtifact({ ...interventionJson, failure_modes: ["   "] })).toThrow(/non-blank/);
    expect(() => parseComparisonArtifact({ ...comparisonJson, declared_side_effects: [] })).toThrow(/non-empty/);
  });

  it("fails closed when a rendered schedule or collapse state is malformed", () => {
    expect(() => parseComparisonArtifact({
      ...comparisonJson,
      fork: { ...comparisonJson.fork, technology_schedule: { "bad-node": "2032" } },
    })).toThrow(/technology_schedule/);
    expect(() => parseComparisonArtifact({
      ...comparisonJson,
      fork: { ...comparisonJson.fork, collapsed: false, collapse_year: 2036 },
    })).toThrow(/inconsistent/);
    expect(() => parseComparisonArtifact({ ...comparisonJson, comparison_year: 2036.5 })).toThrow(/integer/);
    expect(() => parseComparisonArtifact({
      ...comparisonJson,
      baseline: { ...comparisonJson.baseline, final_state: { ...comparisonJson.baseline.final_state, legitimacy: 101 } },
    })).toThrow(/between 0 and 100/);
    expect(() => parseComparisonArtifact({
      ...comparisonJson,
      state_delta_at_comparison_year: { ...comparisonJson.state_delta_at_comparison_year, legitimacy: -101 },
    })).not.toThrow();
    expect(() => parseComparisonArtifact({
      ...comparisonJson,
      fork: { ...comparisonJson.fork, technology_delays: { "contested-evidence-protocol": -1 } },
    })).toThrow(/greater than or equal to 0/);
  });

  it("accepts only replay-equivalent non-AI fixture provenance", () => {
    expect(parseRunManifest(manifestJson).engine_commit).toMatch(/^[0-9a-f]{40}$/);
    expect(parseInterventionArtifact(interventionJson).schema_version).toBe("fiction_forks_intervention.v1");
    expect(() => parseRunManifest({ ...manifestJson, ai_measured: true })).toThrow(/fixture manifests/);
    expect(() => parseRunManifest({ ...manifestJson, comparison_artifact_sha256: "spoof" })).toThrow(/SHA|sha|comparison_artifact/);
  });

  it("fails closed when named-profile meaning drifts across canonical artifacts", () => {
    const normal = parseComparisonArtifact(comparisonJson);
    const delay = parseComparisonArtifact(delayJson);
    const intervention = parseInterventionArtifact(interventionJson);
    const manifest = parseRunManifest(manifestJson);
    expect(() => validateWorkbenchRelationships(
      { ...normal, fork: { ...normal.fork, technology_delays: { "contested-evidence-protocol": 1 } } },
      delay,
      intervention,
      manifest,
    )).toThrow(/normal profile/);
    expect(() => validateWorkbenchRelationships(
      normal,
      delay,
      { ...intervention, costs: ["drift"] },
      manifest,
    )).toThrow(/declared_costs/);
    expect(() => validateWorkbenchRelationships(
      normal,
      delay,
      intervention,
      { ...manifest, scenario_id: "another-scenario" },
    )).toThrow(/Japan scenario/);
    expect(() => validateWorkbenchRelationships(
      normal,
      { ...delay, fork: { ...delay.fork, technology_delays: { "contested-evidence-protocol": 1 } } },
      intervention,
      manifest,
    )).toThrow(/schedule/);
    expect(() => validateWorkbenchRelationships(
      { ...normal, fork: { ...normal.fork, technology_schedule: { ...normal.fork.technology_schedule, "cross-observer-anomaly-drills": 2030 } } },
      delay,
      intervention,
      manifest,
    )).toThrow(/normal technology schedule|normal activation year/);
    expect(() => validateWorkbenchRelationships(
      { ...normal, fork: { ...normal.fork, activation_year: 2031 } },
      delay,
      intervention,
      manifest,
    )).toThrow(/normal activation year/);
  });
});

describe("canonical replay events", () => {
  it("keeps RFC 8785 bundle numbers distinct from Python event float spelling", () => {
    expect(canonicalizeRfc8785({ z: -0, a: 1.0, exponent: 1e-7 })).toBe('{"a":1,"exponent":1e-7,"z":0}');
    expect([1.0, -0.0, 1e-7, 1e-6, 1e15, 1e16].map(pythonFloatRepr)).toEqual([
      "1.0", "-0.0", "1e-07", "1e-06", "1000000000000000.0", "1e+16",
    ]);
  });

  it("keeps the stored event order and numbers the sequence from 1", async () => {
    const run = await parseReplayRun(fixtureJson);
    expect(run.run_id).toBe(fixtureJson.run_id);
    expect(run.events).toHaveLength(fixtureJson.actions.length);
    expect(run.events.map((event) => event.sequence)).toEqual(run.events.map((_, index) => index + 1));
    expect(run.events.map((event) => event.intent_id)).toEqual(fixtureJson.actions.map((entry) => entry.intent_id));
    expect(run.events[run.events.length - 1].event_hash).toBe(run.final_event_hash);
  });

  it("fails closed for tampered replay events", async () => {
    const tamper = (mutate: (clone: typeof fixtureJson) => void) => {
      const clone = structuredClone(fixtureJson);
      mutate(clone);
      return () => parseReplayRun(clone);
    };
    await expect(tamper((clone) => { clone.actions[0].action.stance = "maybe"; })()).rejects.toThrow(/stance/);
    await expect(tamper((clone) => { clone.actions[0].action.run_id = "ff-other"; })()).rejects.toThrow(/belong/);
    await expect(tamper((clone) => { clone.actions[0].valid = false; })()).rejects.toThrow(/inconsistent/);
    await expect(tamper((clone) => { clone.actions[0].event_hash = "a".repeat(64); })()).rejects.toThrow(/event_hash mismatch/);
    await expect(tamper((clone) => { clone.actions[0].action.action_id = "tampered-action"; })()).rejects.toThrow(/event_hash mismatch/);
    await expect(tamper((clone) => { clone.actions[1].previous_event_hash = "b".repeat(64); })()).rejects.toThrow(/hash chain/);
    await expect(tamper((clone) => { clone.final_event_hash = "c".repeat(64); })()).rejects.toThrow(/final_event_hash/);
    await expect(tamper((clone) => { clone.actions[0].action.turn = 99; })()).rejects.toThrow(/turn/);
    await expect(tamper((clone) => { clone.actions.length = 0; })()).rejects.toThrow(/non-empty/);
  });
});
