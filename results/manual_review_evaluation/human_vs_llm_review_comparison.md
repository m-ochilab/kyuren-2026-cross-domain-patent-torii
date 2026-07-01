# Human vs LLM Review Comparison

## agreement

| metric | value | count |
| --- | --- | --- |
| score_agreement_rate | 0.5471698113207547 | 53 |
| label_agreement_rate | 0.5471698113207547 | 53 |
| human_modified_flag_count | 24.0 | 53 |
| mean_score_delta_human_minus_llm | -0.3018867924528302 | 53 |

## agreement_by_candidate_type

| metric | value | count |
| --- | --- | --- |
| future_growth | 0.7 | 10 |
| proposed_top | 0.4782608695652174 | 23 |
| random_low_rank | 0.5 | 10 |
| unet_related | 0.6 | 10 |

## Largest Score Differences

| review_id | candidate_type | method_name | llm_candidate_score | human_candidate_score | score_delta_human_minus_llm | llm_final_label | human_final_label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MR0001 | proposed_top | 画像セグメンテーション | 3 | 0 | -3 | ◎ | × |
| MR0015 | proposed_top | encoder-decoder | 1 | 3 | 2 | △ | ◎ |
| MR0028 | unet_related | U-Net | 3 | 1 | -2 | ◎ | △ |
| MR0029 | unet_related | U-Net | 3 | 1 | -2 | ◎ | △ |
| MR0033 | unet_related | U-Net | 1 | 3 | 2 | △ | ◎ |
| MR0002 | proposed_top | 画像生成・再構成 | 3 | 2 | -1 | ◎ | ○ |
| MR0003 | proposed_top | 深層学習モデル | 3 | 2 | -1 | ◎ | ○ |
| MR0005 | proposed_top | 画像処理システム | 2 | 1 | -1 | ○ | △ |
| MR0006 | proposed_top | 機械学習モデル | 3 | 2 | -1 | ◎ | ○ |
| MR0009 | proposed_top | random forest | 1 | 0 | -1 | △ | × |
| MR0012 | proposed_top | skip connection | 2 | 1 | -1 | ○ | △ |
| MR0014 | proposed_top | ResNet | 1 | 2 | 1 | △ | ○ |
| MR0018 | proposed_top | VGG | 3 | 2 | -1 | ◎ | ○ |
| MR0020 | proposed_top | 画像処理方法 | 2 | 1 | -1 | ○ | △ |
| MR0022 | proposed_top | Domain Adaptation | 3 | 2 | -1 | ◎ | ○ |
| MR0026 | unet_related | U-Net | 3 | 2 | -1 | ◎ | ○ |
| MR0034 | random_low_rank | 撮像装置; 検査装置 | 3 | 2 | -1 | ◎ | ○ |
| MR0036 | random_low_rank | 欠陥検出; 画像処理システム | 3 | 2 | -1 | ◎ | ○ |
| MR0038 | random_low_rank | 画像前処理; 画像生成・再構成; 撮像装置; 検査装置 | 3 | 2 | -1 | ◎ | ○ |
| MR0040 | random_low_rank | 検出方法 | 3 | 2 | -1 | ◎ | ○ |