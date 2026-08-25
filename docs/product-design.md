# プロダクト設計

## プロダクトの一文

Fiction Forksは、知っているフィクションから未来を変える機能を抽出し、技術・制度・運用の実装ツリーへ翻訳して、同じ危機条件の日本で結果を比較する参加型シミュレーションである。

## 解く問題

未来の議論は、専門用語だけでは参加者が分断され、物語だけでは実装可能性が曖昧になる。Fiction Forksは、作品名を会話の入口にしつつ、次の翻訳を必須にする。

```text
作品の機能
  -> 作品を知らない人にも通じる社会の問い
  -> 現実の機能的・制度的な同等物
  -> 技術・制度・運用の依存ツリー
  -> 完了を観測する証拠
  -> 費用・副作用・失敗条件を含む世界比較
```

## 想定参加者

| 参加者 | 持ち込むもの | 得るもの |
|---|---|---|
| フィクションの読者 | 作品の構造への直感 | 直感を検証可能な介入へ変える方法 |
| 技術者・研究者 | 実装条件と制約 | 社会制度や運用まで含む比較対象 |
| 政策・法制度の実務者 | 権限、責任、異議申立て | 技術が完成しても発動しない条件の可視化 |
| デザイナー・市民 | 利用者視点と望ましい未来像 | PRとして残る具体的な未来分岐 |
| 作品を知らない参加者 | 現実問題への知識 | 作品知識なしでも同じ問いへ参加できる同義表現 |

## プレイヤーファンタジーと動詞

プレイヤーは、未来を予言する人ではなく「世界線の設計者」である。

- 選ぶ: 作品から一つの機能を選ぶ
- 翻訳する: 現実の問いと実装方式に言い換える
- 組む: 技術、制度、運用を依存ツリーにする
- 証明する: 各ノードの完成証拠を定義する
- 遅らせる: クリティカルパスへ遅延を入れる
- 比較する: 同じseedの基準世界と介入世界を見る
- 共有する: Idea Builderから未実装の着想をIssueへする
- forkする: contributorが再現可能なPRとして新しい世界線を追加する

## コアループ

1. 日本2036のactive doomと、過去のworldline結果を見る。
2. 作品、問題、専門、過去結果、doom candidateのどこから参加するかを選ぶ。
3. チャットへ作品とアイデアを話し、AIまたはguided対話から「この理解でよいか」を受け取る。
4. 本人確認後に`IdeaDraft`を作り、version付きcatalogの`preview_allowed` templateへ写像できる場合だけ暫定simulationを行う。走らない場合は不足条件を返す。
5. 確認済み草案をidea Issueにし、contributorが一つの機能を現実の介入へ翻訳する。
6. 技術ツリー、費用、副作用、失敗条件を組み、介入あり・なしを同じ条件で実行する。
7. 結果と限界をworldline PRにし、人間レビュー後にmergeする。exact `main` commitから公式runを再実行し、artifact digestを読戻せた場合だけIssueとWebへ公式結果を返す。
8. 既存破滅を回避した場合は、副作用と残存リスクから次の`doom-candidate`を作り、scenario PRで次シーズンを審査する。

最短セッションは既存結果を見るだけの1分、作品または問題とアイデアを壁打ちして理解確認と次の行動を得る3分を目標とする。local adapter接続時は同じ3分内の暫定結果、publicでは非同期requestの受付までを対象にし、Issue後のrun完了時間を混ぜない。新規の公式世界線は、調査とレビューを含め数時間から数日を想定する。

## 破滅レベル

破滅レベルは演出用のAI採点ではなく、scenarioが宣言した観測可能な条件から導く。次の表は0.4で実装する表示taxonomyであり、現行scenarioにはレベル閾値と連鎖条件のversion付き契約がまだない。`DoomLevelContract`とPython実装が揃うまで、Webはレベル数値を表示せず、engineが返すcollapse stateとbreached metricsを表示する。

