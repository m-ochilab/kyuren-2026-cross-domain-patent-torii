# Baseline Comparison Design Note

既存評価で `random_low_rank` として扱っていた候補は、完全なランダム抽出ではなく、全文BERT top-k表の低順位側から抽出された比較候補である。そのため、本比較では名称を `fulltext_low_rank_baseline` に変更し、真のランダムベースラインとは区別する。

新たに `true_random_baseline` として、B0文脈データ全体から本文情報を持つ特許を固定乱数seed=42で抽出した。また、全文BERTによる正式な比較対象として `fulltext_top_baseline` を作成し、`A0_to_B0_fulltext_topk_full.csv` の上位候補からB0側特許を抽出した。さらに、B0内で頻度の高い `technical_means` に対応する代表特許を `frequency_top_baseline` として作成した。

本比較では、提案手法が高スコア候補を出せるかだけでなく、候補理由の説明可能性、すなわち課題文脈・解決手段・技術手段・対象物の対応が人間にとって確認しやすいかも評価対象とする。LLM支援による仮評価を用いる場合でも、最終的な `human_candidate_score` と `human_final_label` は著者が確認・修正した人手評価を用いる。
