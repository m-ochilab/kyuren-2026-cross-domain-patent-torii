#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ARTIFACT_DIR = PROJECT_ROOT / "pipeline/outputs/thesis_artifacts"
SCRIPT_DIR = ARTIFACT_DIR / "scripts"


README_TEXT = """# Thesis Artifacts README

This directory contains reproducible figures and tables for the thesis:

**Patent-based cross-domain technology candidate extraction using problem/solution context separation.**

Experiment 1 is treated as the main analysis. Experiment 2 is treated as an auxiliary analysis.

## Inputs

- Experiment 1 final review and baseline summaries:
  - `pipeline/outputs/experiment1_data_bundle/outputs/final_human_review_all.csv`
  - `pipeline/outputs/experiment1_data_bundle/outputs/final_candidate_type_summary.csv`
  - `pipeline/outputs/experiment1_data_bundle/outputs/final_method_comparison_summary.csv`
  - `pipeline/outputs/experiment1_data_bundle/outputs/final_precision_at_k_summary.csv`
  - `pipeline/outputs/tables/dataset_summary.csv`
  - `pipeline/outputs/tables/method_counts_by_year.csv`
- Experiment 2 strict review and cluster summaries:
  - `pipeline/outputs/experiment2_heterogeneous_bundle/outputs/heterogeneous_manual_review_final_strict.csv`
  - `pipeline/outputs/experiment2_heterogeneous_bundle/outputs/heterogeneous_manual_review_by_cluster.csv`
  - `pipeline/outputs/experiment2_heterogeneous_bundle/outputs/proposed_vs_fulltext_overlap.csv`
  - `pipeline/outputs/experiment2_heterogeneous_bundle/outputs/s1_c1_preparation_summary.csv`
- Dataset source files:
  - `pipeline/data/processed/A0_publication_level.csv`
  - `pipeline/data/raw/A1_orbis_publication_level.csv`
  - `pipeline/data/processed/B0_publication_level.csv`
  - `pipeline/data/raw/B1_orbis_publication_level.csv`
  - `pipeline/outputs/experiment2_heterogeneous_bundle/outputs/C1_pre_for_each_cluster.csv`
  - `pipeline/outputs/experiment2_heterogeneous_bundle/outputs/S1_cluster_first_dates.csv`

## Figures

All figures are generated as both PNG and PDF in `figures/`.

- `framework_overview`: Method chapter. Overall flow from patent text to LLM extraction, context vectors, candidate ranking, and human review.
- `solution_type_quadrant`: Method chapter. Two-axis positioning by problem-context similarity and solution-context similarity.
- `method_pipeline`: Method chapter. Full proposed pipeline from data acquisition to evaluation.
- `experiment1_pipeline`: Experiment 1 chapter. A0/A1/B0/B1, temporal split, U-Net candidate extraction, baselines, and human review.
- `experiment1_unet_trend`: Experiment 1 chapter. Annual U-Net count trend in medical image analysis and manufacturing defect detection.
- `experiment1_baseline_comparison`: Experiment 1 chapter. Proposed method and baseline candidate-quality comparison.
- `experiment2_pipeline`: Experiment 2 chapter. S1 clustering, C1 non-semiconductor pre candidates, cluster ranking, Top20 x 7, family deduplication, and 46-family review.
- `experiment2_label_distribution`: Experiment 2 chapter. Strict human-label distribution.
- `experiment2_cluster_distribution`: Experiment 2 chapter. Cluster-level stacked label distribution.
- `experiment2_fulltext_overlap`: Experiment 2 chapter or appendix. Proposed method vs lightweight fulltext text baseline overlap.

## Tables

All tables are generated as both CSV and LaTeX in `tables/`.

- `dataset_summary_table`: Method/data chapter. Dataset list for Experiment 1 and Experiment 2.
- `extraction_fields_table`: Method chapter. Definitions of LLM extraction fields.
- `solution_type_definition_table`: Method chapter. Near-solution and heterogeneous-solution definitions.
- `experiment1_result_table`: Experiment 1 chapter. U-Net and temporal evaluation summary.
- `experiment1_dataset_table`: Experiment 1 chapter. Dataset and temporal split only.
- `experiment1_unet_occurrence_table`: Experiment 1 chapter. U-Net occurrence counts/rates only.
- `experiment1_evaluation_summary_table`: Experiment 1 chapter. U-Net ranking position and occurrence summary.
- `experiment1_result_table`: Experiment 1 chapter. Compact main-analysis summary.
- `experiment1_baseline_table`: Experiment 1 chapter. Candidate-set comparison table. This is not a simple precision win/loss table.
- `experiment2_label_summary_table`: Experiment 2 chapter. Strict human-label counts. Expected: Strong=11, Plausible=5, Weak=12, Reject=18, Strong+Plausible=16, Broad=28.
- `experiment2_cluster_summary_table`: Experiment 2 chapter. Cluster-level strict review summary.
- `experiment2_fulltext_baseline_table`: Experiment 2 appendix/discussion. Proposed vs lightweight fulltext baseline comparison. Expected: proposed=46, fulltext=56, overlap=11, proposed_only=35, fulltext_only=45.
- `experiment1_experiment2_comparison_table`: Discussion. Main vs auxiliary analysis comparison.
- `limitations_table`: Discussion/limitations. Scope and validity caveats.

## Regeneration

Run all figures and tables:

```bash
python3 pipeline/outputs/thesis_artifacts/scripts/generate_all_thesis_artifacts.py
```

Run only figures:

```bash
python3 pipeline/outputs/thesis_artifacts/scripts/generate_thesis_figures.py
```

Run only tables:

```bash
python3 pipeline/outputs/thesis_artifacts/scripts/generate_thesis_tables.py
```

## Notes

- Matplotlib is used; seaborn is not used.
- Figure labels are in English to avoid Japanese font issues. Japanese captions can be added in the thesis text.
- Experiment 2 is an auxiliary interpretability analysis for expert-check candidates. It does not prove technical deployability.
- Experiment 1 is the **main analysis**. Experiment 2 is the **auxiliary analysis**.
- Evaluation should be described as **LLM-assisted author confirmation review**.
- Extracted candidates should be described as **expert-check candidates**.
- Experiment 2 baseline should be described as a **lightweight fulltext text baseline**, not as a strict BERT-style embedding experiment.
- Experiment 1 baseline comparison should not be presented as a simple all-baseline victory. Some direct baselines can score high because B0 itself is the manufacturing defect detection target field. The intended claim is explainable candidate extraction using problem/solution contexts.
- Root-level `figures/` and `tables/` are also updated for easy LaTeX `\\includegraphics` and `\\input`.

## Final Checklist

- Dataset counts use final aggregate values where available; uncertain raw/future-source counts are noted.
- Experiment 1 result tables are separated into dataset, U-Net occurrence, and evaluation summaries.
- Baseline comparison is framed as auxiliary candidate-set characterization, not overclaiming.
- Experiment 2 pipeline includes Top20 x 7 clusters, family-level deduplication, 46 unique families, and LLM-assisted author review.
- Experiment 2 baseline is not described as a strict BERT-style fulltext experiment.
- Experiment 1 is consistently the main analysis; Experiment 2 is consistently the auxiliary analysis.
"""


def run(script_name: str) -> None:
    subprocess.run([sys.executable, str(SCRIPT_DIR / script_name)], cwd=PROJECT_ROOT, check=True)


def write_readme() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "thesis_artifacts_README.md").write_text(README_TEXT, encoding="utf-8")
    (ARTIFACT_DIR / "figures" / "README.md").write_text(README_TEXT, encoding="utf-8")


def write_manifest() -> None:
    rows = []
    for path in sorted(ARTIFACT_DIR.rglob("*")):
        if path.is_file() and path.name != "manifest.csv":
            rows.append(f"{path.relative_to(ARTIFACT_DIR)},{path.stat().st_size}")
    (ARTIFACT_DIR / "manifest.csv").write_text("relative_path,bytes\n" + "\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    (ARTIFACT_DIR / "figures").mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "tables").mkdir(parents=True, exist_ok=True)
    run("generate_thesis_figures.py")
    run("generate_thesis_tables.py")
    write_readme()
    write_manifest()
    print(f"Generated all thesis artifacts in {ARTIFACT_DIR}")


if __name__ == "__main__":
    main()
