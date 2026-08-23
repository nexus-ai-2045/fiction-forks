# ADR 0006: Web UIとAIをengine結果の投影層にする

- Status: Accepted
- Date: 2026-08-24

## Context

CLIだけでは参加障壁が高いが、Web UIやAIごとにsimulation logicを持つと結果がdriftする。表示の魅力とシミュレーションの正本を分離する必要がある。

## Decision

将来のWeb UIはscenario、intervention、resultを可視化・編集支援する投影層とする。UI stateは選択、filter、drawer、入力途中の草案だけを所有し、社会状態、発動年、破滅判定は所有しない。

将来のAI層は言い換え、候補、説明、review支援だけを行い、出力を未信頼入力としてschema検証と人間reviewへ戻す。

## Consequences

- CLIとWebの結果一致を契約テストで検査できる。
- UIを作り替えてもsimulation contractを維持できる。
- Web実装時にPython APIかTypeScript移植かを別途決める必要がある。
- AIの自然な説明より、根拠と状態所有権を優先する。

## Alternatives considered

- ブラウザ内だけに全ロジックを再実装する: drift対策が未定のため現時点では採用しない。
- AIエージェントが世界を自由生成する: 比較可能性を損なうため不採用。
- 3D世界を先に作る: MVPの参加導線と因果reviewに不要なため後回し。

## 見直し条件

Web実装開始前に、唯一の実行器とcross-language contract testを決定するADRを追加する。
