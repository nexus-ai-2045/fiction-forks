# ADR 0014: 創発指標を観測記録として扱い、創発の証拠にしない

- Status: Accepted
- Date: 2026-09-01

## Context

live AI-agent runが実行され、`artifacts/runs/` に fixture、replay、live projection、決定論比較が並んだ。これらを横断して「行動の多様性がどれだけ出たか」「契約棄却がどれだけ起きたか」「発動年と破滅判定がどれだけ散ったか」を見たい要求がある。集計層として `evaluation/emergence_metrics.py` を追加した。

しかし「創発指標」という名前の数値を出すこと自体が、「創発が起きた証拠がある」と読まれる。実際には、単一runの結果しかなく、同一条件の反復も対照条件も無い。`RESULTS.md` は「fixtureの成功を、AIエージェント間の創発の証拠として扱わない」と既に固定しており、`evaluation/emergence_metrics.py` も報告本文へ同趣旨のdisclaimerを埋め込んでいる。それでも、指標の位置づけがADRにも `PROJECT_SSOT.md` にも登録されていなければ、この層が正本なのか派生物なのか、どこまで主張してよいのかが判定できない。

加えて、欠測を0で補完する集計、fixtureとliveを混ぜた平均、`run_id` だけによる実行同定は、いずれも「良く見える数値」を作る方向へ倒れる。ADR 0001が決定論engineへ、ADR 0008が固定action catalogへ与えた所有権を、観測層が後から侵食しないよう境界を固定する必要がある。

## Decision

1. `evaluation/` は観測記録層とする。runtime physics、公式結果、破滅判定を所有しない。既定入力はcurated root `artifacts/runs` とし、その外を入力へ足すかどうかはoperatorの責任とする。curated rootの外から集めた実行は行ごとの `curated` を偽にし、報告の `input_curation` と各集計の `uncurated` 件数へ機械可読に刻む。curatedとuncuratedを混ぜた集計を、curatedだけの集計として提示しない。
2. 報告はversion付き `fiction_forks_emergence_report.v1` を名乗り、創発を断定しない旨のdisclaimerを本文へ必ず含める。
3. 集計対象は既知の `fiction_forks_social_result.v1`、`fiction_forks_live_run_summary.v1`、`fiction_forks_comparison.v1` だけとし、認識できない文書は無視する。
4. 測れなかった値は0で補完せず `not_measured` にする。分母0、型不一致、密度が1を超える組み合わせも `not_measured` とする。
5. 実行の同一性は `run_id` ではなく、provider / model / runtime_revision / artifact SHA-256 / event stream SHA-256 の組で判定する。`run_id` はscenario・介入・seedの入力IDであり、実行の識別子ではない。
6. `fixture` / `replay` / `live` / `deterministic_comparison` / `unknown` をsource_classとして分離集計する。混ぜた全体平均を主指標として提示しない。
7. 自由記述、role-scoped evidence、raw model textを報告へ入れない。検出した場合は握り潰さず、報告生成を失敗させる。
8. 指標の高低を、創発の証拠、モデル間の一般的な優劣、政策助言、未来予測の根拠として提示しない。fixtureの成功はAIエージェント間の創発の証拠にしない。
9. `evaluation/worldline-issue12/` は未検証のworldline候補として扱い、公式結果、`RESULTS.md` の実測記録、90秒デモ本編へ混ぜない。

## Consequences

- 指標を増やしても「創発した」と言える閾値は生まれない。得られるのは分散の記述だけである。
- `not_measured` が多い報告は失敗ではなく、入力artifact側にprovider、model、runtime_revision、SHAが揃っていないことの表示になる。artifact schemaの整備が指標の前提になる。
- fixtureとliveを分離するため、見栄えのよい単一スコアは出せない。デモや外部説明では毎回source_classを添える必要がある。
- curated rootの外を入力へ足した報告は `input_curation.curated_only` が偽になり、混在の判定に行ごとの `source_path` を目視する必要がなくなる。`evaluation/worldline-issue12/` を混ぜた集計は、curatedの実測記録として引用できない形で残る。
- 集計結果は派生物なので再生成できる。Git履歴上の数値を正本として引用しない。
- 創発を主張したい場合は、この層を拡張するのではなく、対照条件、反復回数、事前に書いた仮説と反証条件を持つ測定設計を別ADRで作り直すことになる。

## Alternatives considered

- **単一の創発スコアを定義して公開する**: 閾値の根拠が無く、fixtureとliveを混ぜた平均だけが独り歩きするため不採用。
- **欠測を0で補完して平均を安定させる**: 未測定と測定値0を同一視し、fail-closed率とcapability coverageを実際より良く見せるため不採用。
- **`run_id` だけで実行を同定する**: provider違いの別実行を1件へ潰し、実行数を過少に見せるため不採用。
- **raw model textを報告へ含めて質的に評価する**: 公開artifactから自由記述とrole-scoped evidenceを除外する境界を破るため不採用。
- **curated root外の入力をCLIで拒否する**: 未検証worldline候補の下見まで塞ぐ一方、`--repo-root` を差し替えれば迂回できて強制にならないため不採用。かわりに行と集計へ `curated` を刻み、混在を機械可読にする。
- **curatedかどうかを本文のdisclaimerだけで断る**: 読み手が行ごとの `source_path` を目視するまで混在が分からず、宣言だけで実装が無い状態に戻るため不採用。
- **`evaluation/` を `src/fiction_forks/` へ統合する**: 決定論engineの正本へ観測層を混ぜ、ADR 0001の状態所有権を曖昧にするため不採用。
- **指標層を作らず結果を人手で読む**: 実行が増えたとき比較条件が記録されず、印象で創発を語る余地がかえって広がるため不採用。

## 見直し条件

- 同一scenario・同一seedでprovider横断の反復実行が単一runを超え、分散を統計的に扱える入力が揃ったとき
- 創発の定義と反証条件を、事前登録した仮説と対照条件として書けるようになったとき
- この指標が「創発の証拠」として外部資料へ引用された、`not_measured` を0と読み替えた報告が発生した、または `curated_only` が偽の報告がcuratedの実測記録として引用されたとき
- artifact schemaがprovider、model、runtime_revision、event stream SHA-256を必須化し、実行同定をadapter側で保証できるようになったとき
