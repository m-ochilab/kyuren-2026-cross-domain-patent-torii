# 卒論 LaTeX セット（初版）

## 方針
このLaTeXセットは、指導教員トレースAgentの評価基準に沿って、以下の方針で再構成した卒論ドラフトです。

- U-Netを主ケースとする。
- 花王・半導体洗浄ケースは補助ケースとして付録に置く。
- 各章タイトル直後に「章の概要」を入れる。
- 研究目的を1つに絞る。
- RQ1〜RQ3と実験・結果・考察を対応させる。
- 「導入可能性を証明」ではなく「専門家確認候補の抽出」と表現する。
- 図1、課題・解決手段分離図、評価設計図、U-Net年次推移図、データセット表を入れる。

## ファイル構成

```text
sotsuron_latex_set/
  main.tex
  references.bib
  latexmkrc
  build.sh
  chapters/
    00_abstract.tex
    01_introduction.tex
    02_related_work.tex
    03_framework.tex
    04_data_experiment.tex
    05_results.tex
    06_discussion.tex
    07_conclusion.tex
    A_supplementary_case_kao.tex
    B_llm_prompt.tex
  figures/
    fig01_framework.png
    fig02_problem_solution_split.png
    fig03_evaluation_design.png
    fig04_unet_publication_rate.png
    fig05_unet_period_publication.png
    fig06_unet_period_family.png
    fig07_dataset_overview.png
    make_figures.py
```

## ビルド方法
LuaLaTeX + biber を想定しています。

```bash
cd sotsuron_latex_set
bash build.sh
```

または、latexmk を使う場合：

```bash
latexmk main.tex
```

## 分析パイプライン

Orbis IPの元データは `source_data/` に保管し、パイプラインの正式入力は再構築済みCSVを使います。

```text
pipeline/data/raw/
  A0_orbis_publication_level.csv
  B0_orbis_publication_level.csv
  A1_orbis_publication_level.csv
  B1_orbis_publication_level.csv
```

A0/B0を主分析に用い、A1/B1はU-Net代表特許の確認用データとして保持します。処理は `pipeline/` 配下で実行します。

```bash
cd pipeline
../.venv/bin/python src/00_check_columns.py --config config/config.yaml
../.venv/bin/python src/01_preprocess_patents.py --config config/config.yaml
../.venv/bin/python src/02_extract_method_terms.py --config config/config.yaml
../.venv/bin/python src/03_extract_problem_solution_contexts.py --config config/config.yaml --mode heuristic
```

卒論手法に合わせ、03ではTitle，Abstract，Claimsから `problem_context` と `solution_context` を分けます。LLM抽出を行う場合は、まず次のコマンドでJSONLリクエストを作成します。

```bash
cd pipeline
../.venv/bin/python src/03_extract_problem_solution_contexts.py --config config/config.yaml --mode prepare_llm
```

LLM結果を `pipeline/outputs/llm_results/` に置いた後、次のコマンドで結果を統合します。

```bash
cd pipeline
../.venv/bin/python src/03_extract_problem_solution_contexts.py --config config/config.yaml --mode merge_llm
```

サンプル実行は `SAMPLE_N=1000 bash run_all.sh` のように指定できます。`CONTEXT_MODE=prepare_llm` を指定するとLLMリクエストのみを作成します。

### U-Net判定列

U-Net判定は、判定に使ったテキスト範囲を明確にするため、以下の列に分けています。

```text
is_unet_title_abstract  Title / Abstract にU-Net表記がある場合に1
is_unet_claims          Claims にU-Net表記がある場合に1
is_unet_full_text       Title / Abstract / Claims のどこかにU-Net表記がある場合に1
is_unet_final           分析に使う最終判定
is_unet                 既存処理との互換用。is_unet_final と同じ値
```

`is_unet_final` に使う範囲は `pipeline/config/config.yaml` の `methods.unet_final_source` で指定します。現在の既定値は、卒論本文の主集計に合わせて `title_abstract` です。Family単位では、family内のいずれか1 publicationが該当すれば1として集約します。

### 文脈抽出の品質確認列

`A0_contexts.csv` / `B0_contexts.csv` には、課題・解決手段分離の結果に加えて次の列を出力します。

```text
technical_means      解決手段側から抽出した技術手段。明示的手法名がない場合も装置構成・処理方法などを抽出
application_field    医療画像解析、製造欠陥検出、半導体・基板処理などの推定用途分野
domain_noise_flag    検索集合の主分野から外れる可能性がある場合に1
domain_noise_reason  ノイズ候補と判定した理由
analysis_include     ノイズ候補でなければ1
```

本番結果に使う前に、`technical_means` の代表サンプルと `domain_noise_flag=1` の行を人手で確認します。

### ベクトル化・類似度・手法ギャップランキング

卒論の主実験では、抽出済みの `problem_context`、`solution_context`、`full_text` を別々にベクトル化し、A0/B0間の文脈類似度と `technical_means` の出現差分から専門家確認候補をランキング化します。

```bash
cd pipeline
../.venv/bin/python src/10_vectorize_contexts.py \
  --input-dir data/processed \
  --output-dir data/processed/embeddings \
  --model sentence-transformers/all-MiniLM-L6-v2 \
  --batch-size 32

../.venv/bin/python src/11_compute_similarity.py \
  --embedding-dir data/processed/embeddings \
  --output-dir data/processed/similarity \
  --top-k 10

../.venv/bin/python src/12_rank_method_gaps.py \
  --input-dir data/processed \
  --similarity-dir data/processed/similarity \
  --output-dir data/processed/ranking

../.venv/bin/python src/13_make_vector_ranking_report.py \
  --input-dir data/processed \
  --output-dir data/processed/reports
```

出力は以下に保存します。

```text
data/processed/embeddings/
data/processed/similarity/
data/processed/ranking/
data/processed/reports/
```

`12_rank_method_gaps.py` のGapScoreは以下です。

```text
GapScore(m) = Rate_A_pre(m) * (1 - Rate_B_pre(m)) * ProblemSimilarity(A, B)
```

ここで過去期間は既定で2015--2018年、将来評価期間は2019--2024年です。`--include-noise` を指定しない限り、`analysis_include == 1` の行だけを主分析に使います。U-Netについては `data/processed/ranking/unet_ranking_check.csv` に順位、出現率、GapScore、将来出現を出力します。

一括実行でベクトル化以降も含める場合は次を使います。

```bash
cd pipeline
bash run_all.sh --with-embeddings
```

## 注意点
- `references.bib` の一部文献は、タイトルベースの仮エントリです。最終提出前に、著者名・ジャーナル名・巻号・ページ・DOIを必ず確認してください。
- 図は現時点のサンプルです。最終分析結果が更新された場合は、`figures/make_figures.py` の数値を差し替えて再生成してください。
- 本ドラフトは、U-Net主分析に寄せた構成です。花王ケースを本文主分析にする場合は、章構成を変更する必要があります。
