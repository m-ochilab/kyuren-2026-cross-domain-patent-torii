# Human Review Aggregation Log

## 入力

- `/Users/h-torii4649/Downloads/manual_review_with_human_filled.xlsx`
- sheet: `manual_review_with_llm`

## 出力

- `pipeline/outputs/manual_review_evaluation/human_review_filled_normalized.csv`
- `pipeline/outputs/manual_review_evaluation/human_review_filled_normalized.xlsx`
- `pipeline/outputs/manual_review_evaluation/human_review_summary.csv`
- `pipeline/outputs/manual_review_evaluation/human_review_summary.md`
- `pipeline/outputs/manual_review_evaluation/human_vs_llm_review_comparison.csv`
- `pipeline/outputs/manual_review_evaluation/human_vs_llm_review_comparison.md`

## 集計条件

- `human_` 列を人間による最終評価として集計しました。
- 元Excelファイルは変更していません。
- `rank`, `score`, `gap_score`, `similarity_score`, `method_source`, `proposed_or_baseline` は人間評価ファイルには含まれていません。
- Precision@k相当は、評価ファイルの行順に対して `human_candidate_score >= 2` を妥当候補として算出しました。

## 確認

- 集計日時: 2026-06-11 06:45:32
- 行数: 53
- human_candidate_score 記入件数: 53
- human_final_label 記入件数: 53