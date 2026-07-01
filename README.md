# Cross-Domain Patent Technology Candidate Screening

卒業論文「特許文書の課題・解決手段分離に基づくクロスドメイン技術候補抽出」の研究レポジトリです。

本研究では、特許文書を `problem_context` と `solution_context` に分離し、課題が近い異分野間で専門家が確認すべき技術手法・解決手段候補を抽出するスクリーニング手法を検討します。

## Repository Layout

```text
.
├── README.md
├── requirements.txt
├── package.json
├── package-lock.json
├── pipeline/                  # 分析パイプライン
│   ├── config/
│   ├── data/raw/              # GitHub用の小型サンプルCSV
│   ├── prompts/
│   ├── scripts/
│   ├── src/
│   └── run_all.sh
├── thesis/                    # 卒論LaTeX本体
├── research_plan_latex/       # 卒論研究計画書用LaTeX
├── results/                   # 論文に採用した図表・評価結果・レポート
├── docs/                      # データ索引、検証ログなど
├── scripts/                   # 補助スクリプト
└── data_external/             # フルデータ置き場。Git管理対象外
```

## GitHub Policy

このフォルダは GitHub へ上げることを想定して整理しています。

- `pipeline/data/raw/` には動作確認用のサンプルCSVのみを入れています。
- フルのOrbis IP由来データ、巨大な中間生成物、埋め込み、キャッシュは `data_external/` に置き、`.gitignore` で Git 管理から除外しています。
- `.venv/` と `node_modules/` は含めません。依存関係は `requirements.txt` と `package-lock.json` から復元します。
- Orbis IP など外部データの公開可否はライセンス・利用規約を確認してください。公開できない場合は、`data_external/` をローカル保管または別ストレージ保管にしてください。

## Setup

Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Node.js tools:

```bash
npm ci
```

## Smoke Test

サンプルデータで、構文確認、パイプラインの軽量実行、卒論LaTeXビルドを確認します。

```bash
bash scripts/smoke_test.sh
```

パイプラインのみ確認する場合:

```bash
cd pipeline
SAMPLE_N=20 bash run_all.sh
```

卒論LaTeXのみ確認する場合:

```bash
cd thesis
tectonic main.tex
```

## Full Data

フルデータは次のように置く想定です。

```text
data_external/source_data/
data_external/pipeline_raw_full/
```

`pipeline/config/config.yaml` はサンプルCSVを参照するため、そのまま GitHub 上で軽量実行できます。フルデータで再実行する場合は、`data_external/` のファイルを `pipeline/data/raw/` にコピーするか、設定ファイルのパスをフルデータ側へ変更してください。

## Build Notes

- メイン卒論は `thesis/main.tex` を `tectonic` でビルド確認済みです。
- `research_plan_latex/` は `ltjsreport` / `luatexja` を使うテンプレートです。現在の環境には LuaLaTeX/latexmk がないため、TeX Live 環境で `lualatex` またはテンプレートに合う `latexmk` 設定を使ってビルドしてください。

## License

研究コード・論文草稿の公開範囲、外部データの再配布可否、図表の扱いは、提出先・共同研究・データ提供元の条件に従って決めてください。
