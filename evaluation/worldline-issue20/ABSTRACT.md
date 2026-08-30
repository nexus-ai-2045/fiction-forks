# Issue #20 simulation candidate

## 翻訳

『呪術廻戦』から提示された「無下限呪術で、危機が来たら無限に回避」を、文字どおりの無限能力ではなく、危機との距離が縮むほど複数の防護層を再構成し、人間の停止・拒否・退避を残す「適応型セーフティ・エンベロープ」へ翻訳した。

## 決定論比較

- scenario: `japan-2036-centralization`
- seed: `2036`
- intervention: `adaptive-safety-envelope`
- 通常条件: 2032年に発動し、2036年の修復不能条件を回避
- 制度層を5年遅延: 2037年発動となり、2036年の修復不能条件に間に合わない

この比較は介入効果を仮定したモデル内結果であり、現実の効果を証明しない。

## Ollama live AI run

- provider/model: `ollama / qwen2.5vl:3b`
- run_id: `ff-d57ea8247832c89d`
- 5役 × 3ターン = 15行動
- valid / invalid / abstain: `14 / 1 / 6`
- interaction edges: `18`
- AIが選択した実装行動: `deploy-hazard-probes`, `establish-stop-rights`, `exercise-resource-exhaustion`
- 選ばれなかった必須行動により、発動は2052年、2036年に修復不能条件へ到達
- replay final event hash: 一致
- bundle内run_id: 全record一致
- event stream SHA-256: replay/evidence/再計算が一致
- result SHA-256: `c536366c092fa28fdf7cadb9d238c31f260444183a21182cc9dbee749b4b266f`
- bundle SHA-256: `5d077c025a0bd52509300f03003c827b010fd0e285737d79e0fb139c4b2bb71c`

## 解釈

設計上は破滅回避可能でも、AI役は監査、手動退避、交換部品の必須行動を選び切らなかった。したがって「無限回避」は成立せず、制度・資源・人間の退避を欠くと防護層が連鎖的に遅延する。これは成功だけを作るデモではなく、AIの選択がモデル内の失敗経路を生む実測例である。

## 正本と状態

- 介入正本: `interventions/adaptive-safety-envelope.json`
- social config正本: `scenarios/japan-2036/social-adaptive-safety-envelope.json`
- fixture正本: `fixtures/social/adaptive-safety-envelope.jsonl`
- このdirectoryはlive result、replay、run bundle、派生比較、解析だけを保持し、入力正本を複製しない
- worldlineはPR #22でmainへ統合済み。Ollama liveは単一runの提出用実測証拠であり、公式curated runや現実の効果認定ではない
