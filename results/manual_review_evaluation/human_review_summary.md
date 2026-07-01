# Human Review Summary

人手評価済みの `human_` 列を最終評価として集計した結果です。`human_candidate_score` を `candidate_score`、`human_final_label` を `final_label` として扱っています。

## Overall

| section | metric | value | count |
| --- | --- | --- | --- |
| overall | count | 53.0 | 53 |
| overall | candidate_score_mean | 1.6603773584905661 | 53 |
| overall | candidate_score_median | 2.0 | 53 |
| overall | valid_candidate_rate_score_ge_2 | 0.5283018867924528 | 53 |
| overall | representative_flag_1_count | 22.0 | 53 |
| final_label_count | △ | 17.0 | 17 |
| final_label_count | ◎ | 15.0 | 15 |
| final_label_count | ○ | 13.0 | 13 |
| final_label_count | × | 8.0 | 8 |
| candidate_score_count | 0 | 8.0 | 8 |
| candidate_score_count | 1 | 17.0 | 17 |
| candidate_score_count | 2 | 13.0 | 13 |
| candidate_score_count | 3 | 15.0 | 15 |
| method_flag_comparison | specific_method_flag_count | 29.0 | 29 |
| method_flag_comparison | specific_method_flag_candidate_score_mean | 1.8275862068965518 | 29 |
| method_flag_comparison | specific_method_flag_valid_rate_score_ge_2 | 0.5517241379310345 | 29 |
| method_flag_comparison | general_term_flag_count | 48.0 | 48 |
| method_flag_comparison | general_term_flag_candidate_score_mean | 1.7291666666666667 | 48 |
| method_flag_comparison | general_term_flag_valid_rate_score_ge_2 | 0.5416666666666666 | 48 |

## Candidate Type

| candidate_type | count | candidate_score_mean | candidate_score_median | valid_candidate_count_score_ge_2 | valid_candidate_rate_score_ge_2 | representative_flag_count | label_◎ | label_○ | label_△ | label_× |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| future_growth | 10 | 1.1 | 1.0 | 3 | 0.3 | 3 | 2 | 1 | 3 | 4 |
| proposed_top | 23 | 1.608695652173913 | 2.0 | 12 | 0.5217391304347826 | 9 | 5 | 7 | 8 | 3 |
| random_low_rank | 10 | 2.2 | 2.0 | 8 | 0.8 | 6 | 4 | 4 | 2 | 0 |
| unet_related | 10 | 1.8 | 1.5 | 5 | 0.5 | 4 | 4 | 1 | 4 | 1 |

## Method / Rank Comparison

| group_type | group_value | count | candidate_score_mean | candidate_score_median | valid_candidate_count_score_ge_2 | valid_candidate_rate_score_ge_2 | representative_flag_count | label_◎ | label_○ | label_△ | label_× |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proposed_or_baseline | baseline_random | 10 | 2.2 | 2.0 | 8 | 0.8 | 6 | 4 | 4 | 2 | 0 |
| proposed_or_baseline | proposed | 43 | 1.5348837209302326 | 1.0 | 20 | 0.46511627906976744 | 16 | 11 | 9 | 15 | 8 |
| specific_method_flag | 0 | 24 | 1.4583333333333333 | 1.5 | 12 | 0.5 | 9 | 4 | 8 | 7 | 5 |
| specific_method_flag | 1 | 29 | 1.8275862068965518 | 2.0 | 16 | 0.5517241379310345 | 13 | 11 | 5 | 10 | 3 |
| general_term_flag | 0 | 5 | 1.0 | 0.0 | 2 | 0.4 | 1 | 1 | 1 | 0 | 3 |
| general_term_flag | 1 | 48 | 1.7291666666666667 | 2.0 | 26 | 0.5416666666666666 | 21 | 14 | 12 | 17 | 5 |
| rank_bucket | rank_001_005 | 5 | 1.2 | 1.0 | 2 | 0.4 | 1 | 0 | 2 | 2 | 1 |
| rank_bucket | rank_006_010 | 25 | 1.76 | 2.0 | 14 | 0.56 | 11 | 8 | 6 | 8 | 3 |
| rank_bucket | rank_011_020 | 10 | 1.9 | 2.0 | 6 | 0.6 | 5 | 3 | 3 | 4 | 0 |
| rank_bucket | rank_021_plus | 3 | 2.6666666666666665 | 3.0 | 3 | 1.0 | 2 | 2 | 1 | 0 | 0 |
| rank_bucket | rank_missing | 10 | 1.1 | 1.0 | 3 | 0.3 | 3 | 2 | 1 | 3 | 4 |

## Precision@k

| proposed_or_baseline | k | evaluated_count | valid_candidate_count_score_ge_2 | precision_at_k | sort_basis |
| --- | --- | --- | --- | --- | --- |
| baseline_random | 5 | 5 | 4 | 0.8 | rank ascending, then review order |
| baseline_random | 10 | 10 | 8 | 0.8 | rank ascending, then review order |
| baseline_random | 20 | 10 | 8 | 0.8 | rank ascending, then review order |
| proposed | 5 | 5 | 2 | 0.4 | rank ascending, then review order |
| proposed | 10 | 10 | 4 | 0.4 | rank ascending, then review order |
| proposed | 20 | 20 | 8 | 0.4 | rank ascending, then review order |

## U-Net Subset

| subset | count | candidate_score_mean | candidate_score_median | valid_candidate_count_score_ge_2 | valid_candidate_rate_score_ge_2 | representative_flag_count | label_◎ | label_○ | label_△ | label_× |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| u_net_related | 13 | 1.9230769230769231 | 2.0 | 7 | 0.5384615384615384 | 6 | 6 | 1 | 5 | 1 |

## Notes

- `manual_review_key.csv` を `review_id` で結合し、`proposed_or_baseline` と `rank` を集計に使用しました。
- 元の `manual_review_with_human_filled.xlsx` は上書きしていません。
- Precision@k は `candidate_score >= 2` を妥当候補として計算しています。