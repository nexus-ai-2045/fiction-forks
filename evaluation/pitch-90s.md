# 90秒デモ脚本と想定問答

対象URL: `http://127.0.0.1:4173/workbench/` のみ。
主証拠: Vertex live の2037発動 / 2036破滅。
使わない: Idea Builder、github.io、Ollama切替、Issue #12候補、末尾スラッシュなしの `/workbench`。

Issue #12 の `low-altitude-public-mobility` は未検証fixture候補であり、本編デモへ混ぜない。

## 因果の一本線

`AI action → contract採否 → missing action → node遅延 → BIG BOSS判定`

1. 5役が固定catalogから行動を選ぶ。
2. schema・証拠・権限を外れた出力は棄却され、世界を書き換えない。
3. 残った行動だけが技術・制度・運用ノードを充足する。欠けたactionは `missing_action_delay_years` 年の遅延になる。
4. 決定論engineが同じseedで発動年と破滅条件を計算する。
5. 2036年までに発動できなければ BIG BOSS（修復不能条件）に負ける。

fixtureの遅延切替は物理の説明装置。Vertex liveは同じ物理を実モデルの欠落から踏んだ実行である。

## 0–15秒

放置した日本は2036年に、誤りを自分たちで直せなくなる。それが BIG BOSS。フィクションの機能を借りて世界線をforkする。ヒーローの `FIXTURE` ラベルは隠さない。

## 15–35秒

同じ2036年、二つの世界。放置は破滅。観測介入は2032年発動で回避する。生活基盤は5点悪化する。よくなる話だけではない。

## 35–60秒

遅延なし → 「対立仮説検証を5年遅延」。発動2037、ボスに間に合わない。制度が1つ遅れるだけで負ける。これはfixtureのnamed stressであり、AI実測ではない。

## 60–80秒

liveはVertexのまま。同じseed 2036。5役×3ターン、12件採用、3件棄却。欠けたのが `compare-rival-hypotheses`。だから対立仮説検証が5年遅れ、2037発動、2036破滅。replay PASS と event SHA を指す。その場でモデルを回したとは言わない。

## 80–90秒

予測装置ではない。借りた想像力を、再現できる社会介入として試す卓。`run_id` は世界入力ID。実行の差は provider / model / result SHA / event SHA。次の世界線でボスを倒す。

## 想定問答

厳しい質問: これはシミュレーターではなく数字のダッシュボードでは？
30秒: UIは計算しない。年次更新と破滅判定はPython engineが所有する。同じseedで放置と介入を比べ、制度ノードを5年遅らせると発動が2037になりボスに負ける。画面は検証済みartifactの再生である。

厳しい質問: AIの選択は結果を変えたのか。台本では？
30秒: 上の回避はfixture。実測はVertex、同じseed。12件採用、3件棄却。`compare-rival-hypotheses` が欠け、対立仮説検証が5年遅れ、2037発動、2036破滅。fixtureの遅延プロファイルと同じ物理が、実モデルの欠落から起きた。

厳しい質問: 未来予測では？
30秒: 予測していない。数値は仮説用テスト値。差はフィクション機能の制度翻訳と、許可行動だけをAIが選びengineが世界を計算すること。

厳しい質問: AutoGenやロールプレイと何が違う？
30秒: 自由会話ではない。固定catalog、反対されたintentは不採用、不正出力はabstain。再現するのは生文ではなく構造化行動とhash chain。

厳しい質問: OllamaとVertexは同じrunでは？
30秒: `ff-c705e4136e2fce00` はscenario・介入・seedの入力ID。実行は別でSHAもcommitも違う。主証拠はVertex。最新Ollama実測も2047年発動・2036年破滅で、10回の棄権と1件の契約違反を観測した。

## fixture / live 境界

| 画面 | 種別 | 言ってよいこと | 言ってはいけないこと |
|---|---|---|---|
| 上部比較と遅延切替 | fixture | 同じseedの決定論比較 | AIが回避した |
| Vertex live表 | live projection | 実モデルが選んだ構造化行動と敗北 | いま生成している |
| Ollama切替 | live projection | ローカル実モデルの選択と敗北 | 一般的なモデル優劣 |
| Issue #12 | fixture candidate | 未検証の翻訳候補 | デモの成功例 |
