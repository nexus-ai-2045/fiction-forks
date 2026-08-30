import { useEffect, useRef, useState } from "react";
import type { ReplayEvent, ReplayRun, ReplayStance } from "./types";

const stanceLabels: Record<ReplayStance, string> = {
  support: "支持",
  condition: "条件付き",
  oppose: "反対",
  abstain: "棄権",
};

const AUTOPLAY_INTERVAL_MS = 1800;

export function describeReplayEvent(event: ReplayEvent, total: number): string {
  const verdict = event.valid ? "契約を通過" : `安全に棄却（${event.invalid_reason}）`;
  const responds = event.action.responds_to.length > 0 ? `、応答先 ${event.action.responds_to.join(" / ")}` : "";
  return `行動 ${event.sequence} / ${total}: ターン${event.action.turn}の${event.action.agent_id}が${event.action.action_id}を選択（${stanceLabels[event.action.stance]}${responds}）— ${verdict}`;
}

export function ReplaySection({ run }: { run: ReplayRun }) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const reducedMotionRef = useRef(false);
  const total = run.events.length;
  const event = run.events[index];
  const atStart = index === 0;
  const atEnd = index === total - 1;

  useEffect(() => {
    const query = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!query) return;
    reducedMotionRef.current = query.matches;
    const onChange = (change: MediaQueryListEvent) => { reducedMotionRef.current = change.matches; };
    query.addEventListener?.("change", onChange);
    return () => query.removeEventListener?.("change", onChange);
  }, []);

  useEffect(() => {
    if (!playing) return;
    if (index >= total - 1) { setPlaying(false); return; }
    // reduced-motion環境では自動送りの間隔を延ばし、CSS側のtransitionはmedia queryで停止する。
    const interval = reducedMotionRef.current ? AUTOPLAY_INTERVAL_MS * 2 : AUTOPLAY_INTERVAL_MS;
    const timer = window.setTimeout(() => setIndex((current) => Math.min(current + 1, total - 1)), interval);
    return () => window.clearTimeout(timer);
  }, [playing, index, total]);

  const stop = () => setPlaying(false);
  const goTo = (next: number) => { stop(); setIndex(Math.min(Math.max(next, 0), total - 1)); };

  return <section className="replay" aria-labelledby="replay-title">
    <div className="section-heading">
      <div>
        <span>REPLAY / VERIFIED RUN</span>
        <h2 id="replay-title">保存済みの{total}行動を、一手ずつ再生する。</h2>
      </div>
      <p>これは検証済みrunのreplayです。いまAIが生成しているのではなく、保存済みeventを保存順のまま表示します。</p>
    </div>

    <div className="replay-stage">
      <article className="replay-event" aria-label={`行動 ${event.sequence} / ${total}`}>
        <header>
          <span className="replay-sequence">行動 {event.sequence} / {total}</span>
          <span className={event.valid ? "run-valid" : "run-rejected"}>{event.valid ? "VALID" : "REJECTED"}</span>
        </header>
        <dl>
          <div><dt>ターン</dt><dd>{event.action.turn}</dd></div>
          <div><dt>役割</dt><dd>{event.action.agent_id}</dd></div>
          <div><dt>行動</dt><dd>{event.action.action_id}</dd></div>
          <div><dt>立場</dt><dd>{event.action.stance}（{stanceLabels[event.action.stance]}）</dd></div>
          <div><dt>応答先</dt><dd>{event.action.responds_to.length > 0 ? event.action.responds_to.join(" / ") : "なし（新規の行動）"}</dd></div>
          {!event.valid && <div><dt>棄却理由</dt><dd>{event.invalid_reason}</dd></div>}
        </dl>
        <p className="replay-hash"><b>event SHA-256</b> {event.event_hash}</p>
      </article>

      <div className="replay-controls" role="group" aria-label="replay操作">
        <button type="button" onClick={() => goTo(0)} disabled={atStart}>最初</button>
        <button type="button" onClick={() => goTo(index - 1)} disabled={atStart}>前へ</button>
        <button type="button" onClick={() => goTo(index + 1)} disabled={atEnd}>次へ</button>
        <button type="button" onClick={() => setPlaying(true)} disabled={playing || atEnd}>自動再生</button>
        <button type="button" onClick={stop} disabled={!playing}>停止</button>
      </div>

      <ol className="replay-strip" aria-label="行動一覧（選ぶとその行動へ移動）">
        {run.events.map((item, itemIndex) => <li key={item.intent_id}>
          <button
            type="button"
            aria-current={itemIndex === index ? "step" : undefined}
            aria-label={`行動${item.sequence}: ${item.action.agent_id} / ${item.valid ? "VALID" : "REJECTED"}`}
            className={itemIndex === index ? "is-current" : undefined}
            onClick={() => goTo(itemIndex)}
          >{item.sequence}</button>
        </li>)}
      </ol>

      <p className="sr-only" aria-live="polite">{describeReplayEvent(event, total)}</p>
    </div>

    <p className="run-proof"><b>run_id</b> {run.run_id} <b>seed</b> {run.seed}<br /><b>final event SHA-256</b> {run.final_event_hash}</p>
  </section>;
}
