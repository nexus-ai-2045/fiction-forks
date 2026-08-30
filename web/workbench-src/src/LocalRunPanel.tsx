import { useEffect, useState } from "react";
import { ReplaySection } from "./Replay";
import { buildLocalRunRequest, requestLocalRun, type LocalProvider, type VerifiedLocalRun } from "./run-request";

export function LocalRunPanel() {
  const [provider, setProvider] = useState<LocalProvider>("fixture");
  const [providers, setProviders] = useState<string[]>([]);
  const [token, setToken] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [verified, setVerified] = useState<VerifiedLocalRun | null>(null);
  const [adapterStatus, setAdapterStatus] = useState<"checking" | "ready" | "unavailable">("checking");

  useEffect(() => {
    let active = true;
    fetch("/api/health").then((response) => response.ok ? response.json() : Promise.reject())
      .then((value: unknown) => {
        const health = typeof value === "object" && value !== null ? value as { status?: unknown; providers?: unknown } : null;
        if (!active) return;
        if (health?.status !== "ready" || !Array.isArray(health.providers) || !health.providers.includes("fixture")) {
          setProviders([]); setAdapterStatus("unavailable"); return;
        }
        setProviders(health.providers.filter((item): item is string => typeof item === "string"));
        setAdapterStatus("ready");
      }).catch(() => { if (active) { setProviders([]); setAdapterStatus("unavailable"); } });
    return () => { active = false; };
  }, []);

  const live = provider !== "fixture";
  const granted = providers.includes(provider);
  const adapterReady = adapterStatus === "ready";
  const submit = async () => {
    if (pending) return;
    setPending(true); setError(""); setVerified(null);
    try {
      setVerified(await requestLocalRun(buildLocalRunRequest(provider, 2036, confirmed), token));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "シミュレーター実行に失敗しました。");
    } finally { setPending(false); }
  };

  return <section className="local-run" aria-labelledby="local-run-title">
    <div className="section-heading"><div><span>RUN / CANONICAL SIMULATOR</span><h2 id="local-run-title">この世界線を、いま実行する。</h2></div><p>既存Python runtimeを呼び出し、run・replay・evidenceを同じrun_idで検証します。</p></div>
    <label>実行環境<select value={provider} onChange={(event) => { setProvider(event.target.value as LocalProvider); setConfirmed(false); }}><option value="fixture">Fixture（外部AI通信なし）</option><option value="ollama">Ollama（ローカルAI）</option><option value="vertex">Vertex AI（Google Cloud）</option></select></label>
    <label>Session token<input type="password" autoComplete="off" value={token} onChange={(event) => setToken(event.target.value)} /></label>
    {adapterStatus === "checking" && <p className="run-status">ローカルadapterを確認しています…</p>}
    {adapterStatus === "unavailable" && <p className="run-warning">このページではローカルadapterに接続できません。手元でadapterを起動したページから実行してください。</p>}
    {live && <label><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />外部AIを実行し、通信が発生することを確認しました</label>}
    {live && !granted && <p className="run-warning">このproviderはadapter起動時に許可されていません。</p>}
    <button type="button" onClick={submit} disabled={pending || !adapterReady || !token || (live && (!confirmed || !granted))}>{pending ? "実行中…" : "シミュレーションを実行"}</button>
    <div aria-live="polite">{error && <p role="alert">{error}</p>}{verified && <p className="run-success"><b>検証成功</b> run_id {verified.run_id}<br />execution_id {verified.execution_id}<br />{verified.replay.events.length} events / hash-chain PASS / bundle PASS</p>}</div>
    {verified && <ReplaySection run={verified.replay} titleId="local-run-replay-title" generated />}
  </section>;
}
