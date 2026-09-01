# ADR 0013: local run transportを参加契約へ一本化し、承認済み世界線をcatalogだけに置く

- Status: Accepted
- Date: 2026-09-01
- Amends: ADR 0012が定めたtemplate catalogとtransport境界のうち、local adapterのrequest schemaと承認済み世界線の宣言場所

## Context

ADR 0012は「publicの非同期transportとlocalの同期transportは同じrequest/result contractへ適合させる」と決め、`docs/architecture.md`のレイヤ表も「Local run transportは同じrequest schemaをcanonical Python CLIへ渡す」と宣言していた。実装はそうなっていなかった。

`src/fiction_forks/local_adapter.py`は`fiction_forks_local_run_request.v1`という独自schema（`worldline_id` / `provider` / `seed` / `confirm_live`）を持ち、`participation.py`の`validate_provisional_request`も`ProvisionalRunRequest`も一度も呼んでいなかった。さらにmodule内の`WORLDLINES`辞書が、scenario、intervention、social config、fixtureのpathを直接持っていた。これは`catalogs/intervention-templates.v1.json`と並ぶ**第二の承認済み世界線定義**である。

二重定義は次を実際に生んでいた。

- catalogは`allowed_seeds: [2036]`を宣言しているのに、adapterは0〜2^31-1の任意seedを通していた。
- catalogは`intervention_sha256`でinterventionを固定しているのに、adapterが渡すsocial configとfixtureは何も固定されていなかった。`WORLDLINES`のsocial configとinterventionが正しい組であることは、`agent_protocol.validate_social_config`が実行時に偶然拒否するかどうかに依存していた。
- `delay_profile`という概念がadapter側に存在せず、catalogが将来遅延profileを増やしたときに「宣言した遅延が黙って無視された結果」を返す経路が空いていた。
- request bodyがproviderを直接運ぶため、`ProvisionalRunRequest.v1`が「model/provider、任意CLI引数は受け付けない」と契約している境界の外に、見分けのつかない別ルートが並んでいた。

同じmoduleのsession tokenも、`secrets.token_urlsafe(32)`を起動時に1回生成して`serve_forever`の間ずっと使い回しており、`docs/architecture.md`が要求する「sessionごとの短命capability token」を満たしていなかった。

## Decision

catalogを唯一の承認済み世界線定義へ昇格し、local run requestを`ProvisionalRunRequest` envelopeへ寄せる。

1. `catalogs/intervention-templates.v1.json`の各templateへ、`social_config_path`、`social_config_id`、`social_config_sha256`、`fixture_path`、`fixture_sha256`をflatな必須fieldとして追加する。`catalog_version`を3、`template_version`を3へ上げる。optional fieldにしない。既定値へのfallbackも作らない。新fieldを欠くcatalogは`missing fields`で即座に拒否する。
2. digestはfileの生バイトではなく、parse後の値をcanonical JSONにしてから取る。JSONLは1行ずつparseしたobjectのlistを対象にする。改行コードの差でdigestが動かないようにする。
3. `participation.py`が絶対path禁止・`..`禁止・正規表現完全一致・root脱出禁止の4段検査を`_safe_repo_path`として共通化し、intervention、social config、fixtureの3本へ横展開する。scenarioはauthored fieldにせず、既存の`scenarios/**/scenario.json` globによる「scenario_idはちょうど1回だけ解決する」一意性不変を`_resolve_scenario_path`として抽出して再利用する。
4. catalog検証の中で`agent_protocol.validate_social_config(social_config, intervention)`を呼び、social configとinterventionの1:1束縛を構造的に保証する。`WORLDLINES`が「たまたま正しい組」だった状態を消す。
5. `resolve_template_inputs`を`participation.py`の公開関数として追加する。検証済みcatalogから、CLIへ渡すrepo相対posix pathの4本だけを返す。transportがpath知識を持つ唯一の入口とし、絶対pathは返さない。argvは`run_bundle`がbundleとevidenceへ記録するため、絶対pathにするとoperatorのhome directoryがartifactへ混入する。
6. `local_adapter.py`から`WORLDLINES`を撤去する。request schemaを`fiction_forks_local_run_request.v2` envelope（`schema_version` / `run_request` / `execution`）へ置き換え、`run_request`は`validate_provisional_request`へそのまま渡す。v1との並行サポートはしない。adapterとUIは同じrepoから同時に配布される。
7. adapterは起動時にcatalogを読んで検証し、落ちるなら起動しない。承認済みtemplate集合はsession中に入れ替わらない。runごとにも`validate_provisional_request`を再実行し、run間のfile差し替えを捕まえる。
8. 失敗の帰属をHTTP statusで分ける。browserが送ったrequestの契約違反だけを`ContractError` → 400 `invalid_run_request`とする。server側の事情（catalog fileの欠落、壊れたJSON、壊れたcatalog、CLIの異常終了、timeout、成果物の読み取り失敗、bundle digest不一致）は`LocalRuntimeError` → 500 `local_run_failed`、同時run拒否は`LocalBusyError` → 409 `run_already_in_progress`とする。両方を`ContractError`へ寄せると、operatorの環境が壊れているだけの場合でも「あなたの要求が契約違反」と誤報し、原因を切り分けられない。`resolve_template_inputs`が投げる「未登録template」「preview不許可template」はrequest側の違反なので、server側の失敗として包まない。
9. providerは`ProvisionalRunRequest`へ入れず、transport層の`execution`に残す。`execution.provider_id`は起動時grant表へのindexであってengine入力ではない。live実行の可否は、browserが送った文字列ではなく解決済みgrantと`confirm_live`の一致で判定する。
10. local transportは`none`以外のdelay profileをfail-closedで拒否する。CLIの`social`サブコマンドに遅延引数が無いためである。catalogへ`supported_delay_profiles`を新設して、transportの能力限界をcatalogへ持ち込むことはしない。
11. `GET /api/health`は`worldlines`をやめ、`preview_allowed`なtemplateのprojectionを返す。TypeScriptはcatalog fileを読まないため、browserが`ProvisionalRunRequest`を組むための入力補助として配る。path、`social_config_sha256`、`fixture_sha256`は載せない。projectionは権限を与えるものではなく、返ってきたrequestは再検証する。
12. session tokenへ寿命を持たせる。`--session-ttl-seconds`（既定900秒）で宣言した時間を過ぎたら、同じprocessでも`session_not_allowed`で拒否する。時刻は`time.monotonic()`で測り、wall clockの跳躍に依存しない。

