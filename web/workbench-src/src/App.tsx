import { useEffect, useRef, useState, type MouseEvent } from "react";
import ollamaLiveRun from "../../../artifacts/runs/ollama-live-run-summary.json";
import vertexLiveRun from "../../../artifacts/runs/vertex-live-run-summary.json";
import { comparison, contestationDelay, contestationDelayHeading, contestationDelayLabel, intervention, manifest } from "./data";
import { metricKeys, type ComparisonArtifact, type MetricKey, type TechnologyNode } from "./types";

const metricLabels: Record<MetricKey, string> = {
  cognitive_sovereignty: "認知主権",
  legitimacy: "正統性",
  living_systems: "生活基盤",
  repair_capacity: "修復能力",
  strategic_autonomy: "戦略的自律",
};

const kindLabels: Record<TechnologyNode["kind"], string> = {
  technology: "TECHNOLOGY",
  institution: "INSTITUTION",
  operations: "OPERATIONS",
};

type Profile = "normal" | "delay";
type LiveProvider = "ollama" | "vertex";

export function describeForkOutcome(artifact: ComparisonArtifact): { summary: string; status: string } {
  if (!artifact.fork.collapsed) {
    return {
      status: "このモデルでは破滅条件を回避",
      summary: `${artifact.fork.activation_year}年に発動し、${artifact.comparison_year}年の比較時点で破滅条件を回避。`,
    };
  }
  const collapseYear = artifact.fork.collapse_year ?? artifact.comparison_year;
  if (artifact.fork.activation_year > collapseYear) {
    return {
      status: "介入が間に合わない",
      summary: `発動が${artifact.fork.activation_year}年となり、${collapseYear}年の破滅条件に間に合いません。`,
    };
  }
  return {
    status: "介入後も破滅条件に到達",
    summary: `${artifact.fork.activation_year}年に発動しましたが、${collapseYear}年に修復不能条件へ到達。`,
  };
}

function StateMark({ collapsed }: { collapsed: boolean }) {
  return <span className={`state-mark ${collapsed ? "is-collapse" : "is-avoided"}`}>{collapsed ? "◆ 修復不能条件" : "○ 条件を回避"}</span>;
}

function MetricRows({ artifact }: { artifact: ComparisonArtifact }) {
  return <div className="metric-table" role="table" aria-label={`${artifact.comparison_year}年の5指標比較`}>
    <div className="metric-head" role="row"><span role="columnheader">指標</span><span role="columnheader">BASELINE</span><span role="columnheader">FORK</span><span role="columnheader">差分</span></div>
    {metricKeys.map((key) => {
      const delta = artifact.state_delta_at_comparison_year[key];
      return <div className="metric-row" role="row" key={key}>
        <strong role="rowheader">{metricLabels[key]}</strong>
        <span role="cell">{artifact.baseline.state_at_comparison_year[key]}</span>
        <span role="cell">{artifact.fork.state_at_comparison_year[key]}</span>
        <span role="cell" className={delta > 0 ? "positive" : delta < 0 ? "negative" : "neutral"}>{delta > 0 ? "+" : ""}{delta}</span>
      </div>;
    })}
  </div>;
}

function TechnologyTree({ artifact }: { artifact: ComparisonArtifact }) {
  return <section className="tree" aria-labelledby="tree-title">
    <div className="section-heading"><div><span>FORK / IMPLEMENTATION</span><h2 id="tree-title">発動までの実装ツリー</h2></div><p>各ノードの完成証拠を開いて確認できます。</p></div>
    <div className="node-list">
      {intervention.technology_tree.nodes.map((node) => <details className={`node node-${node.kind}`} key={node.id}>
        <summary>
          <span className="node-kind">{kindLabels[node.kind]}</span>
          <strong>{node.label}</strong>
          <span className="node-year">{artifact.fork.technology_schedule[node.id]} 完成</span>
        </summary>
        <div className="node-detail"><p><b>完成証拠</b>{node.completion_evidence}</p><p><b>依存</b>{node.depends_on.join(" / ")}</p></div>
      </details>)}
    </div>
  </section>;
}

