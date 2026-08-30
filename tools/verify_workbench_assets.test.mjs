import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { verifyWorkbenchAssets } from "./verify_workbench_assets.mjs";

test("asset verifier rejects content drift against the manifest", async () => {
  const root = await mkdtemp(join(tmpdir(), "fiction-forks-assets-"));
  const runs = join(root, "artifacts", "runs");
  const interventions = join(root, "interventions");
  await mkdir(runs, { recursive: true });
  await mkdir(interventions, { recursive: true });
  const artifact = { engine_version: "0.3.0", scenario_id: "scenario", intervention_id: "intervention", seed: 2036 };
  const comparison = { ...artifact, baseline: { score: 1 }, fork: { score: 2, technology_delays: {} } };
  const comparisonBytes = Buffer.from(JSON.stringify(comparison));
  const comparisonDigest = createHash("sha256").update(comparisonBytes).digest("hex");
  const delayBytes = Buffer.from(JSON.stringify(artifact));
  const delayDigest = createHash("sha256").update(delayBytes).digest("hex");
  const fixture = { ...artifact, world_comparison: { ...comparison, fork: { ...comparison.fork, technology_delays: { node: 0 } } } };
  const fixtureBytes = Buffer.from(JSON.stringify(fixture));
  const fixtureDigest = createHash("sha256").update(fixtureBytes).digest("hex");
  const comparisonPath = join(runs, "haruhi-world-observation-comparison.json");
  const delayPath = join(runs, "haruhi-world-observation-contestation-delay.json");
  const fixturePath = join(runs, "haruhi-world-observation-fixture.json");
  await writeFile(fixturePath, fixtureBytes);
  await writeFile(comparisonPath, comparisonBytes);
  await writeFile(delayPath, delayBytes);
  const interventionBytes = Buffer.from(JSON.stringify({ id: "intervention" }));
  const interventionDigest = createHash("sha256").update(interventionBytes).digest("hex");
  await writeFile(join(interventions, "haruhi-world-observation.json"), interventionBytes);
  const manifest = {
    schema_version: "fiction_forks_run_manifest.v1",
    run_kind: "fixture",
    ai_measured: false,
    replay_equivalent: true,
    engine_version: "0.3.0",
    scenario_id: "scenario",
    intervention_id: "intervention",
    seed: 2036,
    artifact_path: "artifacts/runs/haruhi-world-observation-fixture.json",
    artifact_sha256: fixtureDigest,
    comparison_artifact_path: "artifacts/runs/haruhi-world-observation-comparison.json",
    comparison_artifact_sha256: comparisonDigest,
    delay_artifact_path: "artifacts/runs/haruhi-world-observation-contestation-delay.json",
    delay_artifact_sha256: delayDigest,
    intervention_artifact_path: "interventions/haruhi-world-observation.json",
    intervention_artifact_sha256: interventionDigest,
  };
  const manifestPath = join(runs, "haruhi-world-observation-fixture.manifest.json");
  await writeFile(manifestPath, JSON.stringify(manifest));
  const makeLiveSummary = (provider, model) => ({
    schema_version: "fiction_forks_live_run_summary.v1",
    run_id: "ff-0123456789abcdef",
    provider,
    model,
    seed: 2036,
    runtime_revision: "1".repeat(40),
    result_sha256: "2".repeat(64),
    event_stream_sha256: "3".repeat(64),
    event_count: 1,
    valid_action_count: 1,
    invalid_action_count: 0,
    interaction_edge_count: 0,
    replay_verified: true,
    bundle_contract_verified: true,
    turns: [{ turn: 1, agent_id: "observer", action_id: "observe", valid: true, response_count: 0 }],
  });
  const liveEntries = [];
  for (const [provider, model] of [["ollama", "local-model"], ["vertex", "cloud-model"]]) {
    const artifactPath = `artifacts/runs/${provider}-live-run-summary.json`;
    const bytes = Buffer.from(JSON.stringify(makeLiveSummary(provider, model)));
    await writeFile(join(runs, `${provider}-live-run-summary.json`), bytes);
    liveEntries.push({
      artifact_path: artifactPath,
      artifact_sha256: createHash("sha256").update(bytes).digest("hex"),
      run_id: "ff-0123456789abcdef",
      provider,
      model,
      seed: 2036,
      runtime_revision: "1".repeat(40),
      result_sha256: "2".repeat(64),
      event_stream_sha256: "3".repeat(64),
    });
  }
  await writeFile(join(runs, "live-run-summaries.manifest.json"), JSON.stringify({
    schema_version: "fiction_forks_live_run_manifest.v1",
    summaries: liveEntries,
  }));
  await verifyWorkbenchAssets(root);
  await writeFile(join(runs, "vertex-live-run-summary.json"), JSON.stringify({
    ...makeLiveSummary("vertex", "cloud-model"),
    event_count: 2,
  }));
  await assert.rejects(verifyWorkbenchAssets(root), /SHA-256/);
  const vertexBytes = Buffer.from(JSON.stringify(makeLiveSummary("vertex", "cloud-model")));
  await writeFile(join(runs, "vertex-live-run-summary.json"), vertexBytes);
  await writeFile(delayPath, JSON.stringify({ ...artifact, seed: 2037 }));
  await assert.rejects(verifyWorkbenchAssets(root), /SHA-256/);
  await writeFile(delayPath, delayBytes);
  await writeFile(join(interventions, "haruhi-world-observation.json"), JSON.stringify({ id: "changed" }));
  await assert.rejects(verifyWorkbenchAssets(root), /SHA-256/);
  await writeFile(join(interventions, "haruhi-world-observation.json"), interventionBytes);
  await writeFile(fixturePath, JSON.stringify({ ...fixture, seed: 2037 }));
  await assert.rejects(verifyWorkbenchAssets(root), /SHA-256/);
  await writeFile(fixturePath, fixtureBytes);
  const driftedComparisonBytes = Buffer.from(JSON.stringify({ ...comparison, baseline: { score: 99 } }));
  await writeFile(comparisonPath, driftedComparisonBytes);
  await writeFile(manifestPath, JSON.stringify({
    ...manifest,
    comparison_artifact_sha256: createHash("sha256").update(driftedComparisonBytes).digest("hex"),
  }));
  await assert.rejects(verifyWorkbenchAssets(root), /world_comparison/);
});
