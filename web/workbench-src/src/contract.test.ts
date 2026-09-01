import comparisonJson from "../../../artifacts/runs/haruhi-world-observation-comparison.json";
import delayJson from "../../../artifacts/runs/haruhi-world-observation-contestation-delay.json";
import fixtureJson from "../../../artifacts/runs/haruhi-world-observation-fixture.json";
import interventionJson from "../../../interventions/haruhi-world-observation.json";
import manifestJson from "../../../artifacts/runs/haruhi-world-observation-fixture.manifest.json";
import scenarioJson from "../../../scenarios/japan-2036/scenario.json";
import { canonicalizeRfc8785, parseComparisonArtifact, parseInterventionArtifact, parseReplayRun, parseRunManifest, pythonFloatRepr, validateWorkbenchRelationships } from "./contract";
import { metricKeys, type ComparisonArtifact, type InterventionArtifact } from "./types";

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
      { ...delay, fork: { ...delay.fork, technology_schedule: { "extra-node": 2036 } } },
      intervention,
      manifest,
    )).toThrow(/named delay profile schedule/);
    expect(() => validateWorkbenchRelationships(
      { ...normal, fork: { ...normal.fork, technology_schedule: { "extra-node": 2032 } } },
      delay,
      intervention,
      manifest,
    )).toThrow(/normal technology schedule/);
  });
});

/**
 * `src/fiction_forks/engine.py`の`_technology_schedule`をtest内だけに写した参照実装。
 * scenarioのstart_yearとcapability_availability、interventionの技術ツリー、named delayという
 * Python engineと同じ入力から完成年を引き直す。production側には置かない。
 */
function projectTechnologySchedule(
  intervention: InterventionArtifact,
  delays: Record<string, number>,
): Record<string, number> {
  const nodes = new Map(intervention.technology_tree.nodes.map((node) => [node.id, node]));
  const external = scenarioJson.capability_availability as Record<string, number>;
  const schedule = new Map<string, number>();
  const visiting = new Set<string>();
  const completionYear = (nodeId: string): number => {
    const cached = schedule.get(nodeId);
    if (cached !== undefined) return cached;
    const node = nodes.get(nodeId);
    if (!node) throw new Error(`technology_tree has an unknown node: ${nodeId}`);
    if (visiting.has(nodeId)) throw new Error(`technology_tree has a cycle at: ${nodeId}`);
    visiting.add(nodeId);
    const dependencyYears = [scenarioJson.start_year];
    for (const dependency of node.depends_on) {
      dependencyYears.push(dependency in external ? external[dependency] : completionYear(dependency));
    }
    const completed = Math.max(...dependencyYears) + node.lead_time_years + (delays[nodeId] ?? 0);
    visiting.delete(nodeId);
    schedule.set(nodeId, completed);
    return completed;
  };
  for (const nodeId of nodes.keys()) completionYear(nodeId);
  return Object.fromEntries(schedule);
}

/** `_activation_year`の写し。発動に必要なノードの完成年のうち最も遅いもの。 */
function projectActivationYear(intervention: InterventionArtifact, delays: Record<string, number>): number {
  const schedule = projectTechnologySchedule(intervention, delays);
  return Math.max(...intervention.technology_tree.activation_requires.map((nodeId) => schedule[nodeId]));
}

/** artifactが申告した完成年と発動年を、engine参照実装の投影と突き合わせる。 */
function assertScheduleMatchesEngine(artifact: ComparisonArtifact, intervention: InterventionArtifact): void {
  const projected = projectTechnologySchedule(intervention, artifact.fork.technology_delays);
  const declared = artifact.fork.technology_schedule;
  const nodeIds = [...new Set([...Object.keys(projected), ...Object.keys(declared)])].sort();
  if (nodeIds.some((nodeId) => projected[nodeId] !== declared[nodeId])) {
    throw new Error("technology schedule does not match its declared technology delays");
  }
  if (artifact.fork.activation_year !== projectActivationYear(intervention, artifact.fork.technology_delays)) {
    throw new Error("activation year does not match its technology schedule");
  }
}

describe("cross-language technology schedule", () => {
  const intervention = parseInterventionArtifact(interventionJson);
  const normal = parseComparisonArtifact(comparisonJson);
  const delay = parseComparisonArtifact(delayJson);

  it("reproduces the Python schedule and activation year for both canonical profiles", () => {
    expect(scenarioJson.id).toBe(parseRunManifest(manifestJson).scenario_id);
    expect(projectTechnologySchedule(intervention, normal.fork.technology_delays)).toEqual(normal.fork.technology_schedule);
    expect(projectActivationYear(intervention, normal.fork.technology_delays)).toBe(normal.fork.activation_year);
    expect(projectTechnologySchedule(intervention, delay.fork.technology_delays)).toEqual(delay.fork.technology_schedule);
    expect(projectActivationYear(intervention, delay.fork.technology_delays)).toBe(delay.fork.activation_year);
    expect(() => assertScheduleMatchesEngine(normal, intervention)).not.toThrow();
    expect(() => assertScheduleMatchesEngine(delay, intervention)).not.toThrow();
  });

  it("propagates a named delay through the canonical dependency chain", () => {
    // contested-evidence-protocolの5年遅延が下流のcross-observer-anomaly-drillsへ伝わり、
    // 発動年を2032から2037へ押し出す。上流のノードは動かない。
    expect(projectTechnologySchedule(intervention, { "contested-evidence-protocol": 5 })).toMatchObject({
      "federated-observation-probes": 2029,
      "contested-evidence-protocol": 2036,
      "cross-observer-anomaly-drills": 2037,
    });
    expect(projectActivationYear(intervention, {})).toBe(2032);
    expect(projectActivationYear(intervention, { "contested-evidence-protocol": 5 })).toBe(2037);
  });

  it("fails closed when a rendered schedule drifts from the engine projection", () => {
    // production のロード経路から外した再計算検査の移設先。
    expect(() => assertScheduleMatchesEngine(
      { ...normal, fork: { ...normal.fork, technology_schedule: { ...normal.fork.technology_schedule, "cross-observer-anomaly-drills": 2030 } } },
      intervention,
    )).toThrow(/technology schedule/);
    expect(() => assertScheduleMatchesEngine(
      { ...normal, fork: { ...normal.fork, activation_year: 2031 } },
      intervention,
    )).toThrow(/activation year/);
    expect(() => assertScheduleMatchesEngine(
      { ...delay, fork: { ...delay.fork, technology_delays: { "contested-evidence-protocol": 1 } } },
      intervention,
    )).toThrow(/technology schedule/);
  });
});

describe("cross-language metric delta", () => {
  it("reproduces the Python delta on both canonical artifacts", () => {
    for (const artifact of [parseComparisonArtifact(comparisonJson), parseComparisonArtifact(delayJson)]) {
      for (const key of metricKeys) {
        const projected = Number(
          (artifact.fork.state_at_comparison_year[key] - artifact.baseline.state_at_comparison_year[key]).toFixed(2),
        );
        expect(projected).toBe(artifact.state_delta_at_comparison_year[key]);
      }
    }
  });

  it("keeps the delta projection out of production because toFixed is not Python round", () => {
    // Pythonのround()は偶数丸め、JavaScriptのtoFixed()は0から遠い側へ丸める。
    // 実測: round(0.125, 2) は 0.12 / round(-0.125, 2) は -0.12 を返す。
    // production で再計算すると、この境目に落ちた正しいPython出力を誤ってrejectしうる。
    expect(Number((0.125).toFixed(2))).toBe(0.13);
    expect(Number((-0.125).toFixed(2))).toBe(-0.13);
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
