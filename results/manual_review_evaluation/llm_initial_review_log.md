# LLM Initial Review Log

## 使用した入力ファイル

- `pipeline/outputs/manual_review_evaluation/manual_review_blind.csv`
- `pipeline/outputs/manual_review_evaluation/manual_review_rubric.md`
- `manual_review_key.csv`, `manual_review_summary.csv`, `manual_review_summary.md` はLLM評価時に使用していません。

## 評価設定

- 評価対象件数: 53
- 使用したLLMモデル名: Codex (GPT-5)
- 利用日: 2026-06-11
- temperature: not exposed in this environment

## 評価基準の概要

- 文脈抽出評価: problem_context / solution_context / technical_means / target_object が本文内容を評価に使える形で表しているかを0-2で仮評価。
- 候補評価: 製造欠陥検出・画像検査・異常検出への課題類似性、解決手段の参考可能性、代表例としての説明しやすさを仮評価。
- `llm_candidate_score`: 3=◎, 2=○, 1=△, 0=×。

## 重要な注意

- LLM評価は最終評価ではなく、人間確認前の仮評価です。
- 最終的な `candidate_score` と `final_label` は、人間が本文とrubricを確認して決定します。
- rank / score / source 情報を見ず、blindファイルの本文・文脈情報のみで評価しました。

## 欠損値や本文不足の扱い

- 欠損値は空欄として扱いました。
- problem_context または solution_context が不足する場合は、抽出評価を低めにし、判断根拠が弱い場合は `llm_confidence = low` としました。
- 一般語中心の技術手段は `llm_technical_means_score` を1以下に抑える方針で仮評価しました。

## confidence 件数

- high: 23
- medium: 16
- low: 14

## llm_candidate_score 件数

- 0: 7
- 1: 15
- 2: 4
- 3: 27

## llm_final_label 件数

- ◎: 27
- ○: 4
- △: 15
- ×: 7

## U-Net関連候補

- 件数: 13
- llm_candidate_score平均: 2.000

## 出力ファイル

- `pipeline/outputs/manual_review_evaluation/llm_initial_review.csv`
- `pipeline/outputs/manual_review_evaluation/llm_initial_review.xlsx`
- `pipeline/outputs/manual_review_evaluation/manual_review_with_llm_suggestions.csv`
- `pipeline/outputs/manual_review_evaluation/manual_review_with_llm_suggestions.xlsx`
- `pipeline/outputs/manual_review_evaluation/llm_assisted_review_method_note.md`

## rubric 参照概要

# Manual Review Rubric

## 文脈抽出評価

### problem_extraction_score

- 2 = 課題・目的・問題点が正しく抽出されている
- 1 = 一部曖昧だが評価に使える
- 0 = 誤抽出、または不十分

### solution_extraction_score

- 2 = 解決手段・構成・方法が正しく抽出されている
- 1 = 一部曖昧だが評価に使える
- 0 = 誤抽出、または不十分

### technical_means_score

- 2 = 技術手段名として適切で、具体性がある
- 1 = 関係はあるが一般語・抽象語である
- 0 = 技術手段として不適切

### target_object_score

- 2 = 対象物が明確で正しい
- 1 = 一部曖昧だが使える
- 0 = 不明または不適切

## 候補評価

### problem_similarity_score

- 2 = 参照分野と対象分野で課題が明確に近い
- 1 = 一部近いが、対象・用途がずれる
- 0 = 課題が近いとは言いにくい

### solution_relevance_score

- 2 = 解決手段が対象分野の候補として参考になりそう
- 1 = 関係はあるが、候補としては弱い
- 0 = 解決手段として参考にしにくい

### candidate_score

- 3 = ◎ 卒論の代表例として使える
- 2 = ○ 専門家確認候補として妥当
- 1 = △ 関係はあるが弱い・曖昧
- 0 = × 候補として不適切

### representative_flag

- 1 = 代表特許として本文で説明できる
- 0 = 代表特許としては弱い

### final_label

- ◎ / ○ / △ / × のいずれかを記入する