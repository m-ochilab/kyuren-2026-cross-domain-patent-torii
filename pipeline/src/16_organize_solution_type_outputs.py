"""
研究成果を「近接解決策型」と「異質解決策型」に分けて整理する。

元ファイルは移動しない。重いCSVを重複コピーしないため、整理フォルダには
シンボリックリンクを作る。READMEとmanifestは通常ファイルとして生成する。
"""

from __future__ import annotations

import argparse
import csv
import shutil
from datetime import datetime
from pathlib import Path


PIPELINE_DIR = Path(__file__).resolve().parents[1]


def rel_to_pipeline(path: Path) -> str:
    try:
        return str(path.relative_to(PIPELINE_DIR))
    except ValueError:
        return str(path)


def ensure_clean_dir(path: Path, clean: bool) -> None:
    if clean and path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def link_file(src: Path, dst: Path, rows: list[dict], category: str, note: str) -> None:
    if not src.exists():
        rows.append({
            "category": category,
            "name": dst.name,
            "status": "missing",
            "source_path": str(src),
            "organized_path": str(dst),
            "size_mb": "",
            "note": note,
        })
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    dst.symlink_to(src.resolve())
    rows.append({
        "category": category,
        "name": dst.name,
        "status": "linked",
        "source_path": str(src.resolve()),
        "organized_path": str(dst),
        "size_mb": round(src.stat().st_size / 1024 / 1024, 3),
        "note": note,
    })


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "name", "status", "source_path", "organized_path", "size_mb", "note"])
        writer.writeheader()
        writer.writerows(rows)


def write_root_readme(out_dir: Path) -> None:
    text = f"""# Solution Type Organized Outputs

作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

このフォルダは、卒論の実験結果を以下の2系統に分けて見やすくしたものです。
元データは移動していません。ここにあるCSV/Markdown/PNGの多くは元ファイルへのシンボリックリンクです。

## 01_near_solution_type

近接解決策型です。課題文ベクトルや解決策文ベクトルの近さ、A0/B0のGapScore・U-Net確認など、
「近い課題・近い/既存解決策の確認」に関係する成果物を入れています。

主な元データ:

- `pipeline/data/processed/similarity/`
- `pipeline/data/processed_full/similarity/`
- `pipeline/data/processed/ranking/`
- `pipeline/data/processed_full/ranking/`

## 02_heterogeneous_solution_type

異質解決策型です。C0/C1をsource、S0をtargetとして、課題は近いが解決策が異なる候補を探索した
exports2系の成果物を入れています。

主な元データ:

- `pipeline/outputs/heterogeneous_exports2/`
- `pipeline/data/processed_exports2/`

## 注意

- `A0_to_B0_*_topk_full.csv` や `problem_similarity_topk.csv` は大きいので、コピーではなくリンクです。
- この整理フォルダ内でファイルを削除しても、リンク自体が消えるだけで元ファイルは残ります。
- 近接解決策型の専用スコア `near_solution_score = problem_similarity * solution_similarity` のランキングは、現時点では未作成です。ここには現在までに調べた関連成果物を整理しています。
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")


def write_type_readmes(out_dir: Path) -> None:
    near = out_dir / "01_near_solution_type"
    near_text = """# 近接解決策型

## 目的

課題文・解決策文が近い技術を確認し、既存応用・既知正例・周辺技術が拾えているかを見るための系統です。

## ここに入れたもの

- `data/similarity_sample/`: 1000件サンプルのA0/B0類似度Top-k
- `data/similarity_full/`: 全件A0/B0類似度Top-k
- `data/ranking_sample/`: 1000件サンプルのGapScore関連ランキング
- `data/ranking_full/`: 全件GapScore v2・U-Net確認
- `reports/`: vector/ranking品質レポート
- `figures/`: A0/B0類似度、GapScore v2、具体手法、U-Net確認の図

## 現状

近接解決策型の「専用ランキング」はまだ未作成です。
次にやるなら、problem top-k と solution similarity を結合し、
`near_solution_score = problem_similarity * solution_similarity` を作るのが自然です。
"""
    (near / "README.md").write_text(near_text, encoding="utf-8")

    hetero = out_dir / "02_heterogeneous_solution_type"
    hetero_text = """# 異質解決策型

## 目的

S0半導体洗浄の課題に近く、C0/C1側の解決策が異なる候補を抽出するための系統です。

## データの役割

- `C0_core`: 洗浄・除去・リンス系の広いsource
- `C1`: 花王の洗浄・除去・リンス系source
- `S0`: 半導体洗浄target
- `S1_core`: 花王の半導体洗浄既知正例

## ここに入れたもの

- `data/`: 異質解決策型ランキング、手動確認候補、S1確認、データ概要
- `reports/`: 異質解決策型のMarkdownレポート
- `figures/`: 異質解決策型の図

