# ADR 0011: 参加をIssue、worldline PR、simulation、人間レビューの制御ループにする

- Status: Accepted
- Date: 2026-08-24

## Context

ADR 0009は未実装の着想をIssue、動く世界線をPull Requestに分けた。しかし、画面と文書が個々の入口だけを説明すると、参加者には「Issueを作った後に誰が何をし、いつシミュレーションが走り、何が共有世界へ反映されるか」が見えにくい。

Idea作成時にLLMまたはengineを自動実行すると、費用、未信頼入力、権利境界、結果の再現性、人間レビューの状態が混ざる。逆に、実装者だけを対象にすると、GitHubやコードに詳しくない参加者が着想を持ち込めない。

## Decision

参加ループを次の4状態に固定する。

1. `idea Issue`: Idea Builderがブラウザ内の入力をMarkdownへ変換し、GitHubの確認画面を開く。未実装・simulation未実行と明記する。
2. `Build`: 外部contributorは公開forkの専用branch、write権限者は本repoの専用branchで、一つの介入、技術ツリー、social config、fixtureを作る。AIへ依頼する場合も同じ公式repo URLとIssue URLを渡す。
3. `worldline PR`: 一つのPRを一つの世界線とし、同一seedの基準世界・介入世界・ノード遅延をchecksで実行する。fixtureとlive LLM実測を混同しない。
4. `Human review`: 結果、費用、副作用、権利、安全、再現性を人間が確認した後にだけmergeし、共有世界へ反映する。

Web UIはこのループを可視化するprojectionであり、engine状態、GitHub credential、独自databaseを所有しない。Issue作成時にはsimulationを実行しない。

## Consequences

- コードを書かない参加者はIdea BuilderとIssueだけで参加できる。
- contributorはIssue URLをAI、ローカル、Colabへ渡して実装を始められる。
- Issue数を実装済み世界線数として扱わない。
- PR checksの成功をmergeまたは公開完了として扱わない。
- 同じideaから複数のworldline PRを作り、異なる実装仮説を比較できる。
- Webが停止しても、Issue、branch、PR、CLIの参加経路は残る。

## Alternatives considered

- Idea投稿直後に自動simulationする: 未実装の文章から結果を生成し、再現性と人間レビューを飛ばすため不採用。
- Ideaと実装を同じPRへ入れる: 非技術参加者の障壁が高く、未実装と検証済みが混ざるため不採用。
- 独自Web backendが投稿・実行・保存を所有する: credential、個人情報、費用、運用の境界が初期MVPには過剰なため不採用。
- 一つのIssueを一つの正解worldlineへ固定する: 複数の実装仮説を比較できなくなるため不採用。

## 見直し条件

- GitHub以外の公式受付口を、本人確認、削除、moderation、監査ログ付きで運用できる。
- live LLM runを費用上限、入力検査、model記録、replay artifact、人間確認付きで自動化できる。
- IssueとPRだけでは、同じideaから派生した複数世界線の比較・検索・統計処理が維持できない。
