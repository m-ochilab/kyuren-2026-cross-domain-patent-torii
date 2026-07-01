"""
卒論研究成果をデスクトップへ移すための軽量バンドルを作成する。

巨大な全件CSVや埋め込みnpyはコピーせず、manifestに元パスとサイズを残す。
卒論本文・発表・確認に必要な図、主要ランキング、レポート、サンプルCSV、
再現用スクリプトと設定をまとめる。
"""

from __future__ import annotations

import argparse
import csv
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd


PIPELINE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = PIPELINE_DIR.parent


def copy_file(src: Path, dst: Path, copied: list[dict], note: str = "") -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.append({
        "source_path": str(src),
        "bundle_path": str(dst),
        "bytes": src.stat().st_size,
        "note": note,
    })


def copy_tree_files(src_dir: Path, dst_dir: Path, copied: list[dict], pattern: str = "*", note: str = "") -> None:
    if not src_dir.exists():
        return
    for src in sorted(src_dir.glob(pattern)):
        if src.is_file():
            copy_file(src, dst_dir / src.name, copied, note)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def sample_csv(src: Path, dst: Path, nrows: int, copied: list[dict], note: str) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(src, nrows=nrows)
    df.to_csv(dst, index=False, encoding="utf-8")
    copied.append({
        "source_path": str(src),
        "bundle_path": str(dst),
        "bytes": dst.stat().st_size,
        "note": note,
    })


def collect_large_files() -> list[dict]:
    roots = [
        PIPELINE_DIR / "data" / "processed_full",
        PIPELINE_DIR / "data" / "processed_exports2",
        PIPELINE_DIR / "outputs" / "heterogeneous_exports2",
        PIPELINE_DIR / "cache" / "heterogeneous_exports2",
    ]
    rows = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.stat().st_size >= 100 * 1024 * 1024:
                rows.append({
                    "path": str(path),
                    "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
                    "why_not_copied": "100MB以上のため、軽量バンドルでは本体コピーせず元パスを記録",
                })
    return rows


