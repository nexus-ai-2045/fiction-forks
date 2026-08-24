# コントリビューションガイド

このプロジェクトでは、アイデアと実装を分けます。未実装の着想は一つの`idea` Issue、再現可能な介入実装は一つの`worldline` Pull Requestとして扱います。engine、workflow、文書、依存の変更は`maintenance` Pull Requestです。

## コードを書かない参加

[Fiction Forks Idea Builder](https://nexus-ai-2045.github.io/fiction-forks/)へ作品名、任意の登場人物、未来へ取り入れたい機能、変えたい課題、実現条件、副作用を入力してください。入力はブラウザ内だけで処理され、最後にGitHubのIssue作成確認画面を開きます。GitHub accountを使わない場合はIssue用Markdownをコピーできます。

Idea IssueはAI-agent simulationを実行しません。効果、実現可能性、公式性を認定するものでもありません。実装したいcontributorはIssue URLをAIへ渡すか、ローカルまたはColabで検証してworldline PRへ昇格します。

最初に [プロダクト設計](docs/product-design.md) と [シミュレーション契約](docs/simulation-contract.md) を読み、作品を知らない人にも通じる問いを [フィクション・レンズ](docs/fiction-lenses.md) と同じ形式で一文にしてください。

## Issueからworldline PRへ

### 作業場所を選ぶ

- 外部contributor: [Fork](https://github.com/nexus-ai-2045/fiction-forks/fork) を押し、自分の`<account>/fiction-forks`に`worldline/<slug>` branchを作り、`nexus-ai-2045/fiction-forks:main`へPRします。本repoへのwrite権限は不要です。
- チームメンバー: 本repo内に`worldline/<slug>` branchを作り、同じく`main`へPRします。`main`へ直接pushしません。
- アイデアだけ参加する人: forkもbranchも不要です。Idea BuilderからIssueを作ります。

外部contributorがローカルで始める最小手順:

```powershell
git clone https://github.com/<account>/fiction-forks.git
cd fiction-forks
git remote add upstream https://github.com/nexus-ai-2045/fiction-forks.git
git switch -c worldline/<slug>
```

変更後は自分のforkへ`git push -u origin worldline/<slug>`し、GitHubの`Contribute → Open pull request`からupstreamへPRします。

### AIへ依頼する

READMEの固定プロンプトへIssue URLを貼り、必要ならfork、専用branch、実装、検証、PR作成まで依頼します。AIはPR本文に目的、変更範囲、検証結果、未実装、仮定、残課題、権利・安全確認を書き、人間レビュー前で止まります。

### ローカルで動かす

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m fiction_forks compare `
  --scenario scenarios/japan-2036/scenario.json `
  --intervention interventions/<slug>.json `
  --seed 2036
python -m fiction_forks social `
  --scenario scenarios/japan-2036/scenario.json `
  --intervention interventions/<slug>.json `
  --social-config scenarios/japan-2036/social-<slug>.json `
  --provider fixture `
  --fixture fixtures/social/<slug>.jsonl `
  --output run.json
```

### Colabで動かす

[検証用notebook](https://colab.research.google.com/github/nexus-ai-2045/fiction-forks/blob/main/notebooks/validate-worldline.ipynb)を開き、本repoまたは公開forkのURL、GitHub上のbranch名、slugを指定します。notebookはGitHub APIで本repoからのforkであることをread-only確認してからcloneし、fixtureと決定論比較を実行します。credentialの入力やPR作成は行いません。

PR作成、承認、merge、mainからの反映確認は別の状態です。

## 介入PRの条件

1. 関連する`idea` Issueを一つ指定する。
2. `interventions/<slug>.json`を一つ追加する。
3. `scenarios/japan-2036/social-<slug>.json`を追加する。
4. `fixtures/social/<slug>.jsonl`を追加する。
5. 参照作品と、そこから抽出した機能を自分の言葉で書く。
6. 実現方式、技術・制度・運用ノード、依存先、実装年数、完成証拠を書く。
7. 既存scenarioと同じseedで基準世界・介入世界を比較する。
8. `python -m unittest discover -s tests -v` を通す。
9. 公式画像、台詞、音声、映像、ロゴ、特徴的な口調を収録しない。
10. 一つ以上のノードを意図的に遅らせ、介入が間に合わない条件も確認する。
11. worldline PRへengine、workflow、version、文書等の保守変更を混在させない。判断変更が必要なら先に別のmaintenance PRを作る。

## PRに書くこと

- どの未来問題へ介入するか
- なぜその作品の部品が役立つか
- literal / functional / institutionalのどれか
- 技術ツリー上の未実現部分
- 各ノードの `completion_evidence` とクリティカルパス
- 改善する指標と悪化し得る指標
- 比較結果と、モデル上の限界

効果が大きい介入ほど、費用、副作用、失敗条件を厳しく記述してください。万能な介入は受け付けません。

mergeは作品や介入が「正しい」と認定するものではありません。前提、因果、得失、反証条件が追跡できる比較可能な仮説として受理するものです。

## 技術ツリー

技術ツリーは循環のない有向グラフとして書きます。ノード種別は次の3種類です。

- `technology`: 試作品、相互運用、物理設備
- `institution`: 権限、監査、データ利用、異議申立て
- `operations`: 人材、共同運営、訓練、引継ぎ

`completion_evidence` は「導入した」「整備した」では不十分です。異なる主体が再現できる、住民が異議を申し立てられる、停止訓練の時間を記録できる、といった観測可能な完了条件を書いてください。

## 権利と安全

作品名や公開された概念を議論の参照点として扱えますが、第三者素材をコピーしないでください。公認・公式・共同企画に見える表現も避けてください。実在システムの脆弱性、攻撃手順、個人情報、秘密情報をシナリオへ入力しないでください。

セキュリティ上の信頼境界とWeb/AIで追加される面は [セキュリティモデル](docs/security-model.md) を参照してください。
