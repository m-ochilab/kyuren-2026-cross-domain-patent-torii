# Final Human Review Summary

- total rows: 143
- evaluated rows: 143
- unevaluated rows: 0
- baseline review source: `/Users/h-torii4649/Downloads/baseline_review_with_human_filled_strict.csv`

## Candidate Type

| group_value | count | candidate_score_mean | candidate_score_median | valid_candidate_count_score_ge_2 | valid_candidate_rate_score_ge_2 | representative_flag_count | label_◎ | label_○ | label_△ | label_× |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frequency_top_baseline | 30 | 2.2666666666666666 | 3.0 | 23 | 0.7666666666666667 | 17 | 17 | 6 | 5 | 2 |
| fulltext_low_rank_baseline | 10 | 2.2 | 2.0 | 8 | 0.8 | 6 | 4 | 4 | 2 | 0 |
| fulltext_top_baseline | 30 | 0.5666666666666667 | 0.0 | 5 | 0.16666666666666666 | 1 | 1 | 4 | 6 | 19 |
| future_growth | 10 | 1.1 | 1.0 | 3 | 0.3 | 3 | 2 | 1 | 3 | 4 |
| proposed_top | 23 | 1.608695652173913 | 2.0 | 12 | 0.5217391304347826 | 9 | 5 | 7 | 8 | 3 |
| true_random_baseline | 30 | 2.066666666666667 | 3.0 | 20 | 0.6666666666666666 | 16 | 16 | 4 | 6 | 4 |
| unet_related | 10 | 1.8 | 1.5 | 5 | 0.5 | 4 | 4 | 1 | 4 | 1 |

## Method Comparison

| group_type | group_value | count | candidate_score_mean | candidate_score_median | valid_candidate_count_score_ge_2 | valid_candidate_rate_score_ge_2 | representative_flag_count | label_◎ | label_○ | label_△ | label_× |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proposed_or_baseline | baseline | 90 | 1.6333333333333333 | 2.0 | 48 | 0.5333333333333333 | 34 | 34 | 14 | 17 | 25 |
| proposed_or_baseline | baseline_random | 10 | 2.2 | 2.0 | 8 | 0.8 | 6 | 4 | 4 | 2 | 0 |
| proposed_or_baseline | proposed | 43 | 1.5348837209302326 | 1.0 | 20 | 0.46511627906976744 | 16 | 11 | 9 | 15 | 8 |
| specific_method_flag | 0 | 77 | 1.4675324675324675 | 1.0 | 38 | 0.4935064935064935 | 26 | 21 | 17 | 16 | 23 |
| specific_method_flag | 1 | 66 | 1.8484848484848484 | 2.0 | 38 | 0.5757575757575758 | 30 | 28 | 10 | 18 | 10 |
| general_term_flag | 0 | 10 | 0.5 | 0.0 | 2 | 0.2 | 1 | 1 | 1 | 0 | 8 |
| general_term_flag | 1 | 133 | 1.7293233082706767 | 2.0 | 74 | 0.556390977443609 | 55 | 48 | 26 | 34 | 25 |
| rank_bucket | rank_001_005 | 40 | 0.875 | 0.5 | 11 | 0.275 | 5 | 4 | 7 | 9 | 20 |
| rank_bucket | rank_006_010 | 30 | 1.8333333333333333 | 2.0 | 18 | 0.6 | 13 | 10 | 8 | 9 | 3 |
| rank_bucket | rank_011_020 | 20 | 2.0 | 2.0 | 13 | 0.65 | 11 | 9 | 4 | 5 | 2 |
| rank_bucket | rank_021_plus | 13 | 2.4615384615384617 | 3.0 | 11 | 0.8461538461538461 | 8 | 8 | 3 | 2 | 0 |
| rank_bucket | rank_missing | 40 | 1.825 | 2.0 | 23 | 0.575 | 19 | 18 | 5 | 9 | 8 |

## Precision@k

| candidate_type | k | evaluated_count | valid_candidate_count_score_ge_2 | precision_at_k |
| --- | --- | --- | --- | --- |
| frequency_top_baseline | 5 | 5 | 4 | 0.8 |
| frequency_top_baseline | 10 | 10 | 8 | 0.8 |
| frequency_top_baseline | 20 | 20 | 15 | 0.75 |
| fulltext_low_rank_baseline | 5 | 5 | 4 | 0.8 |
| fulltext_low_rank_baseline | 10 | 10 | 8 | 0.8 |
| fulltext_low_rank_baseline | 20 | 10 | 8 | 0.8 |
| fulltext_top_baseline | 5 | 5 | 0 | 0.0 |
| fulltext_top_baseline | 10 | 10 | 2 | 0.2 |
| fulltext_top_baseline | 20 | 20 | 2 | 0.1 |
| future_growth | 5 | 5 | 1 | 0.2 |
| future_growth | 10 | 10 | 3 | 0.3 |
| future_growth | 20 | 10 | 3 | 0.3 |
| proposed_top | 5 | 5 | 2 | 0.4 |
| proposed_top | 10 | 10 | 3 | 0.3 |
| proposed_top | 20 | 20 | 9 | 0.45 |
| true_random_baseline | 5 | 5 | 3 | 0.6 |
| true_random_baseline | 10 | 10 | 7 | 0.7 |
| true_random_baseline | 20 | 20 | 13 | 0.65 |
| unet_related | 5 | 5 | 2 | 0.4 |
| unet_related | 10 | 10 | 5 | 0.5 |
| unet_related | 20 | 10 | 5 | 0.5 |

## U-Net Subset

| subset | count | candidate_score_mean | candidate_score_median | valid_candidate_count_score_ge_2 | valid_candidate_rate_score_ge_2 | representative_flag_count | label_◎ | label_○ | label_△ | label_× |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| u_net_related | 18 | 2.0555555555555554 | 3.0 | 11 | 0.6111111111111112 | 10 | 10 | 1 | 5 | 2 |
