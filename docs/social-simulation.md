# AIエージェント社会シミュレーション

## 目的

Fiction ForksのAIエージェントは、未来を予言したり状態値を創作したりするためではない。異なる責任と部分観測を持つ役が、同じ危機と介入をどう解釈し、どの条件なら協力・保留・反対するかを観察するために使う。

## 実行単位

日本2036の初期MVPは、5役×3ターンで構成する。

1. 市民監査役
2. 基盤技術者
3. 物流運用者
4. 地域翻訳者
5. 脅威分析役

各ターンは次の順で進む。

1. engineが、その役に見せてよい証拠、目的、前ターンまでの公開行動を部分観測として作る。
2. providerが `fiction_forks_action.v1` に一致する行動を一つ返す。行動は立場 `support / condition / oppose / abstain` と、応答先 `responds_to` を持つ。
3. runnerがrun、turn、agent、action、target、evidence、長さ、未知fieldを検査する。
4. 有効な行動だけを固定action catalogへ通す。不正出力やprovider失敗は `abstain` として状態不変で記録する。
5. 全役の行動をagent ID順に確定し、次ターンへ公開する。同一ターン内の到着順は結果へ影響しない。
6. interaction reducerが応答edgeを作り、反対されたintentを不採用にする。残った行動から技術・制度・運用ノードの未充足条件と遅延年を決定する。
7. 既存の決定論engineが同じscenario、intervention、seedで2036年まで計算する。

## AIができること・できないこと

AIが選べるのは、scenarioで許可された `action_id`、対象役、利用した証拠、確信度、採用条件、280文字以内の説明だけである。

AIは次を出力できない。

- 状態値への `metric_delta`
- 破滅判定や介入効果
- seedやrun IDの変更
- 観測にないevidence ID
- 許可されていないtargetやaction
- 未知field

これらが含まれた行動は全体を破壊せず、その役の `abstain` へfail closedする。

## 部分観測と公開ログ

public evidenceは全役へ、role-scoped evidenceは `audience` に列挙した役だけへ渡す。ここでのprivateはシミュレーション内の情報差を表すだけであり、実在の秘密や個人情報を入力してよいという意味ではない。公開artifactはallowlist projectionとし、role-scoped evidence ID、自由記述、条件本文、役のprivate context、API credential、provider内部情報を保存しない。

公開artifactには次を残す。

- engine version、scenario、intervention、social config、seedから計算したinput digest
- provider名とmodel名（credentialは除外）
- 各行動のvalid/invalid、立場、応答edge、理由コード
- 社会状態のbefore/after hash
- 前イベントhashを含むhash chain
- 技術ノードごとの未充足actionと遅延年
- 決定論engineの世界線比較
- assumption notice

## provider境界

| provider | 用途 | 外部通信 |
|---|---|---|
| `fixture` | CI、デモ、回帰テスト | なし |
| `replay` | 保存済みartifactの同値再計算 | なし |
| `openai` | 実際のLLMエージェント対話 | あり |

OpenAI providerは公式Python SDKとResponses APIのStructured Outputsを使い、`store=false` とする。モデル指定、`OPENAI_API_KEY`、`--confirm-live` の三つが揃わなければ開始しない。CIはlive providerを呼ばない。

fixtureはAI実測ではなく、プロトコルとworld physicsの決定性を検証する台本である。ハッカソン結果としてAI挙動を主張する場合は、live providerで実行したartifact、exact commit、model、出力hashを [RESULTS](../RESULTS.md) に追加する。

## 再現性

同じ入力とfixtureは、run ID、行動、hash chain、技術遅延、世界線を完全一致させる。replayはartifactのinput digestが現在のscenarioと一致しない場合、行動を採用しない。

モデル出力そのものの再現性は保証しない。再現する対象は、そのrunで観測された構造化行動と、それを決定論engineへ適用した結果である。
