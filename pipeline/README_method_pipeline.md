# 研究手法パイプライン

## 卒業論文「特許文書の課題・解決手段分離に基づくクロスドメイン技術候補抽出」

---

## 1. 研究目的

本パイプラインは、以下の研究目的を実現するために設計されている：

1. **技術候補のスクリーニング**：ドメインA（医療画像解析）で広く使われている技術手法が、類似した課題構造を持つドメインB（製造欠陥検出）における技術候補として浮上しうるかを定量的に評価する。

2. **説明可能性**：GapScoreの各構成要素（課題類似度・出現率差・頻度重み・低出現ボーナス）がランキング結果の解釈を可能にする。

3. **後ろ向き評価**：過去期間（2015-2018年）の情報のみでランキングを生成し、将来期間（2019-2024年）の実際の技術動向と照合することで、手法の候補抽出精度を確認する。

---

## 2. データセット定義

| 記号 | 分野 | 役割 |
|---|---|---|
| A0 | 医療画像解析（Medical Image Analysis） | 参照元ドメイン |
| B0 | 製造欠陥検出（Manufacturing Defect Detection） | 候補探索先ドメイン |

---

## 3. セットアップ

### 3.1 動作環境

- Python 3.9以上
- macOS / Linux 推奨

### 3.2 インストール

```bash
# パイプラインディレクトリへ移動
cd /path/to/sotsuron_latex_set/pipeline

# 仮想環境の作成（推奨）
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate   # Windows

# 依存パッケージのインストール
pip install -r requirements.txt
```

### 3.3 設定ファイルの確認

`config/config.yaml` を開いて、データファイルのパスが正しいことを確認する：

```yaml
data:
  a0_csv: "../../A0_data.csv"   # A0_data.csv へのパス
  b0_csv: "../../B0_data.csv"   # B0_data.csv へのパス
```

---

## 4. 実行方法

### 4.1 一括実行

```bash
chmod +x run_all.sh
./run_all.sh
```

ログは `outputs/logs/run_all_YYYYMMDD_HHMMSS.log` に保存される。

### 4.2 個別実行

各スクリプトはそれぞれ独立して実行できる。すべてのスクリプトで `--config` オプションが必須。

```bash
# 列構造の確認（最初に実行推奨）
python src/00_check_columns.py --config config/config.yaml

# データ前処理
python src/01_preprocess_patents.py --config config/config.yaml

# 技術手法語の抽出
python src/02_extract_method_terms.py --config config/config.yaml

# 課題・解決手段文脈の抽出
python src/03_extract_problem_solution_contexts.py --config config/config.yaml

# 埋め込み計算（PatentSBERTa、時間がかかる）
python src/04_embed_patents.py --config config/config.yaml --domain both --type all

# ドメイン間類似度の計算
python src/05_compute_domain_similarity.py --config config/config.yaml

# Method Gapの計算
python src/06_compute_method_gap.py --config config/config.yaml

# GapScoreランキング
python src/07_rank_candidates.py --config config/config.yaml

# 後ろ向き評価
python src/08_temporal_evaluation.py --config config/config.yaml

# ベースライン比較
python src/09_baseline_comparison.py --config config/config.yaml

# 論文用図表の生成
python src/10_export_for_thesis.py --config config/config.yaml
```

### 4.3 サンプル実行（動作確認用）

```bash
# 最初の100件のみで動作確認
python src/01_preprocess_patents.py --config config/config.yaml --sample 100
python src/02_extract_method_terms.py --config config/config.yaml --sample 100
```

---

## 5. 出力ファイル一覧

### 5.1 中間データ（`data/processed/`）

| ファイル名 | 内容 |
|---|---|
| A0_publication_level.csv | A0 Publication レベルの前処理済みデータ |
| B0_publication_level.csv | B0 Publication レベルの前処理済みデータ |
| A0_family_level.csv | A0 Family レベルのグループ化データ |
| B0_family_level.csv | B0 Family レベルのグループ化データ |
| A0_with_methods.csv | 手法フラグ付きA0データ |
| B0_with_methods.csv | 手法フラグ付きB0データ |
| A0_contexts.csv | 課題・解決手段文脈付きA0データ |
| B0_contexts.csv | 課題・解決手段文脈付きB0データ |

### 5.2 埋め込みデータ（`outputs/embeddings/`）

| ファイル名 | 内容 |
|---|---|
| A0_full_embeddings.npy | A0全文埋め込みベクトル |
| A0_problem_embeddings.npy | A0課題文脈埋め込みベクトル |
| A0_solution_embeddings.npy | A0解決手段文脈埋め込みベクトル |
| B0_*.npy | B0の各埋め込みベクトル |
| A0_metadata.csv | A0埋め込みに対応するメタデータ |
| B0_metadata.csv | B0埋め込みに対応するメタデータ |

### 5.3 分析結果テーブル（`outputs/tables/`）

| ファイル名 | 内容 |
|---|---|
| dataset_summary.csv | データセット統計サマリー |
| method_counts_by_domain.csv | ドメイン別手法出現件数 |
| method_counts_by_year.csv | 年別手法出現件数 |
| method_gap_by_period_publication.csv | 期間別Method Gap（Publication）|
| method_gap_by_period_family.csv | 期間別Method Gap（Family）|
| domain_similarity_summary.csv | ドメイン間コサイン類似度 |
| temporal_evaluation_summary.csv | 後ろ向き評価サマリー |
| future_growth_by_method.csv | 手法別B0将来期間成長率 |
| baseline_comparison.csv | ベースライン比較結果 |
| table_method_gap.tex | LaTeXテーブル |
| table_temporal_evaluation.tex | LaTeXテーブル |
| table_baseline_comparison.tex | LaTeXテーブル |
| table_domain_similarity.tex | LaTeXテーブル |

### 5.4 ランキング（`outputs/rankings/`）

| ファイル名 | 内容 |
|---|---|
| method_gap_ranking_past.csv | 過去期間GapScoreランキング |
| method_gap_ranking_all.csv | 全期間GapScoreランキング |

### 5.5 図（`outputs/figures/`）

| ファイル名 | 内容 |
|---|---|
| dataset_overview.png | データセット概要棒グラフ |
| unet_annual_rate_publication.png | U-Net年次出現率折れ線グラフ |
| unet_period_comparison_publication.png | 期間別U-Net出現率（Publication）|
| unet_period_comparison_family.png | 期間別U-Net出現率（Family）|
| method_gap_ranking.png | GapScoreランキング棒グラフ |
| domain_similarity_heatmap.png | ドメイン類似度ヒートマップ |
| baseline_comparison.png | ベースライン比較グラフ |

---

## 6. 注意事項

- **本パイプラインは「専門家が確認すべき候補を抽出する」ためのスクリーニング手法を実装したものである。**
- GapScoreが高い手法がクロスドメイン技術候補として浮上することを確認する目的で設計されており、候補抽出の可能性を示すものである。
- 出力結果は専門家によるレビューと組み合わせて解釈することが前提となる。
- 埋め込み計算（04番スクリプト）は PatentSBERTa モデルのダウンロードを伴うため、初回実行時にネットワーク接続が必要。モデルサイズは約400MBある。
- テキスト列がないデータ（is_unet フラグのみのCSV）でも、02番以降のスクリプトはテキストなしモードで動作し、頻度ベースの分析を実行する。

---

## 7. ライセンス・引用

本パイプラインは卒業論文研究用のものである。
PatentSBERTa の利用にあたっては元論文のライセンスに従うこと。

```
AI-Growth-Lab/PatentSBERTa
https://huggingface.co/AI-Growth-Lab/PatentSBERTa
```