## Allowed

- catalogが宣言したtemplate、seed、delay profileの範囲でloopback adapterからPython CLIを同期実行する。
- workbenchのprovider selectとper-runのlive確認チェックボックスを維持する。
- health projectionからbrowserが`ProvisionalRunRequest`を組み立てる。

## Prohibited

- `local_adapter.py`のsourceへ`scenarios/`、`interventions/`、`fixtures/`のpath literalを書く。残してよいのは`catalogs/intervention-templates.v1.json`の1本だけとする。
- catalogのtemplateへoptional fieldを作る、または新fieldへ既定値fallbackを与える。
- request bodyからmodel名、endpoint、project、location、任意CLI引数を受け取る。
- fileの生バイトのSHA-256をcatalogのdigestとして使う。
- `none`以外のdelay profileを、遅延を無視したまま実行する。

## Consequences

- 承認済み世界線を変えるにはcatalogのmaintenance PRが要る。ADR 0012が定めた「catalogの追加・変更・削除はpreview実行許可範囲の変更」という人間レビュー境界が、local transportにも実際に効くようになる。
- adapterがseedとdelay profileをcatalogどおりに拒否するようになり、UIとCLIとworkflowが同じ拒否理由を返す。
- `template_version`を3へ上げたため、v2として確認済みのtemplate confirmationは再確認が要る。利用者が見ていないsocial config・fixture固定を含む新templateへ、古い確認が結合しないようにするための意図的な非互換である。
- session tokenの寿命が切れると、adapterを再起動するまで実行できない。UIには403として現れる。長時間放置したadapterのtokenがbrowserに残り続ける窓は閉じる。
- catalog検証がrunごとにsocial configとfixtureを読み直すため、runあたりのfile I/Oが増える。同時runは既存の`_run_lock`で1件に制限されているため実害は小さい。

## Alternatives considered

- **docsを実装に合わせて緩める**: レイヤ表の「同じrequest schema」を「独自のlocal schema」へ書き換える案。最小の変更で済むが、二重定義とseed不整合をそのまま残す。宣言に実装を寄せる方向を採り、この案は採らなかった。
- **social config / fixtureをpathとschema versionだけで縛る**: 隣にある`intervention_sha256`より意図的に弱い規律になる。同じcatalog内で強度が非対称になるのは後退なので採らなかった。
- **`social_run`をnested objectにし、`status == "preview_allowed"`のときだけ必須にする**: `tests/test_pr_contract.py`のinline catalogのtemplateは`status: "preview_allowed"`であり、条件付きrequiredにしても壊れるテストは1件も減らない。`_exact_fields`の表現力の外にルールを増やすだけなのでflat requiredを採った。
- **providerをrequest bodyから完全に排除し、adapter 1インスタンス = 1 providerに固定する**: per-runのlive明示確認をper-processへ格下げし、workbenchのprovider selectと確認チェックボックスを殺す。採らなかった。
- **session tokenをTTLではなく発行回数で制限する**: tokenは起動時に1度だけ標準出力へ出す設計であり、回数上限は「あと何回使えるか」がoperatorにもUIにも見えない。時間で切る方が、operatorがadapterを起動しっぱなしにしたときの露出窓を直接縮める。
- **`scenario_path`と`scenario_sha256`をcatalogのauthored fieldにする**: authored fieldが増えるほど`catalog_version` bumpの契機が増える。globによる一意性不変の方が「別scenarioが同じidを名乗る」事故を捕まえられるため、抽出した`_resolve_scenario_path`の再利用に留めた。

## Next Actions

1. `fixtures/participation/public-tools-template-confirmation.v1.json`の`template_version`を3へ更新する。
2. adapterのrun回数上限・費用上限を検討する。起動時grantは「使える/使えない」の2値であって、回数・費用の上限ではない。
3. response schemaへ`template_id`、`catalog_version`、request digestを載せてprovenanceを閉じる。
4. `pr_contract.py`のslugからのpath導出と、catalogのpath保持の関係を整理する。mergeされたworldline PRのsocial configとfixtureをcatalogへ自動登録する経路は作らない。
5. `.github/workflows/`のpublic transport側にも、participationとcatalogを検証するstepを足す。

## 見直し条件

- CLIの`social`サブコマンドが遅延引数を持ち、local transportが`none`以外のdelay profileを実行できるようになったとき
- catalogのtemplate数が増え、health projectionのサイズ上限やpaginationが必要になったとき
- scenarioを編集しても同じ`template_version`のまま結果が変わりうる、という残課題が実害として観測されたとき
- workbenchへIdeaDraft → template confirmation → `ProvisionalRunRequest`の対話経路（prepare-preview）が実装され、`user_confirmed`の根拠がボタン押下より強くなったとき
- session tokenのTTLがoperatorの実作業時間より短く、再起動が常態化したとき
