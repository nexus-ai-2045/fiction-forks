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
  const bytes = Buffer.from(JSON.stringify(artifact));
  const digest = createHash("sha256").update(bytes).digest("hex");
  const comparisonPath = join(runs, "haruhi-world-observation-comparison.json");
  const delayPath = join(runs, "haruhi-world-observation-contestation-delay.json");
  await writeFile(comparisonPath, bytes);
  await writeFile(delayPath, bytes);
  const interventionBytes = Buffer.from(JSON.stringify({ id: "intervention" }));
  const interventionDigest = createHash("sha256").update(interventionBytes).digest("hex");
  await writeFile(join(interventions, "haruhi-world-observation.json"), interventionBytes);
  await writeFile(join(runs, "haruhi-world-observation-fixture.manifest.json"), JSON.stringify({
    schema_version: "fiction_forks_run_manifest.v1",
    run_kind: "fixture",
    ai_measured: false,
    replay_equivalent: true,
    engine_version: "0.3.0",
    scenario_id: "scenario",
    intervention_id: "intervention",
    seed: 2036,
    comparison_artifact_path: "artifacts/runs/haruhi-world-observation-comparison.json",
    comparison_artifact_sha256: digest,
    delay_artifact_path: "artifacts/runs/haruhi-world-observation-contestation-delay.json",
    delay_artifact_sha256: digest,
    intervention_artifact_path: "interventions/haruhi-world-observation.json",
    intervention_artifact_sha256: interventionDigest,
  }));
  await verifyWorkbenchAssets(root);
  await writeFile(delayPath, JSON.stringify({ ...artifact, seed: 2037 }));
  await assert.rejects(verifyWorkbenchAssets(root), /SHA-256/);
  await writeFile(delayPath, bytes);
  await writeFile(join(interventions, "haruhi-world-observation.json"), JSON.stringify({ id: "changed" }));
  await assert.rejects(verifyWorkbenchAssets(root), /SHA-256/);
});
