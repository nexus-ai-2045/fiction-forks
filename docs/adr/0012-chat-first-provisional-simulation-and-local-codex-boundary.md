# ADR 0012: チャット壁打ちと暫定simulationを公式世界線から分離する

- Status: Accepted
- Date: 2026-08-25
- Supersedes: ADR 0006、0009、0011のうち、Idea作成時に対話・previewを行わないとしたWeb境界

## Context

現在のIdea Builderは「作品」と「アイデア」をIssue文へ変換するが、参加者が本当に知りたいのは、意図が正しく理解されたか、どの破滅条件へ作用するか、実現条件や副作用は何か、その介入で世界線がどう変わり得るかである。Issueを作った後にcontributorが実装するまで何も返らない体験では、参加ループが閉じない。

一方、自由記述からLLMが効果量、破滅確率、技術完成年を直接生成して「simulation結果」と表示すると、ADR 0001と0008が固定した決定論engineの所有権、同一条件比較、再現性を失う。公開GitHub PagesからローカルCodexのapp-serverへ直接接続し、ブラウザ入力へshell、filesystem、GitHub writeを渡すことも許可範囲が広すぎる。手元のCodex CLI 0.130.0-alpha.5にはexperimentalなapp-serverとTypeScript binding生成機能があるが、公開Webの安定した製品APIとして扱える根拠はまだない。

## Decision

参加体験を次の8状態へ分ける。

1. `chat-draft`: 参加者は作品とアイデアを自然文で話す。
2. `understanding-check`: 対話providerは、理解したアイデア、抽象機能、対象破滅、未確定条件、副作用候補を返し、「この理解でよいか」を確認する。
3. `idea-draft`: 本人確認後だけ、version付き`IdeaDraft`へ変換する。
4. `provisional-preview`: 既存scenario、既存action catalog、許可された介入templateだけで必要fieldを満たせる場合、決定論engineを実行する。満たせない場合は数値を捏造せず、`not-simulatable`と不足条件を返す。
5. `idea Issue`: 会話全文ではなく、本人が確認した要約、未確定事項、preview区分と入力digestをGitHub確認画面へ渡す。
6. `worldline PR`: contributorが介入、技術ツリー、social config、fixture、比較を再現可能な差分へする。
7. `official-result`: CIと人間レビューを通った結果だけを共有世界の実行結果として表示し、Issueへ返す。
8. `doom-candidate`: 公式結果が既存破滅条件を回避した場合、副作用、残存リスク、外部ショックから次の破滅候補を作る。人間レビュー済みscenario PRだけが次のactive doomへ昇格できる。

`provisional-preview`は未来予測、政策評価、公式結果ではない。UIは必ずscenario、seed、engine version、template、未確定field、暫定表示を示す。LLMは`IdeaDraft`とtemplate候補を作れるが、metric delta、破滅条件、観測値を直接確定しない。

対話層は`DialogueProvider`として分離し、最初の実装候補を次の2つにする。

- `guided`: provider不要の質問テンプレート。公開Webとoffline fallbackで動く。
- `local-codex`: 利用者が明示起動したloopback-only companionを介してCodexへ接続する。

公開WebはCodex app-serverへ直接接続しない。local companionは次を必須とする。

- `127.0.0.1`だけでlistenし、sessionごとの短命capability tokenを使う。
- 許可originを明示し、接続前に利用者が対象repo、読取範囲、model、費用、外部送信を確認する。
- Codexは固定promptとstrict `IdeaDraft` schemaだけを返す。shell、filesystem write、GitHub write、secret読取、任意toolを公開Webへ委譲しない。
- `app-server`のversionと生成bindingを固定し、未対応version、認証欠落、schema不一致では`guided`へfail closedする。
- 会話本文をrepo、Issue、artifactへ自動保存しない。公開へ渡すのは本人確認済みprojectionだけにする。

## Allowed

- チャット形式でアイデアの理解確認、質問、言い換え、技術・制度・運用の不足候補を返す。
- 既存templateへ完全に写像できる案を、同じPython engineで暫定比較する。
- 暫定結果からIdea Issue草案を作り、GitHub側の確認画面で本人が編集する。
- 公式worldlineの結果、争点、技術ツリー、過去runをWebでread-only表示する。
- 破滅回避後に、根拠、発生条件、観測指標、可逆性を持つdoom candidateを提案する。

## Prohibited

- LLMの文章をmetric、破滅レベル、破滅確率、公式simulation結果として直接採用する。
- 未確認の会話をIssue、PR、外部API、telemetryへ自動送信する。
- 公開WebへOpenAI API key、GitHub token、Codex credentialを置く。
- public originからraw Codex app-server、shell、filesystemへ直接接続する。
- 破滅回避を取り消すためだけに、根拠のない新破滅を自動追加する。
- doom candidateを人間レビューなしでactive scenarioまたはmainへ反映する。

## Human Review Gate

次は別々の人間レビューを必要とする。

1. `IdeaDraft` schema、対話文言、暫定結果の表示区分。
2. local companionのorigin、token、sandbox、tool allowlist、data retention。
3. GitHub Pagesからlocal companionへ接続するbrowser securityの実機検証。
4. live providerのmodel、費用上限、入力projection、`store=false`、ログ保存範囲。
5. doom candidateをactive scenarioへ昇格するscenario PR。
6. public Pages deploy、backend deploy、secret設定、GitHub App導入。

## Consequences

- 参加者はIssueを作る前に、自分の案がどう理解され、何が不足しているかを確認できる。
- すぐ試せる案は結果を見られ、試せない案も「何を決めれば走るか」が分かる。
- 暫定preview、fixture、live run、公式結果の混同を避けられる。
- React + TypeScriptへの移行条件が成立し、チャット状態、run状態、結果表示を型で管理する必要が生じる。
- local Codex連携は便利だがexperimental protocolに依存するため、`guided` fallbackとversion gateが不可欠になる。
- adaptive doomはゲームを継続させるが、勝利を無効化せず、次シーズンとしてversioned scenarioを追加する。

## Next Actions

1. `IdeaDraft`、`ProvisionalRunRequest`、`RunSummary`、`DoomCandidate`のschemaをPython側で正本化する。
2. Python fixtureからTypeScript型を生成または検証するcross-language contract testを決める。
3. Vite + React + TypeScriptでdoom map、参加入口、chat shell、result browserを実装する。
4. provider不要の`guided`対話を先に完成させる。
5. local companionをread-only spikeとして実装し、raw app-serverをWebへ露出しないことを検証する。
6. Issueの`listed / assigned / implemented / simulated / reported-back`状態を機械可読にする。

## 見直し条件

- Codex app-serverに安定した公式browser integration契約が公開されたとき
- public Webでlocal companionを使わず、安全な認証、費用制御、削除、監査を持つbackendを運用できるとき
- 暫定previewが公式結果と誤認された、またはtemplate制約で有用な案を継続的に表現できないとき
- adaptive doomが現実的な因果よりゲーム都合を優先していると評価されたとき
