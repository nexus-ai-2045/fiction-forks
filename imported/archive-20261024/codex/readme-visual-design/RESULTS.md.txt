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
- artifact SHA-256: `b0fb526a01c4a6e8c91727c8f7cf76ba625effed11b5b725cc8a9b44aa4efdb4`
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

## 解釈上の制約

- scenario数値は未来予測ではなく、因果仮説を追跡するMVP用テスト値である。
- 一つのrunは政策、災害、安全保障の助言ではない。
- fixtureの成功を、AIエージェント間の創発の証拠として扱わない。
