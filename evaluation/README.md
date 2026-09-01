# evaluation

Grok担当範囲。runtime physics（`src/fiction_forks/`）と既存worldlineは変更しない。

正本境界は [`PROJECT_SSOT.md`](../PROJECT_SSOT.md) の「観測指標評価」行、指標が何を測り何を主張しないかは [ADR 0014](../docs/adr/0014-emergence-metrics-are-observational-not-evidence.md)、実測値の正本は [`RESULTS.md`](../RESULTS.md) にある。ここの出力は再生成可能な派生物であり、公式結果でも創発の証拠でもない。

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

## curated境界

curated rootは `artifacts/runs`（`CURATED_ROOT_RELATIVE`）に固定する。人間レビューを通ったcurated runだけがここに置かれる。`--input` はcurated rootの外も受け付けるが、その場合の混入を目視ではなく機械で判別できるようにする。

- 各行が `curated` booleanを持つ。curated root配下と確認できたartifactだけが `true` で、判定不能は `false` へ倒す。
- レポートは `input_curation`（`curated_root` / `curated_only`）を刻む。`curated_only` が `false` のレポートは、公式結果としても実測結果としても引用しない。
- `evaluation/worldline-issue12/` は未検証のworldline候補である。既定入力に含めない。入力へ足した場合は `curated_only` が `false` になる。
