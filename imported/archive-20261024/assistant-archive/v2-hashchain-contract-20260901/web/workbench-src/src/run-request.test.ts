import fixture from "../../../artifacts/runs/haruhi-world-observation-fixture.json";
import { canonicalizeRfc8785 } from "./contract";
import { buildLocalRunRequest, parseLocalRunResponse, requestLocalRun } from "./run-request";

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
  // 正本 (local_adapter.py) は RFC 8785 + 行末改行で event stream を作る。
  // JSON.stringify ではキー順が挿入順のままで、実adapterの出力と別物になる。
  const streamBytes = new TextEncoder().encode(bundle.events.map((event) => canonicalizeRfc8785(event)).join("\n") + "\n");
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

  // digestと構造が揃っていても、バイト列がcanonicalでなければ拒否する。
  // 期待値は Python 側 rfc8785.dumps の実出力で固定している (2026-09-01 実測)。
  it("requires the event stream bytes to be RFC 8785 canonical", async () => {
    expect(canonicalizeRfc8785({
      run_id: "ff-abc",
      sequence: 0,
      event_type: "social.action.committed",
      occurred_at: "2026-08-30T07:42:00.786302Z",
      payload: { receipt: { confidence: 1.0, ratio: 1e-7, zero: -0.0, big: 1e16, note: "日本語", flag: true, nil: null } },
    })).toBe('{"event_type":"social.action.committed","occurred_at":"2026-08-30T07:42:00.786302Z","payload":{"receipt":{"big":10000000000000000,"confidence":1,"flag":true,"nil":null,"note":"日本語","ratio":1e-7,"zero":0}},"run_id":"ff-abc","sequence":0}');

    const nonCanonical = await responseFixture();
    // キー順だけを挿入順へ戻す。digestも構造も辻褄を合わせたうえで通らないことを見る。
    const bytes = new TextEncoder().encode(nonCanonical.bundle.events.map((event) => JSON.stringify(event)).join("\n") + "\n");
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (byte) => byte.toString(16).padStart(2, "0")).join("");
    nonCanonical.event_stream_base64 = btoa(String.fromCharCode(...bytes));
    nonCanonical.bundle.replay.event_stream_sha256 = digest;
    nonCanonical.bundle.evidence.event_stream_sha256 = digest;
    await refreshArtifacts(nonCanonical);
    await expect(parseLocalRunResponse(nonCanonical)).rejects.toThrow(/canonical/);
  });
});

// 接続不能・timeout・非JSONは、ブラウザ由来の英語やstackを画面へ出さない。
describe("local simulator transport errors", () => {
  const request = buildLocalRunRequest("fixture", 2036, false);
  afterEach(() => { vi.unstubAllGlobals(); });

  it("reports a Japanese message when the adapter is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(requestLocalRun(request, "token")).rejects.toThrow("シミュレーターへ接続できませんでした。adapterが起動しているか確認してください。");
  });

  it("reports a Japanese message when the adapter stops responding", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("timed out", "TimeoutError")));
    await expect(requestLocalRun(request, "token")).rejects.toThrow("シミュレーターの応答がありません。実行が長引いているか、adapterが停止しています。");
  });

  it("passes an abort signal so a hung adapter cannot pin the UI in pending", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);
    await expect(requestLocalRun(request, "token")).rejects.toThrow();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/runs");
    expect(fetchMock.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
  });

  it("does not leak a parser stack when the adapter returns non-JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: () => Promise.reject(new SyntaxError("Unexpected token < in JSON at position 0")) }));
    await expect(requestLocalRun(request, "token")).rejects.toThrow("シミュレーターの応答を解釈できませんでした。");
  });

  it("keeps the session token out of the URL", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);
    await expect(requestLocalRun(request, "secret-token")).rejects.toThrow();
    expect(String(fetchMock.mock.calls[0][0])).not.toContain("secret-token");
    expect(fetchMock.mock.calls[0][1].headers["X-Fiction-Forks-Session"]).toBe("secret-token");
  });
});
