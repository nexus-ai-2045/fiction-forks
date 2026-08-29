import comparisonJson from "../../../artifacts/runs/haruhi-world-observation-comparison.json";
import delayJson from "../../../artifacts/runs/haruhi-world-observation-contestation-delay.json";
import interventionJson from "../../../interventions/haruhi-world-observation.json";
import manifestJson from "../../../artifacts/runs/haruhi-world-observation-fixture.manifest.json";
import { parseComparisonArtifact, parseInterventionArtifact, parseRunManifest, validateWorkbenchRelationships } from "./contract";

describe("canonical comparison artifacts", () => {
  it("accepts the normal and named-delay fixtures", () => {
    expect(parseComparisonArtifact(comparisonJson).fork.activation_year).toBe(2032);
    expect(parseComparisonArtifact(delayJson).fork.activation_year).toBe(2037);
  });

  it("fails closed for unknown contracts", () => {
    expect(() => parseComparisonArtifact({ ...comparisonJson, schema_version: "v2" })).toThrow(/schema_version/);
    expect(() => parseInterventionArtifact({ ...interventionJson, schema_version: "v2" })).toThrow(/schema_version/);
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
  });
});