## 現状

全件実行済みです。次は `manual_review_candidates.csv` の上位20〜50件を人手確認する段階です。
"""
    (hetero / "README.md").write_text(hetero_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(PIPELINE_DIR / "outputs" / "by_solution_type"))
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    ensure_clean_dir(out_dir, clean=not args.no_clean)

    near = out_dir / "01_near_solution_type"
    hetero = out_dir / "02_heterogeneous_solution_type"
    for path in [
        near / "data" / "similarity_sample",
        near / "data" / "similarity_full",
        near / "data" / "ranking_sample",
        near / "data" / "ranking_full",
        near / "reports",
        near / "figures",
        hetero / "data",
        hetero / "reports",
        hetero / "figures",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    # 近接解決策型: A0/B0 vector similarity and ranking.
    for src in sorted((PIPELINE_DIR / "data" / "processed" / "similarity").glob("*.csv")):
        link_file(src, near / "data" / "similarity_sample" / src.name, rows, "near_solution_type", "A0/B0 1000件サンプル類似度")
    for src in sorted((PIPELINE_DIR / "data" / "processed_full" / "similarity").glob("*.csv")):
        link_file(src, near / "data" / "similarity_full" / src.name, rows, "near_solution_type", "A0/B0 全件類似度")
    for src in sorted((PIPELINE_DIR / "data" / "processed" / "ranking").glob("*.csv")):
        link_file(src, near / "data" / "ranking_sample" / src.name, rows, "near_solution_type", "A0/B0 1000件サンプルGapScore")
    for src in sorted((PIPELINE_DIR / "data" / "processed_full" / "ranking").glob("*.csv")):
        link_file(src, near / "data" / "ranking_full" / src.name, rows, "near_solution_type", "A0/B0 全件GapScore v2")
    for src in sorted((PIPELINE_DIR / "data" / "processed" / "reports").glob("vector_ranking_quality_report*")):
        link_file(src, near / "reports" / src.name, rows, "near_solution_type", "サンプル品質レポート")
    for src in sorted((PIPELINE_DIR / "data" / "processed_full" / "reports").glob("vector_ranking_quality_report_full*")):
        link_file(src, near / "reports" / src.name, rows, "near_solution_type", "全件品質レポート")
    for name in [
        "fig10_ab_full_field_similarity.png",
        "fig11_ab_full_gapscore_v2_top10.png",
        "fig12_ab_full_specific_method_rates.png",
        "fig13_ab_full_future_growth_top12.png",
        "fig14_ab_full_unet_ranking_check.png",
    ]:
        src = PIPELINE_DIR / "outputs" / "thesis_figures" / name
        link_file(src, near / "figures" / name, rows, "near_solution_type", "近接/GapScore系の卒論図")

    # 異質解決策型: exports2 heterogeneous analysis.
    hetero_out = PIPELINE_DIR / "outputs" / "heterogeneous_exports2"
    for name in [
        "dataset_summary.csv",
        "vectorization_summary.csv",
        "problem_similarity_topk.csv",
        "heterogeneous_candidate_ranking.csv",
        "manual_review_candidates.csv",
        "s1_known_positive_summary.csv",
        "s1_no_leakage_check.csv",
    ]:
        src = hetero_out / name
        link_file(src, hetero / "data" / name, rows, "heterogeneous_solution_type", "異質解決策型の主要CSV")
    for name in [
        "dataset_summary.md",
        "heterogeneous_analysis_report.md",
        "s1_representative_patent_cards.md",
    ]:
        src = hetero_out / name
        link_file(src, hetero / "reports" / name, rows, "heterogeneous_solution_type", "異質解決策型のレポート")
    for src in sorted((hetero_out / "figures").glob("*.png")):
        link_file(src, hetero / "figures" / src.name, rows, "heterogeneous_solution_type", "異質解決策型の実行時図")
    for name in [
        "fig01_exports2_dataset_size.png",
        "fig02_exports2_text_coverage.png",
        "fig03_exports2_vector_empty_rate.png",
        "fig04_exports2_top20_heterogeneous_candidates.png",
        "fig05_exports2_problem_solution_scatter_top5000.png",
        "fig06_exports2_score_components_top15.png",
        "fig07_exports2_s1_known_positive_similarity.png",
        "fig08_exports2_source_dataset_share.png",
        "fig09_exports2_filing_year_trend.png",
    ]:
        src = PIPELINE_DIR / "outputs" / "thesis_figures" / name
        link_file(src, hetero / "figures" / name, rows, "heterogeneous_solution_type", "異質解決策型の卒論図")

    write_root_readme(out_dir)
    write_type_readmes(out_dir)
    write_csv(out_dir / "manifest.csv", rows)
    print(out_dir)


if __name__ == "__main__":
    main()
