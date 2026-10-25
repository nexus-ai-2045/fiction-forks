# Issue #12 worldline候補 — 抽象化根拠

対象Issue: https://github.com/nexus-ai-2045/fiction-forks/issues/12
状態: 未検証候補。fixtureのみ。live Ollama / Vertex 実測は無い。本編90秒デモへ混ぜない。

## 入力のままではシミュレーションできない理由

Issue本文の借りたい機能は「タケコプター」、同義表現は「夢のロボット」、変えたい未来は「自由に飛べるので便利」、対象は「遊びたい盛りの子ども」、実現条件は「爆発的テクノロジー」、費用・副作用は「？」である。

これは道具名と便益の願望であり、作品非依存の社会機能、active doomへの因果、完成証拠、費用、失敗条件が欠けている。`catalogs/idea-status.v1.json` も同じ欠落を記録している。この候補はその欠落を埋めるための翻訳であり、Issueの正しさの証明ではない。

## 抽出した機能

子どもを含む非専門家が、近距離の低空移動を専門家独占ではなく地域の公共インフラとして使える。

道具を配布する話にも、人物の夢を叶える話にもしない。既存の `doraemon-public-tools`（未来の道具への公共アクセス一般）とも分け、空域・同意・落下・修理・救助に限定する。

## 実装ツリー

| ノード | 種別 | 役割 |
|---|---|---|
| open-low-altitude-platform | technology | 公開設計の機体と交換可能な安全装置 |
| child-consent-and-airspace-charter | institution | 子ども利用の同意、禁止空域、停止権 |
| neighborhood-repair-bays | technology | 地域修理と部品交換 |
| nuisance-and-fall-redress | institution | 騒音・落下・覗き込みの異議 |
| joint-search-rescue-drills | operations | 落下・迷子・悪天候・拠点停止の共同訓練 |

named stress: `child-consent-and-airspace-charter` を5年遅延すると発動が2037年になり、2036年の破滅条件に間に合わない。

## 境界

- キャラクター、台詞、口調、公式設定、竹とんぼ型ガジェット名は収録しない。
- 数値はMVP用の因果仮説であり、航空政策や事故予測ではない。
- fixture成功をAI創発の証拠にしない。
- 生活基盤は維持費で悪化する。回避しても都合のよい成功だけにはしない。