function LiveRunEvidence() {
  const [provider, setProvider] = useState<LiveProvider>("vertex");
  const liveRun = provider === "vertex" ? vertexLiveRun : ollamaLiveRun;
  const isVertex = provider === "vertex";
  return <section className="live-run" aria-labelledby="live-run-title">
    <div className="section-heading"><div><span>LIVE AI / {isVertex ? "GOOGLE CLOUD VERTEX AI" : "LOCAL OLLAMA"}</span><h2 id="live-run-title">5役が3ターン、実際に選んだ。</h2></div><p>fixtureではなく、同じseedとaction契約で実モデルを動かした検証済み結果です。</p></div>
    <fieldset className="live-provider-picker"><legend>実行環境</legend>
      <label><input type="radio" name="live-provider" checked={provider === "vertex"} onChange={() => setProvider("vertex")} />Google Cloud / Gemini 2.5 Flash</label>
      <label><input type="radio" name="live-provider" checked={provider === "ollama"} onChange={() => setProvider("ollama")} />ローカル / Ollama</label>
    </fieldset>
    {isVertex && <p className="live-outcome">2037年に発動。2036年の破滅条件というビッグボスには1年間に合わなかった――次の世界線で倒すべき相手です。</p>}
    <div className="live-run-stats">
      <div><strong>{liveRun.event_count}</strong><span>生成行動</span></div><div><strong>{liveRun.valid_action_count}</strong><span>契約を通過</span></div><div><strong>{liveRun.invalid_action_count}</strong><span>安全に棄却</span></div><div><strong>{liveRun.interaction_edge_count}</strong><span>応答関係</span></div>
    </div>
    <div className="turn-grid" role="table" aria-label="実モデルの行動一覧">
      <div className="turn-head" role="row"><span role="columnheader">TURN</span><span role="columnheader">ROLE</span><span role="columnheader">ACTION</span><span role="columnheader">判定</span></div>
      {liveRun.turns.map((item) => <div className="turn-row" role="row" key={`${item.turn}:${item.agent_id}`}><span role="cell">{item.turn}</span><strong role="rowheader">{item.agent_id}</strong><span role="cell">{item.action_id}</span><span role="cell" className={item.valid ? "run-valid" : "run-rejected"}>{item.valid ? `VALID${item.response_count ? ` / 応答${item.response_count}` : ""}` : "REJECTED"}</span></div>)}
    </div>
    <p className="run-proof"><b>run_id</b> {liveRun.run_id} <b>model</b> {liveRun.model} <b>seed</b> {liveRun.seed}<br /><b>replay</b> {liveRun.replay_verified ? "PASS" : "未検証"} <b>bundle contract</b> {liveRun.bundle_contract_verified ? "PASS" : "未検証"}<br /><b>event SHA-256</b> {liveRun.event_stream_sha256}</p>
  </section>;
}

function ProvenanceDrawer({ open, onClose, artifact, replayVerified }: { open: boolean; onClose: () => void; artifact: ComparisonArtifact; replayVerified: boolean }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (open) closeRef.current?.focus(); }, [open]);
  if (!open) return null;
  return <div className="drawer-layer" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title" onKeyDown={(event) => {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab") {
        const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button, a[href], [tabindex]:not([tabindex="-1"])'));
        if (controls.length === 0) return;
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    }}>
      <button ref={closeRef} className="drawer-close" type="button" onClick={onClose} aria-label="根拠を閉じる">×</button>
      <span>EXPLAIN / PROVENANCE</span><h2 id="drawer-title">この比較の根拠と限界</h2>
      <dl className="provenance"><div><dt>artifact</dt><dd>{manifest.run_kind.toUpperCase()} / AI実測ではない</dd></div><div><dt>schema</dt><dd>{artifact.schema_version}</dd></div><div><dt>engine</dt><dd>{artifact.engine_version}</dd></div><div><dt>engine commit</dt><dd>{manifest.engine_commit}</dd></div><div><dt>scenario</dt><dd>{artifact.scenario_id}</dd></div><div><dt>intervention</dt><dd>{artifact.intervention_id}</dd></div><div><dt>seed</dt><dd>{artifact.seed}</dd></div><div><dt>comparison SHA-256</dt><dd>{manifest.comparison_artifact_sha256}</dd></div><div><dt>delay SHA-256</dt><dd>{manifest.delay_artifact_sha256}</dd></div><div><dt>intervention SHA-256</dt><dd>{manifest.intervention_artifact_sha256}</dd></div><div><dt>evidence</dt><dd>{replayVerified ? "fixture replay同値検証済み" : "canonical digest検証済み（replay未検証）"}</dd></div></dl>
      <h3>費用</h3><ul>{artifact.declared_costs.map((item) => <li key={item}>{item}</li>)}</ul>
      <h3>副作用</h3><ul>{artifact.declared_side_effects.map((item) => <li key={item}>{item}</li>)}</ul>
      <h3>失敗条件</h3><ul>{artifact.declared_failure_modes.map((item) => <li key={item}>{item}</li>)}</ul>
    </aside>
  </div>;
}

