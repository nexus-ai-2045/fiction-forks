import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";

const expected = {
  artifact_path: "artifacts/runs/haruhi-world-observation-fixture.json",
  comparison_artifact_path: "artifacts/runs/haruhi-world-observation-comparison.json",
  delay_artifact_path: "artifacts/runs/haruhi-world-observation-contestation-delay.json",
  intervention_artifact_path: "interventions/haruhi-world-observation.json",
};

const expectedLiveSummaries = new Set([
  "artifacts/runs/ollama-live-run-summary.json",
  "artifacts/runs/vertex-live-run-summary.json",
]);

const sha256Pattern = /^[0-9a-f]{64}$/;
const revisionPattern = /^[0-9a-f]{40}$/;

async function verifyLiveRunSummaries(root) {
  const manifestPath = resolve(root, "artifacts/runs/live-run-summaries.manifest.json");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  if (manifest.schema_version !== "fiction_forks_live_run_manifest.v1" || !Array.isArray(manifest.summaries)) {
    throw new Error("live-run manifest has an unsupported schema");
  }
  const paths = new Set(manifest.summaries.map((entry) => entry.artifact_path));
  if (paths.size !== expectedLiveSummaries.size ||
      [...expectedLiveSummaries].some((path) => !paths.has(path))) {
    throw new Error("live-run manifest must name every canonical live summary exactly once");
  }
  for (const entry of manifest.summaries) {
    if (!expectedLiveSummaries.has(entry.artifact_path)) {
      throw new Error(`${entry.artifact_path} is not a canonical live summary`);
    }
    const bytes = await readFile(resolve(root, entry.artifact_path));
    const actual = createHash("sha256").update(bytes).digest("hex");
    if (!sha256Pattern.test(entry.artifact_sha256) || actual !== entry.artifact_sha256) {
      throw new Error(`${entry.artifact_path} SHA-256 does not match the canonical live-run manifest`);
    }
    const summary = JSON.parse(bytes.toString("utf8"));
    if (summary.schema_version !== "fiction_forks_live_run_summary.v1") {
      throw new Error(`${entry.artifact_path} has an unsupported summary schema`);
    }
    for (const key of ["run_id", "provider", "model", "seed", "runtime_revision", "result_sha256", "event_stream_sha256"]) {
      if (summary[key] !== entry[key]) {
        throw new Error(`${entry.artifact_path} ${key} does not match the canonical live-run manifest`);
      }
    }
    if (!revisionPattern.test(summary.runtime_revision) || !sha256Pattern.test(summary.result_sha256) ||
        !sha256Pattern.test(summary.event_stream_sha256)) {
      throw new Error(`${entry.artifact_path} contains malformed provenance digests`);
    }
    if (!Array.isArray(summary.turns) || summary.event_count !== summary.turns.length ||
        summary.valid_action_count !== summary.turns.filter((turn) => turn.valid === true).length ||
        summary.invalid_action_count !== summary.turns.filter((turn) => turn.valid === false).length ||
        summary.event_count !== summary.valid_action_count + summary.invalid_action_count) {
      throw new Error(`${entry.artifact_path} action counts do not match its event rows`);
    }
    if (summary.turns.some((turn) => turn.turn !== 1 && turn.turn !== 2 && turn.turn !== 3)) {
      throw new Error(`${entry.artifact_path} contains an invalid event turn`);
    }
    if (summary.replay_verified !== true || summary.bundle_contract_verified !== true) {
      throw new Error(`${entry.artifact_path} is not replay and bundle verified`);
    }
  }
  return manifest;
}

export async function verifyWorkbenchAssets(root) {
  const manifestPath = resolve(root, "artifacts/runs/haruhi-world-observation-fixture.manifest.json");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  if (manifest.schema_version !== "fiction_forks_run_manifest.v1" || manifest.run_kind !== "fixture" ||
      manifest.ai_measured !== false || manifest.replay_equivalent !== true) {
    throw new Error("workbench manifest must be a replay-equivalent non-AI fixture");
  }
  const artifacts = {};
  for (const [pathKey, relativePath] of Object.entries(expected)) {
    if (manifest[pathKey] !== relativePath) throw new Error(`${pathKey} does not name the canonical workbench artifact`);
    const bytes = await readFile(resolve(root, relativePath));
    const actual = createHash("sha256").update(bytes).digest("hex");
    const hashKey = pathKey.replace("_path", "_sha256");
    if (actual !== manifest[hashKey]) throw new Error(`${relativePath} SHA-256 does not match the canonical manifest`);
    const artifact = JSON.parse(bytes.toString("utf8"));
    artifacts[pathKey] = artifact;
    if (pathKey === "intervention_artifact_path") {
      if (artifact.id !== manifest.intervention_id) throw new Error(`${relativePath} id does not match the canonical manifest`);
      continue;
    }
    for (const key of ["engine_version", "scenario_id", "intervention_id", "seed"]) {
      if (artifact[key] !== manifest[key]) throw new Error(`${relativePath} ${key} does not match the canonical manifest`);
    }
  }
  const normalizeComparison = (artifact) => {
    const normalized = structuredClone(artifact);
    normalized.fork.technology_delays = Object.fromEntries(
      Object.entries(normalized.fork.technology_delays).filter(([, years]) => years !== 0),
    );
    return normalized;
  };
  if (!isDeepStrictEqual(
    normalizeComparison(artifacts.artifact_path.world_comparison),
    normalizeComparison(artifacts.comparison_artifact_path),
  )) {
    throw new Error("fixture world_comparison does not match the canonical normal comparison");
  }
  await verifyLiveRunSummaries(root);
  return manifest;
}

if (resolve(process.argv[1] ?? "") === fileURLToPath(import.meta.url)) {
  const root = resolve(import.meta.dirname, "..");
  await verifyWorkbenchAssets(root);
  process.stdout.write("workbench asset provenance OK\n");
}
