# Architecture Decision Records

ADRは、現在の設計が「何を選んだか」だけでなく、「なぜ選び、何を捨て、いつ見直すか」を残す正本である。

## 状態

- `Accepted`: 現在の設計契約
- `Proposed`: レビュー中
- `Superseded`: 後続ADRで置換済み
- `Deprecated`: 新規採用しないが互換性のため残る

## Index

| ADR | 状態 | 判断 |
|---|---|---|
| [0001](0001-deterministic-engine-owns-state.md) | Accepted | 決定的ルールエンジンが状態遷移を所有する |
| [0002](0002-fiction-is-a-shared-language-lens.md) | Accepted | フィクションを複製物ではなく共通言語レンズとして使う |
| [0003](0003-pull-request-is-a-world-fork.md) | Accepted | 一つのPRを一つの未来分岐とする |
| [0004](0004-technology-tree-includes-institutions-and-operations.md) | Accepted | 技術ツリーに制度と運用を含める |
| [0005](0005-collapse-means-loss-of-repairability.md) | Accepted | 破滅を修復可能性の喪失として明示判定する |
| [0006](0006-web-and-ai-are-projections.md) | Accepted | WebとAIをengine結果の投影層にする |
| [0007](0007-readme-is-the-first-play-surface.md) | Accepted | READMEを最初のプレイ画面として設計する |
| [0008](0008-ai-agents-choose-bounded-actions.md) | Accepted | AIは制約付き行動を選び、engineが世界状態を所有する |
| [0009](0009-ideas-are-issues-worldlines-are-pull-requests.md) | Accepted | アイデアはIssue、動く世界線はPull Requestとする |
| [0010](0010-independent-observation-requires-contestation.md) | Accepted | 世界観測は独立照合・来歴・異議申立てが揃うまで発動しない |
| [0011](0011-participation-is-a-reviewed-control-loop.md) | Accepted | Issue、worldline PR、simulation、人間レビューを一つの参加ループにする |
| [0012](0012-chat-first-provisional-simulation-and-local-codex-boundary.md) | Accepted | チャット壁打ち、暫定simulation、local Codex、次の破滅を公式世界線から分離する |
| [0013](0013-local-transport-shares-the-participation-contract.md) | Accepted | local run transportを参加契約へ一本化し、承認済み世界線をcatalogだけに置く |
| [0014](0014-emergence-metrics-are-observational-not-evidence.md) | Accepted | 創発指標を観測記録として扱い、創発の証拠にしない |

## 追加方法

連番のMarkdownを追加し、次を記述する。

1. StatusとDate
2. Context
3. Decision
4. Consequences
5. Alternatives considered
6. 見直し条件

既存判断を変更する場合は元ADRを書き換えず、新しいADRから関係を明示する。判断全体を置換する場合は`Supersedes`、判断の一部だけを上書きし残りを有効に保つ場合は`Amends`を使い、どちらも対象ADRと上書きする範囲を書く。誤字やリンク修正を除き、Accepted ADRの意味を履歴なしに変更しない。

新しいADRを追加したら、上のIndexへ同じ連番の行を必ず足す。`tests/test_docs.py`がIndexと実ファイルの双方向一致を検査するため、登録漏れはCIで失敗する。
