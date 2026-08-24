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