export function App() {
  const [profile, setProfile] = useState<Profile>("normal");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const explainButtonRef = useRef<HTMLButtonElement>(null);
  const artifact = profile === "normal" ? comparison : contestationDelay;
  const delayed = profile === "delay";
  const forkOutcome = describeForkOutcome(artifact);
  const baselineSummary = artifact.baseline.collapsed
    ? `${artifact.baseline.collapse_year ?? artifact.comparison_year}年に修復不能条件へ到達。`
    : `${artifact.comparison_year}年の比較時点では修復不能条件を回避。`;
  const livingSystemsDelta = comparison.state_delta_at_comparison_year.living_systems;
  const livingSystemsSummary = livingSystemsDelta === 0
    ? "変化なし"
    : `${Math.abs(livingSystemsDelta)}ポイント${livingSystemsDelta > 0 ? "改善" : "悪化"}`;

  const focusComparison = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    const target = document.getElementById("comparison");
    target?.focus();
    target?.scrollIntoView();
  };

  return <>
    <a className="skip-link" href="#comparison" onClick={focusComparison}>比較結果へ移動</a>
    <header className="topbar">
      <a className="brand" href="../"><span className="branch-glyph" aria-hidden="true">⑂</span><span>FICTION FORKS<small>WORLDLINE WORKBENCH</small></span></a>
      <nav aria-label="サイトナビゲーション"><a href="../">Idea Builder</a><a href="https://github.com/nexus-ai-2045/fiction-forks">GitHub</a></nav>
    </header>
    <main>
      <section className="hero">
        <div>
          <span className="fixture-label">FIXTURE / {artifact.comparison_year}</span>
          <h1>想像力で、破滅ルートをひっくり返せ。</h1>
          <p>アニメや物語のアイデアを、再現できる世界線シミュレーションへ。</p>
          <div className="hero-actions">
            <a href="#comparison" onClick={focusComparison}>世界線をプレイする</a>
            <a href="../">自分のアイデアを持ち込む</a>
          </div>
        </div>
        <div className="hero-status"><span>JAPAN {artifact.comparison_year} / BIG BOSS</span><StateMark collapsed={artifact.fork.collapsed} /><strong>{forkOutcome.status}</strong><small>破滅条件を倒すまで、世界線を何度でも組み替える。</small></div>
      </section>

      <section className="workflow" aria-label="作戦卓の流れ">
        {[["01", "OBSERVE", "放置世界を見る"], ["02", "FORK", "介入世界を比べる"], ["03", "STRESS", "制度を遅らせる"], ["04", "EXPLAIN", "根拠と限界を読む"]].map(([number, name, text]) => <div key={name}><span>{number}</span><strong>{name}</strong><small>{text}</small></div>)}
      </section>

      <section className="comparison" id="comparison" aria-labelledby="comparison-title" tabIndex={-1}>
        <div className="section-heading"><div><span>OBSERVE → FORK</span><h2 id="comparison-title">同じ{artifact.comparison_year}年、二つの世界</h2></div><p>未来予測ではなく、同じseedのモデル結果を比較しています。</p></div>
        <div className="worldline-summary">
          <article><span>BASELINE / 無介入</span><strong>{artifact.comparison_year}</strong><StateMark collapsed={artifact.baseline.collapsed} /><p>{baselineSummary}</p></article>
          <div className="fork-line" aria-hidden="true"><span></span></div>
          <article aria-label="介入世界" className={delayed ? "fork-world is-late" : "fork-world"}><span>FORK / {intervention.extracted_function}</span><strong>{artifact.fork.activation_year}</strong><StateMark collapsed={artifact.fork.collapsed} /><p>{forkOutcome.summary}</p></article>
        </div>
        <MetricRows artifact={artifact} />
      </section>

      <section className="stress" aria-labelledby="stress-title">
        <div><span>STRESS / NAMED PROFILE</span><h2 id="stress-title">{contestationDelayHeading}</h2><p>自由な数値入力ではなく、検証済みartifactに対応するnamed profileだけを切り替えます。</p></div>
        <fieldset><legend>遅延条件</legend>
          <label className={profile === "normal" ? "selected" : ""}><input type="radio" name="profile" value="normal" checked={profile === "normal"} onChange={() => setProfile("normal")} /><span><strong>遅延なし</strong>発動 {comparison.fork.activation_year} / {comparison.fork.collapsed ? "間に合わない" : "回避"}</span></label>
          <label className={profile === "delay" ? "selected" : ""}><input type="radio" name="profile" value="delay" checked={profile === "delay"} onChange={() => setProfile("delay")} /><span><strong>{contestationDelayLabel}</strong>発動 {contestationDelay.fork.activation_year} / {contestationDelay.fork.collapsed ? "間に合わない" : "回避"}</span></label>
        </fieldset>
        <p className="sr-only" aria-live="polite">{`${delayed ? contestationDelayLabel : "遅延なし"}: ${forkOutcome.summary}`}</p>
      </section>

      <TechnologyTree artifact={artifact} />

      <LiveRunEvidence />

      <section className="explain">
        <div><span>EXPLAIN</span><h2>改善だけでなく、代償も読む。</h2><p>生活基盤は通常介入で{livingSystemsSummary}。費用・副作用・失敗条件まで含めて初めて比較できます。</p></div>
        <button ref={explainButtonRef} type="button" onClick={() => setDrawerOpen(true)}>根拠と限界を開く <span aria-hidden="true">→</span></button>
      </section>
    </main>
    <footer><span>CANONICAL ARTIFACT — 同じseedで再現できる世界線比較</span><a href="../">自分のアイデアをIdea Builderで話す →</a></footer>
    <ProvenanceDrawer open={drawerOpen} onClose={() => { setDrawerOpen(false); requestAnimationFrame(() => explainButtonRef.current?.focus()); }} artifact={artifact} replayVerified={!delayed} />
  </>;
}
