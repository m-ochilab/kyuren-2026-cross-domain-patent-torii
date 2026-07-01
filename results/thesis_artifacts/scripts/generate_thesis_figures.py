#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ARTIFACT_DIR = PROJECT_ROOT / "pipeline/outputs/thesis_artifacts"
FIG_DIR = ARTIFACT_DIR / "figures"
ROOT_FIG_DIR = PROJECT_ROOT / "figures"
SRC_SCRIPT = PROJECT_ROOT / "pipeline/src/27_generate_thesis_figures_tables.py"


def load_generator_module():
    spec = importlib.util.spec_from_file_location("thesis_figures_tables_generator", SRC_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {SRC_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    module = load_generator_module()
    module.OUT_DIR = ARTIFACT_DIR
    module.FIG_DIR = FIG_DIR
    module.ROOT_FIG_DIR = ROOT_FIG_DIR

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    ROOT_FIG_DIR.mkdir(parents=True, exist_ok=True)

    module.fig_framework_overview()
    module.fig_solution_type_quadrant()
    module.fig_method_pipeline()
    module.fig_experiment1_pipeline()
    module.fig_experiment1_unet_trend()
    module.fig_experiment1_baseline_comparison()
    module.fig_experiment2_pipeline()
    module.fig_experiment2_label_distribution()
    module.fig_experiment2_cluster_distribution()
    module.fig_experiment2_fulltext_overlap()

    for path in FIG_DIR.glob("*"):
        if path.suffix.lower() in {".png", ".pdf"}:
            shutil.copy2(path, ROOT_FIG_DIR / path.name)

    print(f"Generated thesis figures in {FIG_DIR}")


if __name__ == "__main__":
    main()
