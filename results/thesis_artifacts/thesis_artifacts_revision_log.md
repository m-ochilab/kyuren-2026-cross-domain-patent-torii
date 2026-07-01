# Thesis Artifacts Revision Log

## Revision Summary

`thesis_artifacts_adoption_review.md` の指摘を反映し、卒論用図表・表・生成スクリプトを修正した。

## Modified Files

- `pipeline/src/27_generate_thesis_figures_tables.py`
- `pipeline/outputs/thesis_artifacts/scripts/generate_thesis_figures.py`
- `pipeline/outputs/thesis_artifacts/scripts/generate_thesis_tables.py`
- `pipeline/outputs/thesis_artifacts/scripts/generate_all_thesis_artifacts.py`
- `pipeline/outputs/thesis_artifacts/figures/`
- `pipeline/outputs/thesis_artifacts/tables/`
- `pipeline/outputs/thesis_artifacts/thesis_artifacts_README.md`
- `pipeline/outputs/thesis_artifacts/figures/README.md`
- `pipeline/outputs/thesis_artifacts/thesis_artifacts_adoption_review_revised.md`

Root-level `figures/` and `tables/` were also refreshed for LaTeX inclusion.

## Main Revisions

### 1. Dataset Count Consistency

`dataset_summary_table` was revised so A0/B0 use final aggregate values from `pipeline/outputs/tables/dataset_summary.csv` instead of the 1,000-row processed samples.

Current key counts:

- A0: 54,100 publications / 30,093 families
- B0: 44,364 publications / 28,450 families
- A1: 4,028 raw future-source publications / 2,692 families
- B1: 859 raw future-source publications / 610 families
- C1: 522 family-level non-semiconductor pre-candidates before per-cluster expansion
- S1: 311 publications / 23 families / 7 use-case clusters
- S0_pre: 72,373 cluster-family rows
- S0_pre_filtered: 10,786 cluster-family rows

A1/B1 are marked as raw future sources because final split-specific use depends on Experiment 1 filtering.

### 2. Experiment 1 Result Table Split

The previous mixed `experiment1_result_table` was reorganized into:

- `experiment1_dataset_table.csv/.tex`
- `experiment1_unet_occurrence_table.csv/.tex`
- `experiment1_evaluation_summary_table.csv/.tex`
- a compact `experiment1_result_table.csv/.tex`

This separates dataset scale, U-Net occurrence, and evaluation metrics.

### 3. Experiment 1 Baseline Comparison Framing

The baseline comparison figure and table now state that the comparison characterizes candidate-set properties and is not a simple win/loss claim.

Added note:

> Auxiliary comparison: scores describe candidate-set characteristics, not simple win/loss.

The table includes:

> Candidate-set comparison; not a simple win/loss metric

This prevents overclaiming because true_random and frequency baselines can score high when they draw directly from B0, the manufacturing defect detection target field.

### 4. Experiment 2 Pipeline Clarification

`experiment2_pipeline` was revised to explicitly show:

- S1 known cases
- 7 use-case clusters
- C1 non-semiconductor pre-candidates
- ranking by cluster
- Top20 x 7 clusters
- family-level deduplication
- 46 unique families
- LLM-assisted author review

It also includes the note:

> Goal: extract expert-check candidates, not prove technical deployability.

### 5. Experiment 2 Baseline Terminology

Experiment 2 baseline terminology was standardized to:

- `lightweight fulltext baseline`
- `lightweight fulltext text baseline`

The generated README and figure notes state that this is not a strict BERT-style fulltext embedding experiment.

### 6. Terminology Standardization

The generated README and revised review use the following expressions:

- Experiment 1: main analysis
- Experiment 2: auxiliary analysis
- Evaluation: LLM-assisted author confirmation review
- Candidate: expert-check candidate
- Experiment 2 baseline: lightweight fulltext text baseline

Avoided expressions:

- direct claims of technical transfer prediction
- direct claims of proven applicability
- claims about predicting a company's strategic entry
- simple all-baseline victory claims
- strict BERT-style fulltext embedding wording for Experiment 2 baseline

## Regenerated Outputs

Figures:

- 10 PNG files
- 10 PDF files

Tables:

- 13 CSV files
- 13 LaTeX `.tex` files

Scripts:

- `generate_thesis_figures.py`
- `generate_thesis_tables.py`
- `generate_all_thesis_artifacts.py`

## Verification Checklist

- [x] Dataset counts are aligned with final aggregate values where available.
- [x] A0/B0 counts no longer use the 1,000-row sample files.
- [x] A1/B1 raw future-source counts are marked with notes.
- [x] Experiment 1 result tables are separated and easier to read.
- [x] Baseline comparison is not framed as an overclaim or all-baseline victory.
- [x] Experiment 2 pipeline includes Top20 x 7, family-level deduplication, and 46-family review.
- [x] Experiment 2 baseline is not described as a strict BERT-style fulltext embedding experiment.
- [x] Experiment 1 is described as the main analysis.
- [x] Experiment 2 is described as the auxiliary analysis.
- [x] Strict Experiment 2 label summary matches: ◎11, ○5, △12, ×18, ◎+○16, ◎+○+△28.
- [x] Fulltext baseline summary matches: proposed 46, fulltext 56, overlap 11, proposed-only 35, fulltext-only 45.

## Regeneration Command

```bash
python3 pipeline/outputs/thesis_artifacts/scripts/generate_all_thesis_artifacts.py
```
