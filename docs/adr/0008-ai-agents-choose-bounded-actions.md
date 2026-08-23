# ADR 0008: AIエージェントは制約付き行動を選び、engineが世界状態を所有する

- Status: Accepted
- Date: 2026-08-24

## Context

Fiction ForksをAIエージェント社会シミュレーションとして成立させるには、異なる専門役が相互の発言を受けて判断条件を変える実行層が必要である。一方、LLMへ状態値、介入効果、破滅判定を直接生成させると、比較可能性、再現性、安全境界が失われる。

CI用の台本だけではLLM相互作用の実測にならないが、外部APIを必須にすると費用、credential、ネットワーク障害が公開repoの必須検査へ混ざる。

## Decision

1. 5つの社会役が、役固有の目的と部分観測を持って3ターン対話する。
2. LLMはstrict schemaに一致する `ActionIntent` だけを返し、固定action catalogから一つ選ぶ。intentは `support / condition / oppose / abstain` と過去intentへの `responds_to` を持つ。
3. `metric_delta`、破滅判定、未知field、観測外証拠は拒否し、その役を `abstain` として状態不変で記録する。
4. action catalogだけが技術・制度・運用ノードの充足と遅延へ変換できる。年次状態と破滅判定は既存の決定論engineが所有する。
5. 同一ターンの出力はagent ID順に確定し、次ターンから他役へ公開する。providerの到着順を因果へ混ぜない。interaction reducerは応答edgeを固定し、反対されたintentを不採用にして技術遅延へ反映する。
6. CIは決定論fixtureを使う。live providerのrunはartifactへ固定し、replayでworld physicsとの同値性を検証する。
7. live OpenAI providerは公式SDK、Structured Outputs、`store=false` を使い、モデル、API key、費用確認を必須にする。
8. artifactはinput digestとbefore/after hash chainを持つ。公開artifactはallowlist projectionとし、role-scoped evidence ID、自由記述、条件本文、credential、provider内部情報を保存しない。

## Consequences

- LLMの創造性は「どの許可行動を、誰に、どの証拠と条件で提案するか」に限定される。
- 不正出力やprovider停止が世界を有利に改変しない。
- fixture、replay、liveを同じprotocolで比較できる。
- 新しい行動効果はLLM promptではなく、レビュー可能なscenario差分として追加する必要がある。
- live runがない段階では「AIエージェント実測済み」と主張できない。

## Alternatives considered

- **LLMに状態値を直接採点させる**: 結果がpromptとmodelへ依存し、同条件比較を失うため不採用。
- **役ごとに独立して一度だけ回答させる**: 相互作用と判断改訂を観察できないため不採用。
- **live APIをCI必須にする**: credential、費用、可用性をmerge条件へ混ぜるため不採用。
- **fixtureだけをAIシミュレーションと呼ぶ**: 台本と実測を混同するため不採用。

## 見直し条件

- action catalogでは重要な創発を表現できない具体例が蓄積したとき
- private observationの漏洩またはhash chainの不十分さが実測されたとき
- provider APIを増やし、共通の費用・データ保持・replay契約が必要になったとき