| レベル | 状態 | UIで示すこと |
|---|---|---|
| 0 | 安定 | 破滅条件が管理されている |
| 1 | 兆候 | 一つ以上の悪化指標がある |
| 2 | 圧迫 | 生活、制度、産業への影響が始まる |
| 3 | 危機 | 単一分野では修復できない |
| 4 | 連鎖 | 複数の危機が互いを増幅する |
| 5 | 破滅 | scenarioが定義した修復不能条件に入る |

各active doomは現在レベルだけでなく、発生条件、観測指標、推定到達年、連鎖先、可逆性、根拠の確からしさを表示する。総合レベルは各dimensionの状態と連鎖条件から決定論的に計算し、LLMが直接変更しない。

## 参加入口

最初からIssueやPRを選ばせず、参加者が持っているものから入口を選ぶ。

| 入口 | 最初の問い | 最初の成果物 |
|---|---|---|
| 作品から | どの作品の何を借りたいか | `IdeaDraft` / idea Issue |
| 問題から | どのactive doomを変えたいか | problem-led `IdeaDraft` |
| 専門から | 技術、制度、運用のどこを補えるか | evidenceまたはworldline草案 |
| 結果から | 過去runのどの前提、争点、副作用を直したいか | simulation Issue |
| 次の破滅から | 既存介入が何を新たに壊し得るか | doom-candidate Issue |

参加者は固定roleではない。作品から始め、結果を検証し、後でdoom candidateをred-teamするなど、同じidentityで入口を移動できる。

## 失敗と報酬

失敗はスコアが低いことではない。次の発見も有効な成果である。

- 良い介入だが2036年に間に合わない
- 一つの指標を改善する代わりに別の指標を悪化させる
- 技術は作れるが権限移譲や訓練が完成しない
- 完成証拠が曖昧で、効果を発動させられない

報酬は、介入の強さではなく、因果、費用、限界、反証条件が明確な比較可能世界を一つ増やすことである。

## 進行設計

| 段階 | 参加者ができること | repoに残るもの |
|---|---|---|
| 観察者 | 既存世界を実行する | 再現可能な結果 |
| 実験者 | 遅延やseedを変える | 感度分析 |
| 翻訳者 | 新しい作品レンズを言語化する | 論点と非作品依存の同義表現 |
| 提案者 | Idea Builderで着想を構造化する | idea Issue |
| 世界線設計者 | 介入カードと技術ツリーを作る | Pull Request |
| レビュアー | 根拠、権利、因果、再現性を検査する | 改善された共通契約 |

## Webの現在面と次の面

Webはルールエンジンの状態を所有しない。現在の参加面は次の2つである。

1. Idea Builder: 作品とアイデアだけを一ページで入力する。抽象機能、未来課題、実現条件、副作用はworldline PR化するcontributorが具体化する
2. Issue Preview: 未実装の着想と権利境界を投稿前に確認する

次のWebは「Idea投稿フォーム」ではなく、入口別のworkflowとチャットを持つsimulation workbenchへ進める。主要面は次の7つとする。

1. Doom Map: 日本2036のactive doom、レベル、連鎖、到達年を見る
2. 参加入口: 作品、問題、専門、結果、次の破滅から一つを選び、入口固有の成果物へ分岐する
3. Idea / Problem Chat: 作品またはactive doomとアイデアを話し、「この理解でよいか」を確認する
4. Provisional Preview: 走る案は暫定比較、走らない案は不足条件を見る
5. Result Browser: 過去の公式run、世界比較、技術ツリー、agent争点を見る
6. Issue / PR Handoff: 確認済み草案をIssueへ、再現可能な世界線をPRへ渡す
7. Next Doom: 回避済み世界からdoom candidateを作り、scenario reviewへ送る

画面状態、チャット状態、run状態、schemaを扱うため、0.4 milestoneで`web/`をVite + React + TypeScriptへ移行する。TypeScriptは破滅判定を再実装せず、Python engineが返すversion付きcontractを検証・表示する。公開PagesはPythonを直接実行せず、triage済みsimulation-requestを`main`固定Actionsで非同期実行する。Issue作成前の同期previewは、明示起動したloopback local run adapterだけが提供する。

詳細な状態と文言は [UXフロー](ux-flow.md) に定義する。

## 設計原則

