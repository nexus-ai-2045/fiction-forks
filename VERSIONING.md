# バージョン方針

Fiction ForksはSemantic Versioningを小刻みに運用します。

- patch: バグ修正、小さな互換機能、重要なscenario・文書修正
- minor: 互換性を保った新しいシミュレーション機能または公開API
- major: 既存のscenario、intervention、結果schemaを破壊する変更

すべての変更でversionを上げるわけではありません。同じ目的の変更を一つのレビュー単位にまとめ、通常はpatchを一段だけ上げます。version bump、依存更新、GitHub Actions更新は目的を混ぜず、検証結果を伴うPull Requestで行います。

現在versionの正本は `pyproject.toml` の `project.version` です。packageの `__version__` と実行結果の `engine_version` は同じ値へ同期します。
