<!-- repo-preflight:review-record -->

# Repo Preflight review record

## 公開範囲

公開対象は、シミュレーションコード、オリジナルscenario、抽象化したフィクション介入、テスト、説明文書です。非公開会話、個人情報、秘密情報、第三者IPの複製物は対象外です。

## 停止線

- `repo-preflight` のpassはpushまたは公開の承認ではない。
- secretまたはpersonal path候補がある場合は公開しない。
- CIとローカル検証を分離して記録する。
- visibility変更、merge、releaseは操作ごとの人間承認を必要とする。

## 導入ゲート

- `repo-preflight`: 公開、push、PRの各境界で実行する。
- `ai-ratchet-gate`: 公開済みv0.1.1 wheelをSHA-256固定で導入する。
- `github-ops-skills`: identity、owner、visibility、read-backの共通経路として使う。

## 世界観測成果物 maintenance PR前記録

- 検査日時: 2026-08-24（Asia/Tokyo）
- 検査対象branch: `maintenance/haruhi-world-observation-evidence`
- 検査対象HEAD: `745e0d4503e354044f930c2ab8d71964a64dd678`
- 記録方法: この節を追加する文書commitは検査対象HEADの後続であり、コード、artifact、README、ADR、テストを変更しない

### 確認済み

- `python -m unittest discover -s tests -v`: 49 tests、全件pass
- `python -m ai_ratchet_gate --repo .`: pass（現存0件 / 新規0件）
- maintenance PR contract: pass。新しいintervention、social config、fixtureの混在なし
- 同一seed通常比較: 放置世界は2036年に破滅、介入世界は2032年に発動して回避
- ノード5年遅延比較: 2037年発動となり、2036年に破滅
- fixture replay: 5役×3ターン、15 actions、invalid 0、world comparison・actions・hash chainが同値
- artifactとmanifest: engine version 0.3.0、run ID、input digest、final event hash、3件のSHA-256をテストでread-back
- repo-preflight read-only scan: pass、secret finding 0、personal path 0、必須文書欠落0
- 追加ファイル検査: 画像、ロゴ、音声、映像なし。作品名と独自に抽象化した機能以外の第三者素材なし
- worldline PR #6: squash merge済み。main反映、remote branch自動削除、post-merge CI / CodeQL successを確認

### 未確認・人間レビュー待ち

- dependency vulnerability auditはecosystem固有の現在監査が必要なため`unknown`
- このmaintenance branchのGitHub Actionsはpush後のremote CI待ち
- README、ADR 0010、因果仮説、効果量、artifact、第三者権利境界の現在HEADに対する人間目視は未完了
- live OpenAI providerは未実行。fixtureをLLMエージェント実測として扱わない
- push、maintenance PR作成、merge、release、公開告知は独立した操作であり、この記録は承認しない
