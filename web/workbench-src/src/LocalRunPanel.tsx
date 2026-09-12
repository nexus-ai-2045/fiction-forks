import { useEffect, useRef, useState } from "react";
import { ReplaySection } from "./Replay";
import { DEFAULT_TEMPLATE_ID, buildLocalRunRequest, parseLocalRunCatalog, requestLocalRun, type LocalProvider, type LocalRunCatalog, type VerifiedLocalRun } from "./run-request";

export function LocalRunPanel() {
  const [provider, setProvider] = useState<LocalProvider>("fixture");
  const [catalog, setCatalog] = useState<LocalRunCatalog | null>(null);
  const [templateId, setTemplateId] = useState(DEFAULT_TEMPLATE_ID);
  const [token, setToken] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [verified, setVerified] = useState<VerifiedLocalRun | null>(null);
  const [adapterStatus, setAdapterStatus] = useState<"checking" | "ready" | "unavailable">("checking");
  // template切替や再実行で古いresponseを捨てるための世代カウンタ。
  const requestGeneration = useRef(0);

  useEffect(() => {
    let active = true;
    fetch("/api/health").then((response) => response.ok ? response.json() : Promise.reject())
      .then((value: unknown) => {
        if (!active) return;
        const parsed = parseLocalRunCatalog(value);
        // 既定templateは配列順ではなく明示固定にする（実行の決定性のため）。
        const fallback = parsed.templates.find((item) => item.template_id === DEFAULT_TEMPLATE_ID) ?? parsed.templates[0];
        setCatalog(parsed); setTemplateId(fallback.template_id); setAdapterStatus("ready");
      }).catch(() => { if (active) { setCatalog(null); setAdapterStatus("unavailable"); } });
    return () => { active = false; };
  }, []);

  const live = provider !== "fixture";
  const granted = catalog?.providers.includes(provider) ?? false;
  const selected = catalog?.templates.find((item) => item.template_id === templateId) ?? null;
  const adapterReady = adapterStatus === "ready" && catalog !== null && selected !== null;

  const discardStaleResults = () => {
    requestGeneration.current += 1;
    setVerified(null);
    setError("");
    setPending(false);
  };

  const onTemplateChange = (next: string) => {
    if (next === templateId) return;
    discardStaleResults();
    setTemplateId(next);
  };

  const submit = async () => {
    if (pending || !catalog || !selected) return;
    const generation = ++requestGeneration.current;
    const requestedInterventionId = selected.intervention_id;
    setPending(true); setError(""); setVerified(null);
    try {
      const result = await requestLocalRun(buildLocalRunRequest(catalog, selected, provider, selected.allowed_seeds[0], confirmed), token);
      if (generation !== requestGeneration.current) return;
      const runRequest = result.bundle["run_request"];
      const parameters =
        typeof runRequest === "object" && runRequest !== null && !Array.isArray(runRequest)
          ? (runRequest as Record<string, unknown>)["parameters"]
          : undefined;
      const bundleIntervention =
        typeof parameters === "object" && parameters !== null && !Array.isArray(parameters)
          ? (parameters as Record<string, unknown>)["intervention_id"]
          : undefined;
      // bundleがある応答は intervention_id で request identity へ束縛する。
      if (
        typeof bundleIntervention === "string"
        && bundleIntervention !== requestedInterventionId
      ) {
        throw new Error("応答が選択中の世界線と一致しません。もう一度実行してください。");
      }
      setVerified(result);
    } catch (cause) {
      if (generation !== requestGeneration.current) return;
      setError(cause instanceof Error ? cause.message : "シミュレーター実行に失敗しました。");
    } finally {
      if (generation === requestGeneration.current) setPending(false);
    }
  };

  return <section className="local-run" aria-labelledby="local-run-title">
    <div className="section-heading"><div><span>RUN / CANONICAL SIMULATOR</span><h2 id="local-run-title">この世界線を、いま実行する。</h2></div><p>既存Python runtimeを呼び出し、run・replay・evidenceを同じrun_idで検証します。</p></div>
    {catalog && <label>世界線template<select aria-label="世界線template" value={templateId} onChange={(event) => onTemplateChange(event.target.value)}>{catalog.templates.map((item) => <option key={item.template_id} value={item.template_id}>{item.abstract_function}</option>)}</select></label>}
    <label>実行環境<select value={provider} onChange={(event) => { setProvider(event.target.value as LocalProvider); setConfirmed(false); discardStaleResults(); }}><option value="fixture">Fixture（外部AI通信なし）</option><option value="ollama">Ollama（ローカルAI）</option><option value="vertex">Vertex AI（Google Cloud）</option></select></label>
    <label>Session token<input type="password" autoComplete="off" value={token} onChange={(event) => setToken(event.target.value)} /></label>
    {adapterStatus === "checking" && <p className="run-status">ローカルadapterを確認しています…</p>}
    {adapterStatus === "unavailable" && <p className="run-warning">このページではローカルadapterに接続できません。手元でadapterを起動したページから実行してください。</p>}
    {selected && <p className="run-status">template {selected.template_id} v{selected.template_version} / intervention {selected.intervention_id} / SHA-256 {selected.intervention_sha256}</p>}
    {live && <label><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />外部AIを実行し、通信が発生することを確認しました</label>}
    {live && !granted && <p className="run-warning">このproviderはadapter起動時に許可されていません。</p>}
    <button type="button" onClick={submit} disabled={pending || !adapterReady || !token || (live && (!confirmed || !granted))}>{pending ? "実行中…" : "シミュレーションを実行"}</button>
    <div aria-live="polite">{error && <p role="alert">{error}</p>}{verified && <p className="run-success"><b>検証成功</b> run_id {verified.run_id}<br />execution_id {verified.execution_id}<br />{verified.replay.events.length} events / hash-chain PASS / bundle PASS</p>}</div>
    {verified && <ReplaySection run={verified.replay} titleId="local-run-replay-title" generated />}
  </section>;
}
