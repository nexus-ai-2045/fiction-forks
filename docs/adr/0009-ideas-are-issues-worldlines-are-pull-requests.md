# ADR 0009: アイデアはIssue、動く世界線はPull Requestとする

- Status: Accepted
- Date: 2026-08-24

## Context

ADR 0003は一つの介入を一つのPull Requestに固定した。一方、一般参加者の着想まで介入JSON、技術ツリー、対話fixture、比較結果を必須にすると参加障壁が高い。逆に、未実装の着想と再現可能な実装を同じPR状態で扱うと、シミュレーション済みか、誰が何を検証したかが分からなくなる。

公開Web UIからGitHubへ直接書き込むためのcredentialを配布すると、token漏えい、権限過大、投稿内容の確認不足を招く。参加者が入力した第三者IPや個人情報を独自サーバーへ保存することも避ける必要がある。

## Decision

参加単位を次の二層へ分ける。

1. `idea` Issueは作品名、任意の登場人物名、抽象化した機能、未来課題、実現条件、副作用を記録する。効果、実現可能性、AI-agent実行を検証済みとは扱わない。
2. `worldline` PRは一つのideaを、介入JSON、同じslugのsocial configとfixture、決定論比較、遅延比較、テストへ変換する。

engine、workflow、依存、文書だけを変更するPRは`maintenance`とし、worldlineと分離する。PR本文のhidden markerと変更pathをCIで照合し、種別の混在をfail closedする。

Idea BuilderはGitHub Pages上の静的UIとする。入力はブラウザ内だけで扱い、「GitHubでIssueを確認」を押した時に、prefill済みのGitHub Issue作成画面を開く。自動投稿、GitHub token、独自database、telemetryを持たない。

`worldline` PRではGitHub ActionsがPR author、intervention slug、fixtureの5役×3ターン、決定論比較をstep summaryへ表示する。fixtureはプロトコル検証であり、live LLM実測とは表示しない。

## Consequences

- コードを書けない参加者は、Web UIとGitHub Issueだけで着想を共有できる。
- contributorはIssueをAI、ローカル、Colabのいずれかへ渡し、実装へ昇格できる。
- 外部contributorは公開fork内のbranch、write権限を持つチームメンバーは本repo内のbranchからworldline PRを作る。
- Issue数は実装済み世界線数ではなくなり、PR checksが再現可能性の境界になる。
- GitHub accountなしではIssue投稿できないが、文章をコピーして別経路で相談できる。
- GitHubの公開APIがrate limitまたは障害で失敗するとIdea Builder上の一覧は表示できないが、入力とIssue作成導線は維持する。
- 登場人物名は共通言語の参照点として入力できるが、画像、台詞、ロゴ、音声、外見・口調の再現は受け付けない。

## Alternatives considered

- アイデアもPRにする: review状態と実装済み状態が混ざるため不採用。
- Web UIからGitHub APIへ直接投稿する: public clientへ書込credentialを置けないため不採用。
- 独自backendとdatabaseへ保存する: 初期MVPの運用、個人情報、削除対応が過剰になるため不採用。
- Discussionだけを使う: 構造化field、IssueからPRへのlink、closeによる状態遷移を優先して不採用。

## 見直し条件

- GitHub accountを持たない参加者向けの公式受付窓口を運用できる。
- Idea数が増え、重複検出、moderation、検索にIssueだけでは対応できない。
- GitHub Appを最小権限、監査ログ、credential隔離付きで運用できる。
- live AI-agent runを安全な費用上限と人間確認付きでPR checksへ組み込める。
