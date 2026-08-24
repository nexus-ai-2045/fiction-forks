# Changelog

Fiction Forksの利用者に影響する変更を記録します。形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) を参考にし、版番号はSemantic Versioningに従います。

## [Unreleased]

コード上の現在versionは`0.3.0`です。Git tagとGitHub Releaseは未作成であり、
release時にexact main commit、版番号、実日付を別承認で確定します。

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
