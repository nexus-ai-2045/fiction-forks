# セキュリティモデル

## Overview

Fiction Forksは、ローカルCLI、静的GitHub Pages Idea Builder、公開GitHub repoを主な面に持つ社会シミュレーションMVPである。認証、常駐サーバー、データベースは持たない。Idea Builderは公開Issue一覧をGitHub APIからread-onlyで取得し、投稿時はGitHubの確認画面を開く。任意のlive AI providerだけが明示確認後に外部APIを呼ぶ。主な保護対象は、決定的なシミュレーション結果、部分観測、公開根拠の境界、参加者の安全、第三者IP、credential、CIと依存関係の完全性である。

## Threat Model, Trust Boundaries, and Assumptions

### 信頼境界

| 境界 | 未信頼側 | 信頼側へ入れる条件 |
|---|---|---|
| PR入力 | scenario、intervention、文書、作者の主張 | schema、test、review、権利・安全確認 |
| Idea Chat入力 | 作品名、アイデア、自由記述、会話履歴 | 文字数・turn上限、本人確認済みprojection、strict `IdeaDraft` |
| GitHub公開API | Issue title、author、URL | HTTPS、read-only、`textContent`描画、取得失敗時fallback |
| JSON実行 | ローカルまたは取得したJSON | size制限予定、型・依存・循環検証 |
| 根拠 | 外部URL、統計、作品解釈 | 公式性と参照根拠を分離し、確認日を記録 |
| AI出力 | action、説明、target、evidence ID | strict schema、固定catalog、engine非変更 |
| Local companion | browser origin、Codex protocol、session | loopback、短命token、origin/tool allowlist、version gate |
| 暫定preview | 確認済みIdeaDraft、catalog entry | `preview_allowed`固定interventionへの完全写像、利用者確認、input digest |
| Public run request | GitHub Issue payload、catalog ID、scenario、seed | maintainer triage、strict schema、`main`固定workflow、fork/PR code不使用 |
| Doom candidate | AIまたは人間が提案する次の危機 | 根拠、発生条件、観測指標、可逆性、scenario PR |
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
- 暫定preview、fixture、live run、公式結果を同じ表示またはstatusで扱わない
- public originからraw Codex app-server、shell、filesystemへ直接接続しない
- 新しい破滅を人間レビューなしでactive scenarioへ昇格しない

## Attack Surface, Mitigations, and Attacker Stories

### JSONとルールエンジン

現実的な攻撃は、巨大入力による資源消費、深い依存グラフ、型の境界値、誤解を招く効果量、作品由来と偽る根拠である。現在はengineが参照するscenario・shock・collapse・technology treeのobject/list境界、必須field、数値型（booleanを除く）、未知依存、重複ID、循環、指標範囲を検証し、契約違反は`ContractError`で停止する。これは汎用JSON Schema検証を保証しない。Web入力を受ける前に完全なschema、ファイルサイズ、ノード数、年数範囲、実行時間の上限を追加する。

### GitHubとCI

悪意あるPRはworkflow、依存、外部URL、生成物へ変更を混ぜられる。Actionsはexact commit、Python toolはhash付きwheelへ固定し、CI権限は`contents: read`に限定する。依存更新、workflow変更、gate baseline変更は通常介入と分離してレビューする。加えて、PR契約gate自身がPRのコードで実行されると、`src/fiction_forks/pr_contract.py`を書き換えるPRが混在禁止や5役×3ターン検査を素通しできる。そのため`pr-contract` jobはgateのコードをbase ref (`github.event.pull_request.base.sha`) から別path (`gate-base/`) へcheckoutし、`PYTHONPATH`をbase側の`src`に向けて実行する。PR側のtreeはdiff読み取りと入力fileの検査対象としてのみ使う。PR本文の種別markerを後から書き換える経路も塞ぐため、`pull_request`の`types`に`edited`を含めて再検査させる。残る前提として、workflow定義自体はPR側が使われるため、`.github/`配下の変更は人間レビューが必要である。

### 誤情報と安全保障表現

シミュレーションを予測、政府見解、作品公式企画として表示することが主要な誤用である。README、resultのassumption notice、公式根拠文書、権利通知で境界を示す。実在インフラの脆弱性、標的、攻撃手順は入力対象外とする。

### プライバシーと秘密

非公開Discord本文、応募者情報、メール、ローカル絶対path、API key、tokenをcommitしない。公開前にrepo-preflightのsecret scanとpersonal-path scanを実行し、目視レビューを別に行う。

### Web・AI

Idea Builderはdependency-freeな静的HTML/CSS/JavaScriptとし、入力を独自serverへ送信、保存しない。GitHub tokenを要求せず、Issue作成URLへtitle/bodyをprefillしてGitHub側の確認画面を開く。自由入力と公開API由来のtitle/authorは`innerHTML`へ渡さず`textContent`で描画する。CSPはself-originのscript/styleと`api.github.com`へのread-only接続だけを許可する。公開APIのrate limit、障害、応答形式不正はidea一覧だけをfallback表示にし、入力導線を停止させない。

