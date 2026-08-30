# バージョン方針

Fiction ForksはSemantic Versioningを小刻みに運用します。

- patch: バグ修正、小さな互換機能、重要なscenario・文書修正
- minor: 互換性を保った新しいシミュレーション機能または公開API
- major: 既存のscenario、intervention、結果schemaを破壊する変更

すべての変更でversionを上げるわけではありません。同じ目的の変更を一つのレビュー単位にまとめ、通常はpatchを一段だけ上げます。version bump、依存更新、GitHub Actions更新は目的を混ぜず、検証結果を伴うPull Requestで行います。

## 版の正本と同期

- 正本: `pyproject.toml` の `project.version`
- 同期対象: `src/fiction_forks/__init__.py` の `__version__`
- 独立正本: `src/fiction_forks/engine.py` の `ENGINE_VERSION`。物理ロジック、結果schema、計算意味論が変わるときだけ上げ、文書・UI・証拠公開だけのpatch releaseでは維持する
- 変更履歴: `CHANGELOG.md`
- Git tag: release時にだけ `v<version>` をexact main commitへ付ける

repositoryのpublic/privateは配布versionとは別の状態である。public化にtagやGitHub Releaseは必須ではなく、visibility変更とrelease作成はそれぞれ別のpreflight・人間承認として扱う。

unit testは配布versionと`__version__`の同期、および結果の`engine_version`と`ENGINE_VERSION`の同期を別々に検知する。履歴artifactは生成時のengine versionを保持し、配布versionへ機械的に書き換えない。

## 更新手順

1. `[Unreleased]` に利用者影響を記録する。
2. 互換性からpatch / minor / majorを人間が判断する。
3. 配布version正本と`__version__`を一つのPRで更新する。engine意味論が変わる場合だけ`ENGINE_VERSION`と対応artifactを別途更新する。
4. Python 3.11と3.13、通常比較、遅延比較、公開ゲートを実行する。
5. PRをmergeし、exact main CIを確認する。
6. tag・GitHub Releaseの対象commitと公開内容を提示し、別承認を得る。

自動version bump botは使用しない。scenarioや文書の小変更だけで機械的にversionを上げず、releaseの意味がある単位で小さく上げる。