def build_readme(bundle_dir: Path) -> str:
    return f"""# 卒論研究成果バンドル

作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

このフォルダは、卒論の研究結果を確認・本文へ転記しやすいようにまとめた軽量版です。
巨大な全件CSV、Top-k全件、埋め込みベクトルはコピーしていません。
それらは `manifests/large_files_manifest.csv` に元パスとサイズを記録しています。

## フォルダ構成

- `figures/`
  - 卒論本文・発表用のPNG図。
- `reports/`
  - Markdown / Excel の結果レポート。
- `results/heterogeneous_exports2/`
  - exports2 を使った異分野候補探索の主要出力。
- `results/ab_full_gapscore/`
  - A0/B0 full 実験のGapScore v2、U-Net確認、分野類似度出力。
- `research_data_samples/`
  - 研究データ本体の確認用サンプル。全件ではありません。
- `scripts_and_config/`
  - 再実行・確認に使うPythonスクリプトと設定ファイル。
- `manifests/`
  - コピー済みファイル一覧、巨大ファイル一覧。

## まず見るファイル

1. `reports/heterogeneous_analysis_report.md`
2. `reports/vector_ranking_quality_report_full.md`
3. `figures/fig04_exports2_top20_heterogeneous_candidates.png`
4. `figures/fig05_exports2_problem_solution_scatter_top5000.png`
5. `figures/fig11_ab_full_gapscore_v2_top10.png`
6. `results/heterogeneous_exports2/manual_review_candidates.csv`

## 現在の研究到達点

- A0/B0 full のベクトル化、類似度Top-k、GapScore v2ランキング、U-Net確認は完了。
- exports2 の C0/C1/S0/S1 データ整形、文脈抽出、ベクトル化、異分野候補ランキング、S1既知正例チェックは完了。
- 卒論用図は14枚生成済み。
- 次の作業は `manual_review_candidates.csv` の上位20〜50件の人手確認。

元プロジェクト:

`{PROJECT_DIR}`

バンドル作成先:

`{bundle_dir}`
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--sample-rows", type=int, default=1000)
    args = parser.parse_args()

    default_name = f"sotsuron_research_bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    bundle_dir = Path(args.output_dir) if args.output_dir else PIPELINE_DIR / "outputs" / default_name
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)

    copied: list[dict] = []

    thesis_figures = PIPELINE_DIR / "outputs" / "thesis_figures"
    copy_tree_files(thesis_figures, bundle_dir / "figures", copied, "*.png", "卒論用図")
    for name in ["figure_manifest.csv", "thesis_figures_readme.md", "thesis_figures_includegraphics.tex"]:
        copy_file(thesis_figures / name, bundle_dir / "figures" / name, copied, "図一覧・LaTeX貼り込み用")

    het = PIPELINE_DIR / "outputs" / "heterogeneous_exports2"
    for name in [
        "heterogeneous_analysis_report.md",
        "dataset_summary.md",
        "s1_representative_patent_cards.md",
    ]:
        copy_file(het / name, bundle_dir / "reports" / name, copied, "異分野候補探索レポート")
    for name in [
        "dataset_summary.csv",
        "vectorization_summary.csv",
        "heterogeneous_candidate_ranking.csv",
        "manual_review_candidates.csv",
        "s1_known_positive_summary.csv",
        "s1_no_leakage_check.csv",
    ]:
        copy_file(het / name, bundle_dir / "results" / "heterogeneous_exports2" / name, copied, "異分野候補探索の主要CSV")
    sample_csv(
        het / "problem_similarity_topk.csv",
        bundle_dir / "results" / "heterogeneous_exports2" / "problem_similarity_topk_head1000.csv",
        args.sample_rows,
        copied,
        "1GB級Top-k CSVの先頭サンプル",
    )

    full = PIPELINE_DIR / "data" / "processed_full"
    for name in ["vector_ranking_quality_report_full.md", "vector_ranking_quality_report_full.xlsx"]:
        copy_file(full / "reports" / name, bundle_dir / "reports" / name, copied, "A0/B0 full レポート")
    for name in [
        "method_gap_ranking_all_full.csv",
        "method_gap_ranking_pre_full.csv",
        "method_gap_ranking_specific_methods_full.csv",
        "method_gap_ranking_with_future_full.csv",
        "method_future_growth_evaluation_full.csv",
        "unet_ranking_check_full.csv",
    ]:
        copy_file(full / "ranking" / name, bundle_dir / "results" / "ab_full_gapscore" / name, copied, "A0/B0 full GapScore結果")
    for name in ["field_level_similarity_summary.csv", "field_level_similarity_summary_full.csv"]:
        copy_file(full / "similarity" / name, bundle_dir / "results" / "ab_full_gapscore" / name, copied, "A0/B0 full 分野類似度")

    processed_exports2 = PIPELINE_DIR / "data" / "processed_exports2"
    copy_file(
        processed_exports2 / "dataset_summary_exports2.csv",
        bundle_dir / "research_data_samples" / "dataset_summary_exports2.csv",
        copied,
        "exports2 processedデータ概要",
    )
    for domain in ["C0", "C1", "S0", "S1"]:
        for level in ["publication_level", "family_level"]:
            sample_csv(
                processed_exports2 / f"{domain}_{level}.csv",
                bundle_dir / "research_data_samples" / f"{domain}_{level}_head1000.csv",
                args.sample_rows,
                copied,
                f"{domain} {level} の先頭サンプル",
            )

    for cfg in ["config.yaml", "heterogeneous_exports2.yaml"]:
        copy_file(PIPELINE_DIR / "config" / cfg, bundle_dir / "scripts_and_config" / "config" / cfg, copied, "設定ファイル")
    for src in sorted((PIPELINE_DIR / "src").glob("*.py")):
        copy_file(src, bundle_dir / "scripts_and_config" / "src" / src.name, copied, "再現用Pythonスクリプト")

    readme_path = bundle_dir / "00_README.md"
    readme_path.write_text(build_readme(bundle_dir), encoding="utf-8")
    copied.insert(0, {
        "source_path": "generated",
        "bundle_path": str(readme_path),
        "bytes": readme_path.stat().st_size,
        "note": "バンドル説明",
    })

    write_csv(bundle_dir / "manifests" / "copied_files_manifest.csv", copied)
    write_csv(bundle_dir / "manifests" / "large_files_manifest.csv", collect_large_files())

    print(bundle_dir)


if __name__ == "__main__":
    main()
