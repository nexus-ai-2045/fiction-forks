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
- 実行実装commit: `8cb8d65332ef897472e31dfadc6daac0b87dcca8`
- 用途: 世界観測介入のaction catalog、部分観測、技術遅延、world physicsの回帰検査
- AI実測: いいえ。5役×3ターンのfixtureは台本であり、LLMの挙動を示さない
- Python: bundled 3.13 compatible runtime
- scenario: `japan-2036-centralization`
- intervention: `haruhi-world-observation`
- social config: `japan-2036-world-observation-dialogue`
- seed: `2036`
- run ID: `ff-106b8f673125c917`
- input digest: `106b8f673125c917651d8c5c7cdd03ae6eb9a70ab6ca6eacdca273cff9449aa1`
- final event hash: `aabf03db804eb8e01582103fc4a5479100e2dd5aa6d15c66cc54a8a1d6b71dad`
- fixture artifact: [`artifacts/runs/haruhi-world-observation-fixture.json`](artifacts/runs/haruhi-world-observation-fixture.json)
- manifest: [`artifacts/runs/haruhi-world-observation-fixture.manifest.json`](artifacts/runs/haruhi-world-observation-fixture.manifest.json)
- fixture SHA-256: `950092c227e19ebb311feb71167ca78ba7706d90dbc72de18a8992d87d45c223`
- actions: 15 / invalid: 0 / abstain: 0
- capability coverage: 7 / interaction edges: 10 / conditioned intents: 15 / reversible action ratio: 1.0
- 技術ノード遅延: 全5ノード 0年
- 世界線: 放置世界は2036年に破滅、介入世界は2032年に発動して回避
- replay: world comparison、actions、hash chainが完全一致

## 世界観測fork：同一seed比較

通常比較は [`artifacts/runs/haruhi-world-observation-comparison.json`](artifacts/runs/haruhi-world-observation-comparison.json) に固定した。SHA-256は `51e182e99541c0237276e77e99fe163e95c5e8d8e74c51652e06d87c7d240959`。

| 2036年（seed 2036） | 放置世界 | 世界観測介入 | 差分 |
|---|---:|---:|---:|
| 破滅判定 | 破滅 | 回避 | — |
| 生活基盤 | 43 | 38 | -5 |
| 戦略的自律性 | 17 | 22 | +5 |
| 認知主権 | 6 | 35 | +29 |
| 正統性 | 38 | 45 | +7 |
| 修復能力 | 33 | 56 | +23 |

## 世界観測fork：ノード遅延比較

`contested-evidence-protocol` を5年遅らせた比較を [`artifacts/runs/haruhi-world-observation-contestation-delay.json`](artifacts/runs/haruhi-world-observation-contestation-delay.json) に固定した。SHA-256は `7839fbb443c594f741fb20cc8b0691b492c7ec92ec80fe68a67477704d318ac2`。

- 通常: 対立仮説検証 2031年 → 共同訓練 2032年 → 2032年発動 → 回避
- 5年遅延: 対立仮説検証 2036年 → 共同訓練 2037年 → 2037年発動 → 2036年に破滅
- 遅延世界では介入効果が一度も発生せず、2036年の5指標は放置世界と同値

## 世界観測fork：検証結果

- `python -m unittest discover -s tests -v`: 37 tests、全件pass
- `python -m ai_ratchet_gate --repo .`: pass（現存0件 / 新規0件）
- JSON契約: 介入、social config、fixture、通常比較、遅延比較をテストでread-back
- 権利境界: 新規画像、ロゴ、音声、映像、台詞、キャラクター表現なし

## 世界観測fork：未確認事項

- live OpenAI providerは未実行であり、実際のLLMエージェント対話や創発を実測していない
- 観測系が異なるデータ供給者・モデル・運営者へ十分分散しているかを測る現実の独立性指標は未設計
- 誤警報率、異議処理時間、運用費、維持人員、法制度適合性、プライバシー影響は現実データで未校正
- 状態値への効果量と2032年発動はMVP用の因果仮説であり、予測または政策助言として未確認
- GitHub ActionsのLinux / Windows、Python 3.11 / 3.13 matrixはPR作成後のCIで確認する

## 解釈上の制約

- scenario数値は未来予測ではなく、因果仮説を追跡するMVP用テスト値である。
- 一つのrunは政策、災害、安全保障の助言ではない。
- fixtureの成功を、AIエージェント間の創発の証拠として扱わない。
