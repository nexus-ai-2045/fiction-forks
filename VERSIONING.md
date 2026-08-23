# バージョン方針

Fiction ForksはSemantic Versioningを小刻みに運用します。

- patch: バグ修正、小さな互換機能、重要なscenario・文書修正
- minor: 互換性を保った新しいシミュレーション機能または公開API
- major: 既存のscenario、intervention、結果schemaを破壊する変更

すべての変更でversionを上げるわけではありません。同じ目的の変更を一つのレビュー単位にまとめ、通常はpatchを一段だけ上げます。version bump、依存更新、GitHub Actions更新は目的を混ぜず、検証結果を伴うPull Requestで行います。

## 版の正本と同期

- 正本: `pyproject.toml` の `project.version`
- 同期対象: `src/fiction_forks/__init__.py` の `__version__`
- 同期対象: シミュレーション結果の `engine_version`
- 変更履歴: `CHANGELOG.md`
- Git tag: release時にだけ `v<version>` をexact main commitへ付ける

unit testが三つのversion不一致を検知する。ずれた場合は個別に数字を合わせるだけでなく、同じversion変更PRで正本、同期対象、CHANGELOGを更新してから再検証する。

## 更新手順

1. `[Unreleased]` に利用者影響を記録する。
2. 互換性からpatch / minor / majorを人間が判断する。
3. 正本と同期対象を一つのPRで更新する。
4. Python 3.11と3.13、通常比較、遅延比較、公開ゲートを実行する。
5. PRをmergeし、exact main CIを確認する。
6. tag・GitHub Releaseの対象commitと公開内容を提示し、別承認を得る。

自動version bump botは使用しない。scenarioや文書の小変更だけで機械的にversionを上げず、releaseの意味がある単位で小さく上げる。