1. 作品名は入口に使い、作品知識を参加条件にしない。
2. 介入には必ず得失と失敗条件を持たせる。
3. 技術の完成と社会実装の完成を分ける。
4. 破滅条件と数値仮説をコードとデータから追跡できるようにする。
5. 画面の演出より、同じ入力が同じ結果になることを優先する。
6. LLMの説明と決定的な状態遷移を分離する。
7. 未実装の着想はIssue、再現可能な実装はworldline PRへ分ける。
8. 会話全文ではなく、本人が確認したprojectionだけを公開境界へ渡す。
9. 暫定preview、fixture、live run、公式結果を表示とschemaで区別する。
10. 破滅回避を勝利として保存し、次の破滅は根拠付きの別scenarioとして追加する。

## 成功指標

初期評価では利用者数より、次を測る。

- 初見の人が30秒で「アイデアはIssue、動く世界線はPR」と説明できる
- 3分以内に通常比較と遅延比較を一回ずつ実行できる
- 新規介入PRが技術・制度・運用の3種と完成証拠を含む
- 改善指標だけでなく、悪化指標または失敗条件が記述される
- 作品を知らないレビュアーが同義表現だけで介入を評価できる
- 同じ入力の結果がCIとローカルで一致する
- 参加者が3分以内に理解確認と、local暫定結果、`not-simulatable`の理由、またはpublic非同期requestの受付を得る
- Ideaの`listed / assigned / implemented / simulated / reported-back`状態がWebとGitHubで一致する
- 破滅レベルを、scenarioの観測条件から再計算できる
- doom candidateが根拠、発生条件、観測指標、可逆性を持ち、人間レビューなしにactive化されない

## 非目標

- 作品世界、キャラクター、物語の再現
- どの作品が優れているかのランキング
- 現実の政策、災害、軍事結果の予測
- LLM同士の自由会話を結果の根拠にすること
- LLMの自由記述を破滅レベル、効果量、公式結果へ直接変換すること
- 公開Webからlocal Codex、shell、filesystemへ直接アクセスすること
- 初期MVPでの大規模3D世界、リアルタイム戦闘、トークン経済

## 実装ロードマップ

| 段階 | 到達点 | 判定 |
|---|---|---|
| 0.1 | CLI、JSON契約、日本2036、一介入、遅延比較 | 完了 |
| 0.2 | 5役×3ターンの制約付きAIエージェント、fixture、replay、live provider境界 | 完了 |
| 0.3 | 公開Idea Builder、Idea Issue、worldline/maintenance PR分離、投稿者別check summary | 2026-08-24 release済み |
| 0.4 milestone | Vite + React + TypeScript、Doom Map、参加入口、Idea Chat、Result Browser | Python engineとのcross-language contract一致 |
| 0.4 milestone | version付きpreview template catalog、入口別routing、`DoomLevelContract` | catalog/path/ID一致と、未実装レベルを現在値として表示しない |
| 0.4 milestone | `guided`対話、version付き`IdeaDraft`、暫定previewまたは`not-simulatable` | LLMが効果量と破滅判定を所有しない |
| 0.4 milestone | public非同期Actions transportとlocal loopback transport | publicはfork code/secretを使わず、両transportが同じrequest/result contractに適合 |
| 0.4 milestone | optional local Codex companionのread-only spike | loopback、短命token、origin/tool allowlist、version gateを実機確認 |
| 0.4 milestone | Issueからmerge済みexact-main公式run、結果還流までの状態台帳 | `listed / assigned / implemented / simulated / reported-back`をread-back可能 |
| 0.5 candidate | 回避済みworldlineからdoom candidateを作りscenario PRで審査 | 勝利を上書きせず、根拠のない破滅をactive化しない |
| 1.0条件 | 公開運用、複数worldline、公式result browser、費用・安全・moderation runbook | 人間レビュー済みの運用証拠が揃う |

0.4は複数PRをまとめる一つのmilestoneであり、文書や小機能ごとに版を上げない。版番号は到達点だけで自動決定せず、[VERSIONING.md](../VERSIONING.md) の互換性規則に従う。
