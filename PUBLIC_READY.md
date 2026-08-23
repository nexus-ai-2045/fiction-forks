<!-- repo-preflight:review-record -->

# 公開準備記録

## 公開対象

- Fiction Forksの説明文書
- 透明な状態遷移ルールを持つPython MVP
- オリジナルの日本2036シナリオ
- 作品名と抽象化した機能だけを使う介入例
- テスト、CI、コントリビューション規約

## 公開対象外

- Discordその他の非公開会話本文と参加者情報
- ローカル絶対パス、個人名、credential、内部URL
- 公式画像、漫画コマ、映像、音声、音楽、ロゴ、原作台詞
- 実在システムの脆弱性、標的、攻撃手順
- 公開を政策助言や未来予測として保証する表現

## ローカル確認

- [ ] READMEを人間が目視確認した
- [ ] LICENSE、SECURITY.md、CONTRIBUTING.mdを確認した
- [x] secret scanがpassした
- [x] personal-path scanがpassした
- [x] ai-ratchet-gateがpassした
- [x] unittestと比較smokeがpassした
- [x] Git authorが `nexus_ai` 名義だけである
- [ ] 第三者IPの複製物が含まれない
- [x] THIRD_PARTY_NOTICES.mdのURLと版を確認した
- [x] 公式根拠が公式サイトと片山俊大氏 v1.0ペーパーの2点だけである

## GitHub側の確認

- [x] visibilityをread-backした（PRIVATE）
- [x] default branchをread-backした（`main`）
- [ ] CIが公開予定のexact HEADでpassした
- [ ] Private vulnerability reportingの状態を確認した
- [ ] 公開前の人間レビューと明示承認を記録した

自動検査のpassは公開承認ではありません。公開時には、ファイルとコミット履歴がWebから閲覧可能になることを再確認します。
