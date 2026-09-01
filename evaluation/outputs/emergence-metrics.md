# 行動多様性・相互作用・結果分散の観測報告

この報告は創発性の断定ではない。観測できた行動の多様性、相互作用、契約棄却、技術遅延、発動年、破滅判定の分散だけを集計する。LLM生成そのものの決定論性は主張しない。同じ入力run_idでも provider / model / runtime_revision / result SHA / event SHA が違えば別実行である。

- 実行数: 6
- curated root: `artifacts/runs`
- curated入力のみ: True
- curated / uncurated: 6 / 0

## 実行ごとの識別

| source_class | curated | run_id | provider | model | seed | activation_year | collapsed | result SHA |
|---|---|---|---|---|---:|---:|---|---|
| deterministic_comparison | True | `not_measured` | not_measured | not_measured | 2036 | 2032 | False | `8b75d3470b5e` |
| deterministic_comparison | True | `not_measured` | not_measured | not_measured | 2036 | 2037 | True | `122a8fb540bc` |
| fixture | True | `ff-c705e4136e2fce00` | fixture | not_measured | 2036 | 2032 | False | `12b1a98cbd0d` |
| fixture | True | `ff-b74f4c768380c732` | fixture | not_measured | 2036 | 2032 | False | `a062aba60111` |
| live | True | `ff-c705e4136e2fce00` | ollama | qwen2.5vl:3b | 2036 | 2047 | True | `2dcf5b0fc3ee` |
| live | True | `ff-c705e4136e2fce00` | vertex | gemini-2.5-flash | 2036 | 2037 | True | `d1a758b63c61` |

## 分離集計

### deterministic_comparison

- n: 2
- curated / uncurated: 2 / 0
- action diversity 平均: not_measured
- capability coverage 平均: not_measured
- interaction edge 平均: not_measured
- fail-closed rate 平均: not_measured
- collapse rate: 0.5
- activation year: {'measured': 2, 'not_measured': 0, 'counts': {'2032': 1, '2037': 1}}

### fixture

- n: 2
- curated / uncurated: 2 / 0
- action diversity 平均: 6.5
- capability coverage 平均: 6.5
- interaction edge 平均: 10.0
- fail-closed rate 平均: 0.0
- collapse rate: 0.0
- activation year: {'measured': 2, 'not_measured': 0, 'counts': {'2032': 2}}

### live

- n: 2
- curated / uncurated: 2 / 0
- action diversity 平均: 4.5
- capability coverage 平均: not_measured
- interaction edge 平均: 9.5
- fail-closed rate 平均: 0.1333
- collapse rate: 1.0
- activation year: {'measured': 2, 'not_measured': 0, 'counts': {'2047': 1, '2037': 1}}

## 指標定義

- action diversity: 有効行動のうち `abstain` を除いたユニーク `action_id` 数。行動が無い入力は `not_measured`。
- capability coverage: social result の `metrics.capability_coverage`。無ければ `not_measured`。0で埋めない。
- interaction density: `interaction_edge_count / (roles × (roles-1) × turns)`。欠けた項があれば `not_measured`。
- fail-closed rate: invalid / event_count。分母が無ければ `not_measured`。
- collapse rate: `collapsed` が真偽値として測定できた実行だけの割合。未知は分母に入れない。
- 実行の区別: `run_id` は世界入力ID。実行差は provider / model / runtime_revision / 実artifact SHA / event SHA。
- curated: curated root 配下と確認できた入力だけが真。判定できない入力は偽にする。
