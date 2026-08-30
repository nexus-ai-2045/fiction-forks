# evaluation

Grok担当範囲。runtime physics（`src/fiction_forks/`）と既存worldlineは変更しない。

| パス | 内容 |
|---|---|
| `emergence_metrics.py` | 複数artifactの観測指標集計。創発性は断定しない |
| `outputs/` | 既存artifactから生成したJSON/Markdown |
| `worldline-issue12/` | Issue #12の未検証worldline候補 |
| `pitch-90s.md` | 90秒デモ脚本。Vertex敗北が主証拠 |

```powershell
python evaluation/emergence_metrics.py `
  --repo-root . `
  --input artifacts/runs `
  --output-json evaluation/outputs/emergence-metrics.json `
  --output-md evaluation/outputs/emergence-metrics.md
```

入力不足は0で補完せず `not_measured` にする。raw model textは集計へ入れない。同じ `run_id` でも provider / model / runtime_revision / result SHA / event SHA が違えば別実行として数える。
