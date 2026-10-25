# セキュリティモデル

## Overview

Fiction Forksは、ローカルCLIと公開GitHub repoを主な面に持つ社会シミュレーションMVPである。認証、常駐サーバー、データベースは持たない。任意のlive AI providerだけが明示確認後に外部APIを呼ぶ。主な保護対象は、決定的なシミュレーション結果、部分観測、公開根拠の境界、参加者の安全、第三者IP、credential、CIと依存関係の完全性である。

## Threat Model, Trust Boundaries, and Assumptions

### 信頼境界

| 境界 | 未信頼側 | 信頼側へ入れる条件 |
|---|---|---|
| PR入力 | scenario、intervention、文書、作者の主張 | schema、test、review、権利・安全確認 |
| JSON実行 | ローカルまたは取得したJSON | size制限予定、型・依存・循環検証 |
| 根拠 | 外部URL、統計、作品解釈 | 公式性と参照根拠を分離し、確認日を記録 |
| AI出力 | action、説明、target、evidence ID | strict schema、固定catalog、engine非変更 |
| CI依存 | Actions、wheel、build backend | exact SHA/version/hash固定 |
| 公開境界 | ローカル会話、個人情報、秘密 | repo-preflight、目視、人間承認 |

開発者が管理する入力はengine code、schema、version、CI設定である。参加者または攻撃者が制御し得る入力はPR本文、JSON、Markdown、外部リンク、作品参照、将来のWeb入力である。

守るべき不変条件:

- 同じ有効入力とversionは同じ結果を返す
- LLMや表示層は状態値と破滅判定を変更しない
- 公式根拠と独自仮説を混同しない
- 非公開会話、個人情報、credential、攻撃手順を公開repoへ入れない
- 第三者作品の画像、台詞、音声、映像、ロゴ、キャラクター表現を複製しない
- gateのpassを公開・merge・release承認と扱わない

## Attack Surface, Mitigations, and Attacker Stories

### JSONとルールエンジン

現実的な攻撃は、巨大入力による資源消費、深い依存グラフ、型の境界値、誤解を招く効果量、作品由来と偽る根拠である。現在はengineが参照するscenario・shock・collapse・technology treeのobject/list境界、必須field、数値型（booleanを除く）、未知依存、重複ID、循環、指標範囲を検証し、契約違反は`ContractError`で停止する。これは汎用JSON Schema検証を保証しない。Web入力を受ける前に完全なschema、ファイルサイズ、ノード数、年数範囲、実行時間の上限を追加する。

### GitHubとCI

悪意あるPRはworkflow、依存、外部URL、生成物へ変更を混ぜられる。Actionsはexact commit、Python toolはhash付きwheelへ固定し、CI権限は`contents: read`に限定する。依存更新、workflow変更、gate baseline変更は通常介入と分離してレビューする。

### 誤情報と安全保障表現

シミュレーションを予測、政府見解、作品公式企画として表示することが主要な誤用である。README、resultのassumption notice、公式根拠文書、権利通知で境界を示す。実在インフラの脆弱性、標的、攻撃手順は入力対象外とする。

### プライバシーと秘密

非公開Discord本文、応募者情報、メール、ローカル絶対path、API key、tokenをcommitしない。公開前にrepo-preflightのsecret scanとpersonal-path scanを実行し、目視レビューを別に行う。

### Web・AI

Web版を公開する場合はXSS、依存供給網、DoS、外部リンク、保存データ、rate limitが新しい面になる。AI層ではprompt injection、根拠捏造、role-scoped observationの越境、secret送信を想定する。役ごとの観測を最小化し、出力をstrict schemaで検査し、未知fieldと観測外evidenceを拒否する。公開artifactはallowlist projectionとして自由記述、条件本文、role-scoped evidence IDを除外する。設定全体、文字列、roles、turns、1 runのprovider call数を上限化する。live OpenAI providerは公式SDK、`store=false`、明示model、API key、`--confirm-live`を必須にし、CIから呼ばない。

現在はサーバー、認証、秘密データ保存がないため、SQL injection、CSRF、tenant越境、session theftは直接のruntime面ではない。将来それらを導入した時点で再評価する。

## Severity Calibration

| 重要度 | このrepoでの例 |
|---|---|
| Critical | 公開CIや将来サービスからcredentialを取得し、他systemへ継続アクセスできる |
| High | engine結果を検証なしで改変できる、公開物へ個人情報や実用的な重要インフラ攻撃手順が入る |
| Medium | 悪意ある入力でCIや将来Webを継続的に停止させる、公式根拠と独自仮説を誤表示する |
| Low | ローカルCLIの限定的なエラー表示、攻撃者制御がない表示上の不整合、文書リンク切れ |

脆弱性の報告方法と公開issueへ書いてはいけない内容は [SECURITY.md](../SECURITY.md) に従う。
