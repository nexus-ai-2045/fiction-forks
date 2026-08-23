# PROJECT SSOT

## 正本境界

| 対象 | 正本 |
|---|---|
| プロダクトコード | このリポジトリの `src/` |
| シナリオ契約 | `scenarios/` と `docs/simulation-contract.md` |
| シナリオの公開根拠と反証条件 | `docs/scenario-rationale.md` |
| 介入カード | `interventions/` と `CONTRIBUTING.md` |
| フィクション参照レンズ | `docs/fiction-lenses.md` |
| 公開方針 | `README.md`、`SECURITY.md`、`PUBLIC_READY.md` |
| バージョン | `pyproject.toml` の `project.version`。同期規律は `VERSIONING.md`、変更履歴は `CHANGELOG.md` |
| 元議論・非公開証拠 | このリポジトリの外。本文や参加者情報を複製しない |
| ハッカソンの公式根拠 | `docs/official-sources.md` に固定した公式サイトと片山俊大氏 v1.0ペーパー |

## 派生物

CLIのJSON出力、可視化、比較レポートは再生成可能な派生物です。既定ではGit管理しません。結果を研究記録として残す場合は、scenario、intervention、seed、実行versionを必ず併記します。

## 変更ルール

- schemaまたは破滅条件を変更するPRは、既存結果との非互換性を明示します。
- 現実に関する数値は、出典と確認日を持たせます。
- フィクション参照は、作品由来の機能と本プロジェクト独自の実装仮説を分離します。
- 非公開会話、個人情報、秘密情報、実在システムの攻撃手順を取り込みません。
- 公式サイトまたは片山俊大氏 v1.0ペーパーにない内容を「公式」と表示しません。

## 上位台帳

ローカル配置とGitHub owner/visibilityは、workspaceの `ssot-registry.yaml` へ別途登録します。このファイルはworkspace台帳を複製せず、repo内部の責務境界だけを定義します。
