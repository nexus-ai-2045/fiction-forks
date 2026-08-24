# 実測結果

この文書は、実際に実行したrunだけを記録する。計画値、期待値、未実行のAI出力を結果として書かない。

## 決定論fixture run

- 状態: 実行済み（2026-08-24）
- 実行実装commit: `5edebf7f0f7141d887281ea23a8b6b6e028959b3`
- 用途: protocol、部分観測、fail-closed、hash chain、world physicsの回帰検査
- AI実測: いいえ。fixtureは台本であり、LLMの挙動を示さない
- Python: 3.13
- scenario: `japan-2036`
- intervention: `doraemon-public-tools`
- seed: `2036`
- run ID: `ff-d3674fbb82db8614`
- input digest: `d3674fbb82db861487318ff61a864f82dcb1c5fc1b6393591e0fc0292f683a3e`
- final event hash: `9e6aadfc484e44f966bfb8f54c004be50e3f09f4ed98241b8e250fe90c2760fe`
- artifact: [`artifacts/runs/japan-2036-fixture.json`](artifacts/runs/japan-2036-fixture.json)
- manifest: [`artifacts/runs/japan-2036-fixture.manifest.json`](artifacts/runs/japan-2036-fixture.manifest.json)
- artifact SHA-256: `445732bd1a424fbee7e70f59d1c0ccda36e636517a9c61bd9783aa4fa0dc63dd`
- actions: 15 / invalid: 0 / abstain: 0
- capability coverage: 6 / interaction edges: 10 / conditioned intents: 15 / reversible action ratio: 1.0
- 公開artifact漏洩検査: role-scoped evidence ID 0件 / 自由記述 0件
- 技術ノード遅延: 全4ノード 0年
- 世界線: 放置世界は破滅、介入世界は回避
- replay: world comparison、actions、hash chainが完全一致

実行コマンド:

```powershell
$env:PYTHONPATH = "src"
python -m fiction_forks social `
  --scenario scenarios/japan-2036/scenario.json `
  --intervention interventions/doraemon-public-tools.json `
  --social-config scenarios/japan-2036/social.json `
  --provider fixture `
  --fixture fixtures/social/japan-2036-cooperation.jsonl `
  --seed 2036 `
  --output artifacts/runs/japan-2036-fixture.json `
  --overwrite
```

## live AI-agent run

- 状態: 未実行
- 理由: 現在の実装環境では `OPENAI_API_KEY` が設定されておらず、外部API費用を伴うrunの承認も分離している
- 完了条件: model、exact commit、scenario、seed、run ID、artifact SHA-256、観測メトリクス、replay同値性を記録する

## 世界観測fork：決定論fixture run

- 状態: 実行済み（2026-08-24）
- engine基点commit: `ade8d3333e1505e03698391051d054869bc8050c`（worldline PR #6 merge commit）
- 用途: 世界観測介入のaction catalog、部分観測、技術遅延、world physicsの回帰検査
- AI実測: いいえ。5役×3ターンのfixtureは台本であり、LLMの挙動を示さない
- Python: bundled 3.13 compatible runtime
- scenario: `japan-2036-centralization`
- intervention: `haruhi-world-observation`
- social config: `japan-2036-world-observation-dialogue`
- seed: `2036`
- run ID: `ff-188b986bb1ddbb7b`
- input digest: `188b986bb1ddbb7b594fbfb9b1cd3a330a418646af6f206ff1d25a2ba455438a`
- final event hash: `88d7242dad9b6e5a2f875daeda4ae5329705b3b64807bc0a1f7bdc0af2aa473f`
- fixture artifact: [`artifacts/runs/haruhi-world-observation-fixture.json`](artifacts/runs/haruhi-world-observation-fixture.json)
- manifest: [`artifacts/runs/haruhi-world-observation-fixture.manifest.json`](artifacts/runs/haruhi-world-observation-fixture.manifest.json)
- fixture SHA-256: `9e4b5adb971d739d00fb6a529e0c0323aceac5c69404e429922c47e6bac7298e`
- actions: 15 / invalid: 0 / abstain: 0
- capability coverage: 7 / interaction edges: 10 / conditioned intents: 15 / reversible action ratio: 1.0
- 技術ノード遅延: 全5ノード 0年
- 世界線: 放置世界は2036年に破滅、介入世界は2032年に発動して回避
- replay: world comparison、actions、hash chainが完全一致

## 世界観測fork：同一seed比較

通常比較は [`artifacts/runs/haruhi-world-observation-comparison.json`](artifacts/runs/haruhi-world-observation-comparison.json) に固定した。SHA-256は `8b75d3470b5ea6e6b3180231712267ce70af3fa39036bcfc9f9871ded1861d2f`。

| 2036年（seed 2036） | 放置世界 | 世界観測介入 | 差分 |
|---|---:|---:|---:|
| 破滅判定 | 破滅 | 回避 | — |
| 生活基盤 | 43 | 38 | -5 |
| 戦略的自律性 | 17 | 22 | +5 |
| 認知主権 | 6 | 35 | +29 |
| 正統性 | 38 | 45 | +7 |
| 修復能力 | 33 | 56 | +23 |

## 世界観測fork：ノード遅延比較

`contested-evidence-protocol` を5年遅らせた比較を [`artifacts/runs/haruhi-world-observation-contestation-delay.json`](artifacts/runs/haruhi-world-observation-contestation-delay.json) に固定した。SHA-256は `122a8fb540bc60d93dc4b7a68ff200093f65b05941a404bc5db2b8d3c635b7d5`。

- 通常: 対立仮説検証 2031年 → 共同訓練 2032年 → 2032年発動 → 回避
- 5年遅延: 対立仮説検証 2036年 → 共同訓練 2037年 → 2037年発動 → 2036年に破滅
- 遅延世界では介入効果が一度も発生せず、2036年の5指標は放置世界と同値

## 世界観測fork：検証結果

- `python -m unittest discover -s tests -v`: 49 tests、全件pass
- `python -m ai_ratchet_gate --repo .`: pass（現存0件 / 新規0件）
- JSON契約: 介入、social config、fixture、通常比較、遅延比較をテストでread-back
- 権利境界: 新規画像、ロゴ、音声、映像、台詞、キャラクター表現なし
- worldline PR #6: Linux / Windows、Python 3.11 / 3.13、PR contract、WORLDLINE実行、CodeQLが全件pass

## 世界観測fork：未確認事項

- live OpenAI providerは未実行であり、実際のLLMエージェント対話や創発を実測していない
- 観測系が異なるデータ供給者・モデル・運営者へ十分分散しているかを測る現実の独立性指標は未設計
- 誤警報率、異議処理時間、運用費、維持人員、法制度適合性、プライバシー影響は現実データで未校正
- 状態値への効果量と2032年発動はMVP用の因果仮説であり、予測または政策助言として未確認
- このmaintenance差分のGitHub ActionsはPR作成後に確認する

## 解釈上の制約

- scenario数値は未来予測ではなく、因果仮説を追跡するMVP用テスト値である。
- 一つのrunは政策、災害、安全保障の助言ではない。
- fixtureの成功を、AIエージェント間の創発の証拠として扱わない。
