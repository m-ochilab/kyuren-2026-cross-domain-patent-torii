# Baseline Generation Log

## 使用した入力ファイル

- human_filled: `/Users/h-torii4649/Downloads/manual_review_with_human_filled.xlsx` / exists / rows=53 / columns=review_id, publication_number, family_id, title, abstract, claims, problem_context, solution_context, technical_means, target_object, effect_context, application_field, method_name, candidate_type, general_term_flag, specific_method_flag, problem_extraction_score, solution_extraction_score, technical_means_score, target_object_score...
- manual_review_key: `pipeline/outputs/manual_review_evaluation/manual_review_key.csv` / exists / rows=53 / columns=review_id, publication_number, family_id, candidate_type, method_name, source_file, source_row_index, method_source, proposed_or_baseline, rank, score, gap_score, similarity_score, future_count, future_rate, general_term_flag, specific_method_flag, a_publication_number, a_family_id, a_year...
- manual_review_rubric: `pipeline/outputs/manual_review_evaluation/manual_review_rubric.md` / exists / rows=None / columns=
- manual_review_generation_log: `pipeline/outputs/manual_review_evaluation/manual_review_generation_log.md` / exists / rows=None / columns=
- b0_contexts: `pipeline/data/processed_full/B0_contexts.csv` / exists / rows=44364 / columns=publication_number, family_id, year, is_unet_raw, title, abstract, claims, full_text, title_abstract_text, is_unet_title_abstract, is_unet_claims, is_unet_full_text, is_unet_final, is_unet, has_text, domain, is_yolo, is_gan, is_cyclegan, is_transformer...
- a0_contexts: `pipeline/data/processed_full/A0_contexts.csv` / exists / rows=54100 / columns=publication_number, family_id, year, is_unet_raw, title, abstract, claims, full_text, title_abstract_text, is_unet_title_abstract, is_unet_claims, is_unet_full_text, is_unet_final, is_unet, has_text, domain, is_yolo, is_gan, is_cyclegan, is_transformer...
- fulltext_topk: `pipeline/data/processed_full/similarity/A0_to_B0_fulltext_topk_full.csv` / exists / rows=518700 / columns=a_rank_source_idx, neighbor_rank, a_publication_number, b_publication_number, similarity, a_family_id, b_family_id, a_year, b_year, a_application_field, b_application_field, a_technical_means, b_technical_means, a_is_unet_final, b_is_unet_final
- problem_topk: `pipeline/data/processed_full/similarity/A0_to_B0_problem_topk_full.csv` / exists / rows=518700 / columns=a_rank_source_idx, neighbor_rank, a_publication_number, b_publication_number, similarity, a_family_id, b_family_id, a_year, b_year, a_application_field, b_application_field, a_technical_means, b_technical_means, a_is_unet_final, b_is_unet_final
- solution_topk: `pipeline/data/processed_full/similarity/A0_to_B0_solution_topk_full.csv` / exists / rows=518700 / columns=a_rank_source_idx, neighbor_rank, a_publication_number, b_publication_number, similarity, a_family_id, b_family_id, a_year, b_year, a_application_field, b_application_field, a_technical_means, b_technical_means, a_is_unet_final, b_is_unet_final
- method_gap_all: `pipeline/data/processed_full/ranking/method_gap_ranking_all_full.csv` / exists / rows=23 / columns=rank, method, method_display, A_pre_count, A_pre_total, A_pre_rate, B_pre_count, B_pre_total, B_pre_rate, gap_rate, positive_gap, problem_field_similarity, gap_score_old, gap_score_v2
- method_gap_specific: `pipeline/data/processed_full/ranking/method_gap_ranking_specific_methods_full.csv` / exists / rows=12 / columns=specific_rank, method, method_display, A_pre_count, A_pre_total, A_pre_rate, B_pre_count, B_pre_total, B_pre_rate, gap_rate, positive_gap, problem_field_similarity, gap_score_old, gap_score_v2, rank
- method_gap_future: `pipeline/data/processed_full/ranking/method_gap_ranking_with_future_full.csv` / exists / rows=23 / columns=method, method_display, A_pre_rate, B_pre_rate, gap_rate, positive_gap, gap_score_old, gap_score_v2, B_future_rate, B_growth_rate, future_observed_flag, rank
- method_future_growth: `pipeline/data/processed_full/ranking/method_future_growth_evaluation_full.csv` / exists / rows=49 / columns=method, B_future_count, B_future_total, B_future_rate, B_growth_rate
- unet_check: `pipeline/data/processed_full/ranking/unet_ranking_check_full.csv` / exists / rows=1 / columns=method, method_display, A_pre_rate, B_pre_rate, gap_rate, positive_gap, gap_score_old, gap_score_v2, B_future_rate, B_growth_rate, future_observed_flag, rank, A_pre_count, B_pre_count, problem_field_similarity

## 既存評価ファイル

- 行数: 53
- `random_low_rank` から `fulltext_low_rank_baseline` への置換件数: 10
- 元の candidate_type は `candidate_type_original` として `existing_human_review_normalized.csv` に保持。

## 追加ベースライン抽出条件と件数

- true_random_baseline: B0_contextsから本文情報あり、既存候補と非重複、seed=42で抽出 / 件数=30
- fulltext_top_baseline: A0_to_B0_fulltext_topk_fullのneighbor_rank昇順・similarity降順、既存候補と非重複 / 件数=30
- frequency_top_baseline: B0 technical_means頻度上位から代表特許を抽出、既存候補と非重複 / 件数=30

## 重複除外・候補除外

- true_random_baseline: 除外または未採用候補の概数=44281
- fulltext_top_baseline: 除外または未採用候補の概数=518670
- frequency_top_baseline: 除外または未採用候補の概数=26

## 欠損列への対応

- B0_contexts側で欠損している文脈列は空欄として保持。
- has_text列がある場合は has_text=True を優先し、titleまたはabstractが空でない候補に限定。
- human_評価列は追加評価前の空欄として作成。

## 作成した出力ファイル

- `pipeline/outputs/manual_review_evaluation/existing_human_review_normalized.csv`
- `pipeline/outputs/manual_review_evaluation/baseline_review_blind.csv`
- `pipeline/outputs/manual_review_evaluation/baseline_review_blind.xlsx`
- `pipeline/outputs/manual_review_evaluation/baseline_review_key.csv`
- `pipeline/outputs/manual_review_evaluation/baseline_review_with_llm_suggestions.csv`
- `pipeline/outputs/manual_review_evaluation/baseline_review_with_llm_suggestions.xlsx`
- `pipeline/outputs/manual_review_evaluation/baseline_comparison_design_note.md`
- `pipeline/outputs/manual_review_evaluation/baseline_generation_log.md`
- `pipeline/outputs/manual_review_evaluation/aggregate_final_human_review.py`

## 確認

- 追加評価対象件数: 90
- candidate_type別件数: {'true_random_baseline': 30, 'fulltext_top_baseline': 30, 'frequency_top_baseline': 30}
- 追加評価用blindファイルへのrank/score/similarity/source列混入: []

## 次に人間がやるべきこと

1. `baseline_review_blind.xlsx` または `baseline_review_with_llm_suggestions.xlsx` を開き、human_列に評価を記入する。
2. 評価済みファイルを `baseline_review_with_human_filled.xlsx` として保存する。
3. `aggregate_final_human_review.py` を実行し、既存評価と追加ベースライン評価を結合集計する。