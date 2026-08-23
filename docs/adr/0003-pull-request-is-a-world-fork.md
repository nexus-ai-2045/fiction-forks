# ADR 0003: 一つのPull Requestを一つの未来分岐とする

- Status: Accepted
- Date: 2026-08-24

## Context

未来アイデアを会話や投稿だけで集めると、前提、効果、副作用、実行結果が分離し、比較と再現ができない。GitHubには差分、review、CI、履歴という共同編集機構がある。

## Decision

一つの介入または一つのscenario変更を、一つのPull Requestとして提出する。PRには介入JSON、通常比較、少なくとも一つの遅延比較、費用、副作用、失敗条件、権利・安全確認を含める。

複数の独立した作品レンズや介入を一PRへ束ねない。engine、workflow、version変更は介入PRと分離する。

## Consequences

- PR URLが再現可能な世界線の識別子になる。
- 結果と前提を同じreview単位で検査できる。
- 小さな提案でもJSONと検証の作業が必要になる。
- mergeは「正しい未来」の認定ではなく、比較可能な仮説として受理したことを意味する。

## Alternatives considered

- issueや掲示板だけで募集する: 着想受付には使えるが実行可能な成果にならないため主単位にはしない。
- 一つの巨大scenarioファイルへ直接追記する: reviewとrollbackが難しいため不採用。

## 見直し条件

Web BuilderからPRを作る場合も、最終成果は同じdiff、test、review契約へ変換する。
