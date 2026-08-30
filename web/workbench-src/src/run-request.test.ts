import fixture from "../../../artifacts/runs/haruhi-world-observation-fixture.json";
import { buildLocalRunRequest, parseLocalRunResponse } from "./run-request";

async function artifact(value: unknown) {
  const bytes = new TextEncoder().encode(JSON.stringify(value));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return {
    base64: btoa(String.fromCharCode(...bytes)),
    sha256: Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join(""),
  };
}

async function responseFixture() {
  const runId = fixture.run_id;
  const result = structuredClone(fixture);
  const bundle = {
    schema: "meta-security-run-bundle/v1",
    run_request: { run_id: runId },
    events: fixture.actions.map((receipt, sequence) => ({ run_id: runId, sequence, payload: { receipt: structuredClone(receipt) } })),
    replay: { run_id: runId, seed: fixture.seed, event_count: fixture.actions.length, event_stream_sha256: "" },
    evidence: { run_id: runId, event_stream_sha256: "" },
  };
  const streamBytes = new TextEncoder().encode(bundle.events.map((event) => JSON.stringify(event)).join("\n") + "\n");
  const streamDigest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", streamBytes)), (byte) => byte.toString(16).padStart(2, "0")).join("");
  bundle.replay.event_stream_sha256 = streamDigest;
  bundle.evidence.event_stream_sha256 = streamDigest;
  const [resultArtifact, bundleArtifact] = await Promise.all([artifact(result), artifact(bundle)]);
  return {
    schema_version: "fiction_forks_local_run_response.v1",
    run_id: runId,
    execution_id: `ffx-${"1".repeat(32)}`,
    provider: { name: "fixture", model: null },
    source_revision: "2".repeat(40),
    result_sha256: resultArtifact.sha256,
    bundle_sha256: bundleArtifact.sha256,
    result_artifact_base64: resultArtifact.base64,
    bundle_artifact_base64: bundleArtifact.base64,
    event_stream_base64: btoa(String.fromCharCode(...streamBytes)),
    result,
    bundle,
  };
}

async function refreshArtifacts(response: Awaited<ReturnType<typeof responseFixture>>) {
  const [resultArtifact, bundleArtifact] = await Promise.all([artifact(response.result), artifact(response.bundle)]);
  response.result_sha256 = resultArtifact.sha256;
  response.result_artifact_base64 = resultArtifact.base64;
  response.bundle_sha256 = bundleArtifact.sha256;
  response.bundle_artifact_base64 = bundleArtifact.base64;
}

describe("local simulator wire contract", () => {
  it("builds only the exact provider confirmation contract", () => {
    expect(buildLocalRunRequest("fixture", 2036, false)).toEqual({
      schema_version: "fiction_forks_local_run_request.v1",
      worldline_id: "haruhi-world-observation",
      provider: "fixture",
      seed: 2036,
      confirm_live: false,
    });
    expect(() => buildLocalRunRequest("vertex", 2036, false)).toThrow(/明示確認/);
    expect(buildLocalRunRequest("vertex", 2036, true).confirm_live).toBe(true);
  });

  it("accepts a response whose run, replay and evidence share one identity", async () => {
    const parsed = await parseLocalRunResponse(await responseFixture());
    expect(parsed.run_id).toBe(fixture.run_id);
    expect(parsed.replay.events).toHaveLength(fixture.actions.length);
  });

  it("fails closed for response and bundle relationship drift", async () => {
    const changedRun = await responseFixture();
    changedRun.result.run_id = "ff-other";
    await refreshArtifacts(changedRun);
    await expect(parseLocalRunResponse(changedRun)).rejects.toThrow(/resultのrun_id/);

    const changedBundle = await responseFixture();
    changedBundle.bundle.evidence.run_id = "ff-other";
    await refreshArtifacts(changedBundle);
    await expect(parseLocalRunResponse(changedBundle)).rejects.toThrow(/evidence.*run_id/);

    const changedOrder = await responseFixture();
    changedOrder.bundle.events[0].sequence = 1;
    await refreshArtifacts(changedOrder);
    await expect(parseLocalRunResponse(changedOrder)).rejects.toThrow(/event順序/);

    const changedReceipt = await responseFixture();
    changedReceipt.bundle.events[0].payload.receipt.action.action_id = "tampered";
    await refreshArtifacts(changedReceipt);
    await expect(parseLocalRunResponse(changedReceipt)).rejects.toThrow(/result action/);

    const changedDigest = await responseFixture();
    changedDigest.bundle.events[0].sequence = 1;
    changedDigest.bundle_artifact_base64 = changedDigest.bundle_artifact_base64.slice(0, -4) + "AAAA";
    await expect(parseLocalRunResponse(changedDigest)).rejects.toThrow(/artifact SHA-256/);
  });
});
