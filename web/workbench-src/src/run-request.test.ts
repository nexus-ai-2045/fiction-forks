import fixture from "../../../artifacts/runs/haruhi-world-observation-fixture.json";
import { buildLocalRunRequest, parseLocalRunResponse } from "./run-request";

function responseFixture() {
  const runId = fixture.run_id;
  return {
    schema_version: "fiction_forks_local_run_response.v1",
    run_id: runId,
    execution_id: `ffx-${"1".repeat(32)}`,
    provider: { name: "fixture", model: null },
    source_revision: "2".repeat(40),
    result_sha256: "3".repeat(64),
    bundle_sha256: "4".repeat(64),
    result: structuredClone(fixture),
    bundle: {
      schema: "meta-security-run-bundle/v1",
      run_request: { run_id: runId },
      events: fixture.actions.map((receipt, sequence) => ({ run_id: runId, sequence, payload: { receipt } })),
      replay: { run_id: runId, seed: fixture.seed, event_count: fixture.actions.length },
      evidence: { run_id: runId },
    },
  };
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
    const parsed = await parseLocalRunResponse(responseFixture());
    expect(parsed.run_id).toBe(fixture.run_id);
    expect(parsed.replay.events).toHaveLength(fixture.actions.length);
  });

  it("fails closed for response and bundle relationship drift", async () => {
    const changedRun = responseFixture();
    changedRun.result.run_id = "ff-other";
    await expect(parseLocalRunResponse(changedRun)).rejects.toThrow(/resultのrun_id/);

    const changedBundle = responseFixture();
    changedBundle.bundle.evidence.run_id = "ff-other";
    await expect(parseLocalRunResponse(changedBundle)).rejects.toThrow(/evidence.*run_id/);

    const changedOrder = responseFixture();
    changedOrder.bundle.events[0].sequence = 1;
    await expect(parseLocalRunResponse(changedOrder)).rejects.toThrow(/event順序/);

    const changedReceipt = responseFixture();
    changedReceipt.bundle.events[0].payload.receipt.action.action_id = "tampered";
    await expect(parseLocalRunResponse(changedReceipt)).rejects.toThrow(/result action/);
  });
});
