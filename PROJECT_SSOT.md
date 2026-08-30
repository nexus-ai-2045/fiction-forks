# PROJECT SSOT

## 正本境界

| 対象 | 正本 |
|---|---|
| プロダクトコード | このリポジトリの `src/` |
| プロダクト体験とロードマップ | `docs/product-design.md` |
| Web UXと画面引継ぎ | `docs/ux-flow.md` |
| ビジュアル文法とtoken | `docs/visual-system.md` |
| アーキテクチャと設計判断 | `docs/architecture.md` と `docs/adr/` |
| シナリオ契約 | `scenarios/` と `docs/simulation-contract.md` |
| 社会エージェント契約 | `scenarios/*/social*.json`、`src/fiction_forks/agent_protocol.py`、`docs/social-simulation.md` |
| Meta-Security Studio交換形式 | `src/fiction_forks/run_bundle.py`は既存social resultを`meta-security-run-bundle/v1`へ射影する薄いadapter。domain resultとrun_idの正本は`src/fiction_forks/social.py`、交換schemaの正本は`nexus-ai-2045/meta-security-sim`、外部実行transportの正本は`nexus-ai-2045/cloud-autopilot` |
| Web参加面 | `web/`。静的Idea Builderを維持し、`web/workbench-src/`がcurated fixtureを投影するResult Workbench縦切りを所有する。状態遷移と破滅判定はPython engine、値とprovenanceは`artifacts/runs/`のartifact・manifestが正本。Doom Map・Idea Chat・公式Result Browser全体は0.4残務 |
| 対話草案 | `src/fiction_forks/participation.py`のversion付き`IdeaDraft` schema。会話全文ではなく本人確認済みprojectionだけを受理する |
| 暫定simulation | `src/fiction_forks/participation.py`の`ProvisionalRunRequest`／`RunSummary`と`catalogs/intervention-templates.v1.json`。`preview_allowed`な固定templateへの完全写像だけを許し、公式結果と分離する |
| Public run transport | triage済みsimulation-requestを`main`固定Actionsで非同期実行する契約（0.4で追加予定）。fork/PR codeとsecretを使わない |
| Local run transport | loopback adapterからcanonical Python CLIを呼ぶ契約（0.4で追加予定）。公開listenと独自engineを持たない |
| Local Codex連携 | optional loopback companion（spike）。公開Web、Codex credential、filesystem、GitHub writeの正本ではない |
| Idea / Worldline境界 | `.github/ISSUE_TEMPLATE/`、`.github/PULL_REQUEST_TEMPLATE/`、`src/fiction_forks/pr_contract.py`、ADR 0009 |
| Idea状態還流 | `catalogs/idea-status.v1.json`の`listed / assigned / implemented / simulated / reported-back` projection。Issue open/closedだけで推定しない。本文は複製しない |
| シナリオの公開根拠と反証条件 | `docs/scenario-rationale.md` |
| 介入カード | `interventions/` と `CONTRIBUTING.md` |
| フィクション参照レンズ | `docs/fiction-lenses.md` |
| 公開方針 | `README.md`、`SECURITY.md`、`PUBLIC_READY.md` |
| セキュリティ境界 | `SECURITY.md` と `docs/security-model.md` |
| バージョン | `pyproject.toml` の `project.version`。同期規律は `VERSIONING.md`、変更履歴は `CHANGELOG.md` |
| 公開curated run | `RESULTS.md` のmanifest記録と `artifacts/runs/` の対応artifact |
| 提出用評価・生ログ | `evaluation/`。domain runtimeや公式結果の正本ではなく、同じrun_idへ結合したlive result・replay・run bundleと、その観測指標を公開する提出用データセット。結果の意味論は`src/fiction_forks/`、公式curated runへの昇格条件は`RESULTS.md`と`artifacts/runs/`が正本 |
| 次の破滅候補 | version付き`DoomCandidate`とscenario PR（0.5 candidate）。人間レビュー前はactive doomではない |
| 元議論・非公開証拠 | このリポジトリの外。本文や参加者情報を複製しない |
| ハッカソンの公式根拠 | `docs/official-sources.md` に固定した公式サイトと片山俊大氏 v1.0ペーパー |

## 派生物

CLIのJSON出力、可視化、比較レポートは再生成可能な派生物です。既定ではGit管理しません。例外として、人間レビューを通すcurated runだけを `artifacts/runs/` へ置き、`RESULTS.md` にfixture/live区分、scenario、intervention、seed、engine version、exact commit、input digest、artifact SHA-256を記録します。ハッカソン提出で再現性を示すlive生ログ・replay・run bundle・解析は`evaluation/`へ置けますが、公式curated runとは区別し、provider、model、source revision、artifact digest、fixture/live区分を保持します。自由記述、role-scoped evidence、credentialは公開artifactから除外します。

## 変更ルール

- schemaまたは破滅条件を変更するPRは、既存結果との非互換性を明示します。
- Accepted ADRの意味を変える場合は、元ADRを履歴なしに書き換えず後続ADRで置換します。
- 現実に関する数値は、出典と確認日を持たせます。
- フィクション参照は、作品由来の機能と本プロジェクト独自の実装仮説を分離します。
- 非公開会話、個人情報、秘密情報、実在システムの攻撃手順を取り込みません。
- 公式サイトまたは片山俊大氏 v1.0ペーパーにない内容を「公式」と表示しません。
- Idea Issueをシミュレーション済み世界線として数えず、PR種別markerと変更pathをCIで照合します。
- 壁打ち、暫定preview、fixture、live run、公式結果を別status・別schemaで扱います。
- 公式結果はworldline PRのmerge後、exact `main` commitから再実行したrunとartifact digestをread-backできた場合だけ昇格します。
- local Codexとの会話全文を自動でrepoまたはIssueへ保存せず、本人確認済みprojectionだけを公開境界へ渡します。
- 破滅回避済みworldlineを上書きせず、次の破滅はscenario PRで審査する別versionとして追加します。

## 上位台帳

ローカル配置とGitHub owner/visibilityは、workspaceの `ssot-registry.yaml` へ別途登録します。このファイルはworkspace台帳を複製せず、repo内部の責務境界だけを定義します。
