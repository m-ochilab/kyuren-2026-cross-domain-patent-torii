# Manual Review Generation Log

## 使用した入力ファイル

- specific_methods: `pipeline/data/processed_full/ranking/method_gap_ranking_specific_methods_full.csv` / rows=12 / columns=specific_rank, method, method_display, A_pre_count, A_pre_total, A_pre_rate, B_pre_count, B_pre_total, B_pre_rate, gap_rate, positive_gap, problem_field_similarity, gap_score_old, gap_score_v2, rank
- with_future: `pipeline/data/processed_full/ranking/method_gap_ranking_with_future_full.csv` / rows=23 / columns=method, method_display, A_pre_rate, B_pre_rate, gap_rate, positive_gap, gap_score_old, gap_score_v2, B_future_rate, B_growth_rate, future_observed_flag, rank
- all_methods: `pipeline/data/processed_full/ranking/method_gap_ranking_all_full.csv` / rows=23 / columns=rank, method, method_display, A_pre_count, A_pre_total, A_pre_rate, B_pre_count, B_pre_total, B_pre_rate, gap_rate, positive_gap, problem_field_similarity, gap_score_old, gap_score_v2
- future_growth: `pipeline/data/processed_full/ranking/method_future_growth_evaluation_full.csv` / rows=49 / columns=method, B_future_count, B_future_total, B_future_rate, B_growth_rate
- unet_check: `pipeline/data/processed_full/ranking/unet_ranking_check_full.csv` / rows=1 / columns=method, method_display, A_pre_rate, B_pre_rate, gap_rate, positive_gap, gap_score_old, gap_score_v2, B_future_rate, B_growth_rate, future_observed_flag, rank, A_pre_count, B_pre_count, problem_field_similarity
- problem_topk: `pipeline/data/processed_full/similarity/A0_to_B0_problem_topk_full.csv` / rows=518700 / columns=a_rank_source_idx, neighbor_rank, a_publication_number, b_publication_number, similarity, a_family_id, b_family_id, a_year, b_year, a_application_field, b_application_field, a_technical_means, b_technical_means, a_is_unet_final, b_is_unet_final
- solution_topk: `pipeline/data/processed_full/similarity/A0_to_B0_solution_topk_full.csv` / rows=518700 / columns=a_rank_source_idx, neighbor_rank, a_publication_number, b_publication_number, similarity, a_family_id, b_family_id, a_year, b_year, a_application_field, b_application_field, a_technical_means, b_technical_means, a_is_unet_final, b_is_unet_final
- fulltext_topk: `pipeline/data/processed_full/similarity/A0_to_B0_fulltext_topk_full.csv` / rows=518700 / columns=a_rank_source_idx, neighbor_rank, a_publication_number, b_publication_number, similarity, a_family_id, b_family_id, a_year, b_year, a_application_field, b_application_field, a_technical_means, b_technical_means, a_is_unet_final, b_is_unet_final
- field_summary: `pipeline/data/processed_full/similarity/field_level_similarity_summary_full.csv` / rows=1 / columns=problem_field_similarity, problem_A_count, problem_B_count, solution_field_similarity, solution_A_count, solution_B_count, fulltext_field_similarity, fulltext_A_count, fulltext_B_count
- b_contexts: `pipeline/data/processed_full/B0_contexts.csv` / rows=44364 / columns=publication_number, family_id, year, is_unet_raw, title, abstract, claims, full_text, title_abstract_text, is_unet_title_abstract, is_unet_claims, is_unet_full_text, is_unet_final, is_unet, has_text, domain, is_yolo, is_gan, is_cyclegan, is_transformer...
- manual_review_blind_xlsx: `pipeline/outputs/manual_review_evaluation/manual_review_blind.xlsx` / rows=53 / columns=review_id, publication_number, family_id, title, abstract, claims, problem_context, solution_context, technical_means, target_object, effect_context, application_field, method_name, candidate_type, general_term_flag, specific_method_flag, problem_extraction_score, solution_extraction_score, technical_means_score, target_object_score...

## 列名対応

- `publication_number`, `family_id`, `title`, `abstract`, `claims` は `B0_contexts.csv` の同名列を使用。
- `problem_context`, `solution_context`, `technical_means`, `target_object`, `effect_context`, `application_field` は `B0_contexts.csv` の抽出済み列を使用。
- `method_name` はランキング表の `method_display` を優先し、欠損時は `method` または `b_technical_means` を使用。
- `rank`, `score`, `gap_score`, `similarity_score`, `method_source`, `proposed_or_baseline`, `future_count`, `future_rate` は `manual_review_key.csv` にのみ保存。

## 候補抽出条件

- A. 提案手法ランキング上位候補: `method_gap_ranking_with_future_full.csv` の `rank` 上位23手法から、B0側の代表特許を `A0_to_B0_problem_topk_full.csv`、`A0_to_B0_solution_topk_full.csv`、`B0_contexts.csv` で探索。
- B. U-Net関連候補: `unet_ranking_check_full.csv` と `specific_methods` の U-Net 行を根拠に、B0側で U-Net フラグまたは技術手段に該当する特許を抽出。
- C. 低順位・ランダム候補: `A0_to_B0_fulltext_topk_full.csv` の `neighbor_rank >= 8` から、本文情報があるB0候補を固定乱数seed=42で抽出。
- D. 将来比較用候補: `method_future_growth_evaluation_full.csv` の `B_growth_rate`, `B_future_count` が大きい手法から、2019年以降のB0代表特許をproblem/solution top-kとcontextで抽出。
- 重複する `publication_number` は評価対象内で1件に統合。
- 評価用blindファイルにはランキング・スコア・手法ソースを入れず、keyファイルに分離。

## 作成件数

- `manual_review_blind.csv`: 53 rows
- `manual_review_key.csv`: 53 rows
- proposed_top: 23 rows
- unet_related: 10 rows
- random_low_rank: 10 rows
- future_growth: 10 rows

## 欠損列・欠損値への対応

- 必須出力列は全て作成。元データ側の欠損値は空欄として保持。

## 注意点

- このファイル群は人手評価の材料整理であり、候補の良否をCodexが最終判定したものではありません。
- `general_term_flag` と `specific_method_flag` は候補整理用の機械的フラグです。最終評価では本文・請求項・抽出文脈を読んで判断してください。
- `manual_review_blind.csv` には評価バイアスになりやすいrank/score/source系の列を含めていません。
- 集計時は評価記入後に `aggregate_manual_review.py` を同じディレクトリで実行してください。

## 次に人間がやるべきこと

1. `manual_review_blind.csv` またはExcel版を開き、rubricに沿って空欄の評価列を記入する。
2. 記入後、`python3 aggregate_manual_review.py` を実行して `manual_review_summary.csv` と `manual_review_summary.md` を作成する。
3. 必要に応じて `manual_review_key.csv` と結合し、rank/score/source別の追加分析を行う。