Issue URLは入力をquery stringへ含むため、共有端末のhistoryや外部画面共有に残る可能性がある。UIは個人情報、秘密情報、攻撃手順の入力を禁止し、GitHub遷移前に権利・安全checkboxと内容previewを必須にする。GitHubへ遷移した後の保存、公開、削除はGitHubと投稿者の責任境界になる。

AI層ではprompt injection、根拠捏造、role-scoped observationの越境、secret送信を想定する。役ごとの観測を最小化し、出力をstrict schemaで検査し、未知fieldと観測外evidenceを拒否する。公開artifactはallowlist projectionとして自由記述、条件本文、role-scoped evidence IDを除外する。設定全体、文字列、roles、turns、1 runのprovider call数を上限化する。live OpenAI providerは公式SDK、`store=false`、明示model、API key、`--confirm-live`を必須にし、CIから呼ばない。

0.4 milestoneのIdea Chatでは、会話全文、model出力、暫定previewを公式結果へ混ぜない。対話providerは理解確認と`IdeaDraft`候補だけを返し、参加者が「この理解でよい」と確認するまでIssue URL、engine request、外部保存へ渡さない。providerが利用不能でも参加できる`guided` modeを維持する。

local Codex連携はpublic Pagesからraw app-serverへ直接接続せず、loopback-only companionを挟む。主要な攻撃は、悪意ある公開ページからlocalhostへの接続、DNS rebinding、origin偽装、token窃取、prompt injectionによるshell/filesystem/GitHub操作、別repoまたはprivate fileの読取、protocol version driftである。companionはsessionごとの短命capability token、厳密なorigin allowlist、対象repoのread-only projection、tool deny-by-default、turn/size/time上限、version付きschemaを必須にする。app-serverがexperimentalである間はfeature flagを既定offとし、未対応versionまたは認証不明を`guided` fallbackにする。

暫定previewは既存scenarioと`catalogs/intervention-templates.v1.json`の`preview_allowed` templateに完全に写像でき、利用者がtemplate IDを確認した場合だけ決定論engineを呼ぶ。Idea本文で参照先interventionのmetric、効果量、技術ノード、完成年を変更せず、LLMに不足値を補わせない。公式結果と異なるbadge、URL、schema fieldを使い、scenario、seed、engine version、template ID、input digest、未確定fieldを表示する。

公開PagesはPython engineへ直接接続しない。public previewは、利用者がGitHub確認画面から送信したversion付きsimulation-requestをmaintainerが`simulation-ready`へtriageした後、`main`に固定したworkflowで非同期実行する。workflowはIssue payloadをstrict schemaで検証し、forkまたはPRのcodeをcheckoutせず、secretを渡さない。Issue本文を`${{ }}`またはshell引数へ直接展開せず、`GITHUB_EVENT_PATH`をJSON parserで読む。triage時のrequest digestと実行時main SHAを記録して同じ組み合わせを冪等化し、raw自由文をartifactやcommentへ反射しない。engine実行jobは`contents: read`、検証済みsummaryをIssueへ返すjobだけを`issues: write`とし、権限を分離する。

Issue送信前の同期previewは、利用者が明示起動した`127.0.0.1` local run adapterに限定する。local adapterもlocal Codex companionと同じく、sessionごとの短命capability token、exact Origin allowlist、JSON Content-Typeとcustom headerによるCORS preflightを要求し、`Origin: null`とsimple requestを拒否する。request body、同時run数、run timeoutへ上限を設け、未接続、token不一致、origin不一致、上限超過ではengineを起動せず`guided`または`not-available`へfail closedする。

PR-headのCI artifactはcandidateであり、公式結果ではない。worldline PRのmerge後にexact `main` commitから再実行し、main commit、engine version、input digest、artifact digestをread-backできた結果だけをofficialへ昇格する。

破滅回避後のdoom candidateは、ゲームを継続するための自動ペナルティではない。元介入との因果、現実リスクへの接続、発生条件、観測指標、連鎖、可逆性を必須にし、scenario PRの人間レビュー前にactive doomまたは破滅レベルへ反映しない。

現在はサーバー、認証、秘密データ保存がないため、SQL injection、CSRF、tenant越境、session theftは直接のruntime面ではない。将来それらを導入した時点で再評価する。

## Severity Calibration

| 重要度 | このrepoでの例 |
|---|---|
| Critical | 公開CIや将来サービスからcredentialを取得し、他systemへ継続アクセスできる |
| High | engine結果を検証なしで改変できる、公開物へ個人情報や実用的な重要インフラ攻撃手順が入る |
| Medium | 悪意ある入力でCIや将来Webを継続的に停止させる、公式根拠と独自仮説を誤表示する |
| Low | ローカルCLIの限定的なエラー表示、攻撃者制御がない表示上の不整合、文書リンク切れ |

脆弱性の報告方法と公開issueへ書いてはいけない内容は [SECURITY.md](../SECURITY.md) に従う。
