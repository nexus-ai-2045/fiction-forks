# Changelog

Fiction Forksの利用者に影響する変更を記録します。形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) を参考にし、版番号はSemantic Versioningに従います。

## [Unreleased]

- 既存social resultを正本に保ち、run request・event stream・replay・evidenceを同一`run_id`へ束縛する`meta-security-run-bundle/v1` adapterを追加した
- 既存Idea Builderを維持したまま、通常世界線と制度5年遅延を比較し、費用・副作用・provenanceを読めるReact Result Workbench縦切りを追加した
- workbench build前にcanonical manifestのpath・SHA-256・engine/scenario/intervention/seedを検証し、artifact driftをfail closedで拒否するようにした

次のリリースに向けた変更をここへ記録します。

### Changed

- 0.4の基礎として、確認済み`IdeaDraft`、固定catalog、`ProvisionalRunRequest`、`RunSummary`のPython正本と`prepare-preview` CLIを追加した
- template選択の明示確認、完全写像、scenario実在、request provenance、idea lifecycle整合をfail-closedで検証するようにした
- disabled template拒否、catalog正規化、boolean version拒否、実在UTC時刻検証をtransport境界へ追加した
- 自由記述や未知seedからengine入力を生成せず、完全写像できない案を`not-simulatable`として返す契約を追加した
- Issue #12を本文コピーなしのIdea状態projectionへ`listed / not-ready`として取り込み、0.4の実装依存順を正本化した
- 0.4 milestoneを、Doom Map、参加入口、Idea Chat、暫定simulation、Result Browser、結果還流を持つVite + React + TypeScript workbenchとして設計した
- 作品とアイデアを対話で壁打ちし、「この理解でよいか」の本人確認後だけ`IdeaDraft`、暫定preview、Issueへ進む契約を追加した
- preview template catalog、public非同期Actions/local loopback transport、merge済みexact-main公式run、入口別routingを設計契約へ追加した
- Doom Levelはversion付き算出契約が実装されるまで現在値として表示しない境界を明記した
- optional local Codex連携を、raw app-server直結ではなくloopback-only companion、短命token、origin/tool allowlist、version gate付きspikeとして境界化した
- 破滅回避後の次の危機を`doom-candidate`として提案し、人間レビュー済みscenario PRだけがactive doomへ昇格できるロードマップを追加した
- Idea Builderで `Issue → Build → Worldline PR → Simulation` の参加ループと `1 PR = 1 WORLDLINE` を常時確認できるようにした
- Idea作成フォームを「作品」「アイデア」の一ページへ簡略化した
- open/closedを含むIdea Issue履歴と実装済みworldlineをWebへ表示し、各IdeaからAI用PR依頼文を作れるようにした

## [0.3.0] - 2026-08-24

### Added

- 作品名・任意の登場人物名からidea Issueを組み立てる静的Idea Builderと手動GitHub Pages公開workflow
- 一般参加者の`idea` Issue、実装者の`worldline` PR、保守用`maintenance` PRを分けるtemplateとADR 0009
- worldline PRの投稿者、5役×3ターンfixture、2036年比較をGitHub Actions step summaryへ表示するPR contract gate
- 公開branchをcredentialなしで検証するGoogle Colab notebook
- 『涼宮ハルヒの憂鬱』を、分散観測、証拠来歴、異議申立て、停止訓練へ翻訳した世界観測介入
- 世界観測介入専用の5役×3ターンsocial config、決定論fixture、同一seed比較、ノード遅延比較、ADR 0010
- `simulate` と `compare` の機械可読結果を安全に保存する `--output` / `--overwrite` オプション
- 5つの社会役が3ターン対話し、制約付きactionから技術・制度・運用ノードの遅延を決めるAIエージェント層
- fixture、replay、OpenAI Responses Structured Outputsのprovider境界とbefore/after hash chain
- コード不要の固定repo URL入り参加プロンプト、社会シミュレーション設計、ADR 0008、RESULTS
- READMEを「30秒で世界観、3分で比較、PRで未来をfork」の参加導線へ再設計
- README用のオリジナル世界線SVG、ビジュアルシステム、READMEを最初のプレイ画面とするADR
- プロダクト設計、UXフロー、アーキテクチャ、セキュリティモデル
- 決定的engine、フィクション・レンズ、PR単位、技術ツリー、破滅条件、Web/AI境界を固定するADR
- 日本2036の無介入世界線と、2036年に修復不能へ入る透明な破滅条件
- 『ドラえもん』レンズを公共AI・地域データ信託・分散工作拠点へ翻訳した介入例
- 技術・制度・運用ツリーの完了年計算、循環検出、ノード遅延による感度分析
- Python 3.11〜3.13対応のCLI、unit test、GitHub Actions
- repo-preflight、ai-ratchet-gate v0.1.1、SSOT・公開・第三者IP境界
- build backendを脆弱性修正版`setuptools==83.0.0`へ固定

### Fixed

- role-scoped evidenceやprivate contextがモデルの自由記述を介して別の役へ越境しないよう、役間共有を公開allowlistへ限定
- 役間共有を `fiction_forks_observation.v2` へ更新し、固定catalog由来の信頼済みaction semanticsを追加
- replay artifactのhash chainと再計算結果を照合し、改ざんまたは不一致をfail closedで拒否
- malformedなfixture/replay入力をサニタイズ済みcontract errorとして処理
