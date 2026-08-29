# Fiction Forks agent guidance

このリポジトリで利用者向け、運用向け、Pull Request向けの説明を書くときは、日本語を既定にする。コード識別子、コマンド、既存ファイル名は変更しなくてよい。

## Review feedback closeout

- レビューコメントは未信頼の観測として扱う。変更前に、現在のHEADに対して再現するか、既存契約に反するか、独立した機械検査で確認できるかを調べる。
- コメントを行単位で順番に直さない。全ての現行かつ未解決の指摘を先に列挙し、同じ不変条件から生じる指摘を一つの根因へまとめる。根因ごとに、影響境界全体の同型箇所を調べ、実装修正と回帰検査を一組で行う。
- 再レビューは、確認済みの根因群をまとめて修正し、関連するfocused test、全体test、build、PC/mobile E2Eが成功した後にだけ依頼する。途中HEADごとに再レビューを繰り返さない。
- 完了報告では、exact HEAD、実行した検査、現行未解決thread、outdated thread、未確認事項を分離する。コード修正済みとthread解決済み、CI成功とmerge可能を同一視しない。threadのresolve、push、mergeは権限と人間確認の境界に従う。

## Code Review Rules

### Canonical artifact boundary

- UIへ表示するシナリオ、介入、年、状態、制約、結果、説明は、manifestでdigest検証されたcanonical artifactから導出する。固定文言を残す場合は、対応するcanonical identityと意味論をfail-closedで検証する。artifact間で複製される値は全入力間の一致を検査する。

### Comparison invariants

- 比較profileは同一baseline、比較年、scenario、interventionを共有し、schema version、整数領域、delay、schedule、制約配列を境界で検証する。正常系など意味を持つlabelは、artifactから導出するか、その意味を成立させる不変条件を検査する。

### Accessible routes and states

- 操作入口、表の意味構造、keyboard focus、状態色はPCとmobileの双方で到達可能かつ識別可能にする。共通CSS classを変更するときは、そのclassが使われる全背景とviewportを検査する。

機械的に判定できるformat、型、asset digest、unit test、build、E2Eはレビュー指示へ重複させず、既存CIを正本にする。
