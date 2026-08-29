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
  return manifest;
}

if (resolve(process.argv[1] ?? "") === fileURLToPath(import.meta.url)) {
  const root = resolve(import.meta.dirname, "..");
  await verifyWorkbenchAssets(root);
  process.stdout.write("workbench asset provenance OK\n");
}
