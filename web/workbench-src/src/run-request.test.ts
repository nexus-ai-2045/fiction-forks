import catalogFile from "../../../catalogs/intervention-templates.v1.json";
import fixture from "../../../artifacts/runs/haruhi-world-observation-fixture.json";
import { DEFAULT_TEMPLATE_ID, buildLocalRunRequest, parseLocalRunCatalog, parseLocalRunResponse, requestLocalRun } from "./run-request";

const healthTemplate = {
  template_id: DEFAULT_TEMPLATE_ID,
  template_version: 3,
  scenario_id: "japan-2036-centralization",
  intervention_id: "haruhi-world-observation",
  intervention_sha256: "6b9420240ae02129b4fd24f679aef0a9e79dbd53dca052f58700e1a7d5c79d70",
  abstract_function: "複数の独立観測と異議申立てで世界状態の変化を検証する",
  allowed_seeds: [2036],
  delay_profiles: ["none"],
};

const health = {
  status: "ready",
  schema_version: "fiction_forks_local_run_response.v1",
  providers: ["fixture"],
  catalog_id: "japan-2036-preview-templates",
  catalog_version: 3,
  templates: [healthTemplate],
};

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
  it("blames the right side for each adapter status", async () => {
    const catalog = parseLocalRunCatalog(health);
    const request = buildLocalRunRequest(catalog, catalog.templates[0], "fixture", 2036, false);
    const original = globalThis.fetch;
    // adapterはrequest違反(400)、server側の失敗(500)、実行中(409)を別statusで返す。
    // 未マップのstatusは「接続できませんでした」へ落ちるため、誰のせいかが逆転する。
    const expected: Record<number, RegExp> = {
      400: /契約と一致しません/,
      403: /session token/,
      409: /実行中/,
      413: /大きすぎます/,
      415: /形式が不正/,
      500: /シミュレーター側で実行に失敗/,
    };
    try {
      for (const [status, pattern] of Object.entries(expected)) {
        globalThis.fetch = (async () => new Response(null, { status: Number(status) })) as typeof fetch;
        await expect(requestLocalRun(request, "token")).rejects.toThrow(pattern);
        await expect(requestLocalRun(request, "token")).rejects.not.toThrow(/接続できませんでした/);
      }
    } finally {
      globalThis.fetch = original;
    }
  });

  it("builds a participation run request inside the transport envelope", () => {
    const catalog = parseLocalRunCatalog(health);
    expect(buildLocalRunRequest(catalog, catalog.templates[0], "fixture", 2036, false)).toEqual({
      schema_version: "fiction_forks_local_run_request.v2",
      run_request: {
        schema_version: "fiction_forks_provisional_run_request.v1",
        scenario_id: "japan-2036-centralization",
        template_id: DEFAULT_TEMPLATE_ID,
        template_version: 3,
        catalog_id: "japan-2036-preview-templates",
        catalog_version: 3,
        intervention_id: "haruhi-world-observation",
        intervention_sha256: healthTemplate.intervention_sha256,
        seed: 2036,
        delay_profile: "none",
        user_confirmed: true,
      },
      execution: { provider_id: "fixture", confirm_live: false },
    });
    expect(() => buildLocalRunRequest(catalog, catalog.templates[0], "vertex", 2036, false)).toThrow(/明示確認/);
    expect(() => buildLocalRunRequest(catalog, catalog.templates[0], "fixture", 2036, true)).toThrow(/live確認/);
    expect(() => buildLocalRunRequest(catalog, catalog.templates[0], "fixture", 9999, false)).toThrow(/許可されたseed/);
    expect(buildLocalRunRequest(catalog, catalog.templates[0], "vertex", 2036, true).execution.confirm_live).toBe(true);
  });

  it("fails closed when the adapter health projection is not a catalog", () => {
    expect(() => parseLocalRunCatalog({})).toThrow(/ready/);
    expect(() => parseLocalRunCatalog({ ...health, templates: [] })).toThrow(/template/);
    expect(() => parseLocalRunCatalog({ ...health, templates: [{ ...healthTemplate, intervention_sha256: "zz" }] })).toThrow(/intervention_sha256/);
    expect(() => parseLocalRunCatalog({ ...health, templates: [{ ...healthTemplate, intervention_path: "interventions/x.json" }] })).toThrow(/項目が契約と一致しません/);
  });

  it("keeps the default template inside the reviewed catalog", () => {
    const ids = catalogFile.templates.map((entry) => entry.template_id);
    expect(ids).toContain(DEFAULT_TEMPLATE_ID);
    for (const entry of health.templates) expect(ids).toContain(entry.template_id);
    const reviewed = catalogFile.templates.find((entry) => entry.template_id === DEFAULT_TEMPLATE_ID);
    expect(reviewed?.template_version).toBe(healthTemplate.template_version);
    expect(reviewed?.intervention_sha256).toBe(healthTemplate.intervention_sha256);
    expect(catalogFile.catalog_version).toBe(health.catalog_version);
    expect(catalogFile.catalog_id).toBe(health.catalog_id);
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
