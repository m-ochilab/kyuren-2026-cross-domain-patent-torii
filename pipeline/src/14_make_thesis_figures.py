"""
卒論用の図をまとめて生成するスクリプト。

対象:
  1. exports2 の異分野候補探索結果
  2. A0/B0 full の GapScore v2 結果

出力:
  - pipeline/outputs/thesis_figures/*.png
  - pipeline/outputs/thesis_figures/figure_manifest.csv
  - pipeline/outputs/thesis_figures/thesis_figures_readme.md
"""

from __future__ import annotations

import argparse
import logging
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "thesis_figures"
HET_OUTPUT_DIR = ROOT / "outputs" / "heterogeneous_exports2"
EXPORTS2_PROCESSED_DIR = ROOT / "data" / "processed_exports2"
FULL_PROCESSED_DIR = ROOT / "data" / "processed_full"

COLORS = {
    "C0_core": "#2B6CB0",
    "C0": "#2B6CB0",
    "C1": "#805AD5",
    "S0": "#DD6B20",
    "S1_core": "#38A169",
    "S1": "#38A169",
    "A0": "#1F77B4",
    "B0": "#D62728",
    "accent": "#319795",
    "muted": "#718096",
    "dark": "#2D3748",
}


def setup_logger() -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    return logging.getLogger("thesis_figures")


def setup_font(logger: logging.Logger) -> None:
    candidates = [
        "Hiragino Sans",
        "Hiragino Kaku Gothic Pro",
        "Yu Gothic",
        "Noto Sans CJK JP",
        "AppleGothic",
        "IPAGothic",
        "DejaVu Sans",
    ]
    available = {font.name for font in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            plt.rcParams["font.family"] = font
            plt.rcParams["axes.unicode_minus"] = False
            logger.info("font: %s", font)
            return
    plt.rcParams["axes.unicode_minus"] = False
    logger.warning("日本語フォントが見つからないため、既定フォントを使います。")


def save_figure(fig: plt.Figure, output_dir: Path, filename: str, title: str, description: str, manifest: list[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / filename
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    manifest.append({
        "filename": filename,
        "title": title,
        "description": description,
        "path": str(out),
    })


def pct_label(value: float) -> str:
    if pd.isna(value):
        return ""
    return f"{value * 100:.1f}%"


def read_csv_if_exists(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, **kwargs)


def plot_exports2_dataset_size(summary: pd.DataFrame, output_dir: Path, manifest: list[dict]) -> None:
    df = summary.copy()
    labels = df["dataset_key"].astype(str).tolist()
    x = np.arange(len(labels))
    width = 0.36

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    bars1 = ax.bar(x - width / 2, df["publication_records"], width, label="Publication", color="#2B6CB0")
    bars2 = ax.bar(x + width / 2, df["family_records"], width, label="Family", color="#90CDF4")
    ax.set_title("exports2 データ規模", fontsize=15, fontweight="bold")
    ax.set_ylabel("件数")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    ax.bar_label(bars1, labels=[f"{int(v):,}" for v in df["publication_records"]], padding=3, fontsize=9)
    ax.bar_label(bars2, labels=[f"{int(v):,}" for v in df["family_records"]], padding=3, fontsize=9)
    ax.set_ylim(0, max(df["publication_records"].max(), df["family_records"].max()) * 1.18)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig01_exports2_dataset_size.png",
        "exports2 データ規模",
        "C0/C1/S0/S1のpublication件数とfamily件数を比較する図。",
        manifest,
    )


def plot_exports2_text_coverage(summary: pd.DataFrame, output_dir: Path, manifest: list[dict]) -> None:
    cols = ["title_nonempty_rate", "abstract_nonempty_rate", "claims_nonempty_rate"]
    labels = ["Title", "Abstract", "Claims"]
    df = summary.set_index("dataset_key")[cols]

    fig, ax = plt.subplots(figsize=(9.5, 5.3))
    x = np.arange(len(df.index))
    width = 0.24
    palette = ["#2B6CB0", "#38A169", "#DD6B20"]
    for i, (col, label) in enumerate(zip(cols, labels)):
        bars = ax.bar(x + (i - 1) * width, df[col], width, label=label, color=palette[i])
        ax.bar_label(bars, labels=[pct_label(v) for v in df[col]], padding=3, fontsize=8)
    ax.set_title("Title / Abstract / Claims の取得率", fontsize=15, fontweight="bold")
    ax.set_ylabel("非空率")
    ax.set_ylim(0, 1.12)
    ax.set_xticks(x)
    ax.set_xticklabels(df.index.tolist())
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig02_exports2_text_coverage.png",
        "テキスト取得率",
        "Title/Abstract/Claimsの非空率。抽出・ベクトル化の入力品質確認に使う。",
        manifest,
    )


def plot_exports2_vector_empty(vector_summary: pd.DataFrame, output_dir: Path, manifest: list[dict]) -> None:
    df = vector_summary.copy()
    if df.empty:
        return
    df["empty_rate"] = df["empty_texts"] / df["input_records"].replace(0, np.nan)
    pivot = df.pivot(index="dataset_id", columns="embedding_type", values="empty_rate").fillna(0)
    order = [c for c in ["problem", "solution", "fulltext"] if c in pivot.columns]
    pivot = pivot[order]

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    x = np.arange(len(pivot.index))
    width = 0.24
    palette = ["#2B6CB0", "#DD6B20", "#805AD5"]
    for i, col in enumerate(pivot.columns):
        bars = ax.bar(x + (i - (len(pivot.columns) - 1) / 2) * width, pivot[col], width, label=col, color=palette[i])
        ax.bar_label(bars, labels=[pct_label(v) for v in pivot[col]], padding=3, fontsize=8)
    ax.set_title("ベクトル化対象テキストの空欄率", fontsize=15, fontweight="bold")
    ax.set_ylabel("空欄率")
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index.tolist())
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3)
    ymax = max(0.08, float(pivot.max().max()) * 1.35)
    ax.set_ylim(0, ymax)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig03_exports2_vector_empty_rate.png",
        "ベクトル化空欄率",
        "problem/solution/fulltextごとの空欄率。context抽出の安定性確認に使う。",
        manifest,
    )


def plot_exports2_top_candidates(ranking: pd.DataFrame, output_dir: Path, manifest: list[dict]) -> None:
    if ranking.empty:
        return
    df = ranking.head(20).copy()
    df["label"] = df["rank"].astype(int).astype(str) + ". " + df["source_publication_number"].astype(str)
    df = df.iloc[::-1]

    fig, ax = plt.subplots(figsize=(10.5, 8))
    colors = df["source_dataset_id"].map(COLORS).fillna("#4A5568")
    bars = ax.barh(df["label"], df["heterogeneous_score_a"], color=colors)
    ax.set_title("異分野候補ランキング Top20", fontsize=15, fontweight="bold")
    ax.set_xlabel("Heterogeneous Score A")
    ax.grid(axis="x", alpha=0.25)
    ax.bar_label(bars, labels=[f"{v:.3f}" for v in df["heterogeneous_score_a"]], padding=3, fontsize=8)
    from matplotlib.patches import Patch

    handles = [
        Patch(facecolor=COLORS["C0"], label="C0"),
        Patch(facecolor=COLORS["C1"], label="C1"),
    ]
    ax.legend(handles=handles, frameon=False, loc="lower right")
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig04_exports2_top20_heterogeneous_candidates.png",
        "異分野候補Top20",
        "problem similarityとsolution差分から算出した異分野候補の上位20件。",
        manifest,
    )


def plot_exports2_similarity_scatter(ranking: pd.DataFrame, output_dir: Path, manifest: list[dict]) -> None:
    if ranking.empty:
        return
    df = ranking.head(5000).copy()
    fig, ax = plt.subplots(figsize=(8.2, 6.5))
    sc = ax.scatter(
        df["problem_similarity"],
        df["solution_similarity"],
        c=df["heterogeneous_score_a"],
        s=18,
        cmap="viridis",
        alpha=0.55,
        edgecolors="none",
    )
    ax.set_title("問題類似度と解決策類似度の関係", fontsize=15, fontweight="bold")
    ax.set_xlabel("Problem similarity")
    ax.set_ylabel("Solution similarity")
    ax.axvline(df["problem_similarity"].quantile(0.75), color="#2D3748", linestyle="--", linewidth=1, alpha=0.7)
    ax.axhline(df["solution_similarity"].median(), color="#2D3748", linestyle=":", linewidth=1, alpha=0.7)
    ax.grid(alpha=0.22)
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("Heterogeneous Score A")
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig05_exports2_problem_solution_scatter_top5000.png",
        "問題類似度・解決策類似度散布図",
        "上位5000候補について、課題の近さと解決策の違いを同時に見る図。",
        manifest,
    )


def plot_exports2_score_components(ranking: pd.DataFrame, output_dir: Path, manifest: list[dict]) -> None:
    if ranking.empty:
        return
    df = ranking.head(15).copy()
    labels = df["rank"].astype(int).astype(str) + ". " + df["source_publication_number"].astype(str)
    x = np.arange(len(df))
    width = 0.28

    fig, ax = plt.subplots(figsize=(12.5, 5.8))
    ax.bar(x - width, df["problem_similarity"], width, label="Problem sim.", color="#2B6CB0")
    ax.bar(x, 1 - df["solution_similarity"], width, label="1 - Solution sim.", color="#DD6B20")
    ax.bar(x + width, df["heterogeneous_score_a"], width, label="Score A", color="#38A169")
    ax.set_title("異分野スコアの構成要素 Top15", fontsize=15, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
    ax.set_ylabel("値")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig06_exports2_score_components_top15.png",
        "異分野スコア構成要素",
        "Top15候補について、problem similarity、解決策差分、最終スコアを並べる図。",
        manifest,
    )


def plot_exports2_s1_known_positive(s1_summary: pd.DataFrame, output_dir: Path, manifest: list[dict]) -> None:
    if s1_summary.empty:
        return
    cols = [
        "similarity_to_s0_problem_centroid",
        "similarity_to_c1_problem_centroid",
        "nearest_s0_problem_similarity",
    ]
    existing = [c for c in cols if c in s1_summary.columns]
    if not existing:
        return

    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    data = [pd.to_numeric(s1_summary[c], errors="coerce").dropna() for c in existing]
    labels = ["S0 centroid", "C1 centroid", "Nearest S0"][: len(existing)]
    box = ax.boxplot(data, labels=labels, patch_artist=True, showmeans=True)
    for patch, color in zip(box["boxes"], ["#DD6B20", "#805AD5", "#38A169"]):
        patch.set_facecolor(color)
        patch.set_alpha(0.65)
    ax.set_title("S1既知正例の類似度分布", fontsize=15, fontweight="bold")
    ax.set_ylabel("Similarity")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig07_exports2_s1_known_positive_similarity.png",
        "S1既知正例チェック",
        "S1既知正例がS0/C1の問題空間でどの程度近いかを確認する図。",
        manifest,
    )


def plot_exports2_source_share(ranking: pd.DataFrame, output_dir: Path, manifest: list[dict]) -> None:
    if ranking.empty:
        return
    rows = []
    for k in [20, 50, 100, 500, 1000]:
        top = ranking.head(k)
        counts = top["source_dataset_id"].value_counts()
        for dataset_id, count in counts.items():
            rows.append({"top_k": f"Top{k}", "source_dataset_id": dataset_id, "count": int(count)})
    df = pd.DataFrame(rows)
    if df.empty:
        return
    pivot = df.pivot(index="top_k", columns="source_dataset_id", values="count").fillna(0)
    pivot = pivot.reindex([f"Top{k}" for k in [20, 50, 100, 500, 1000]])

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    bottom = np.zeros(len(pivot))
    for col in pivot.columns:
        vals = pivot[col].to_numpy()
        ax.bar(pivot.index, vals, bottom=bottom, label=col, color=COLORS.get(col, "#718096"))
        bottom += vals
    ax.set_title("候補ランキングにおける source dataset 構成", fontsize=15, fontweight="bold")
    ax.set_ylabel("候補件数")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig08_exports2_source_dataset_share.png",
        "候補source構成",
        "Top-k候補にC0/C1がどの程度含まれるかを確認する図。",
        manifest,
    )


def read_year_counts(path: Path, dataset_key: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["dataset_key", "year", "count"])
    chunks = []
    for chunk in pd.read_csv(path, usecols=["year"], chunksize=250_000):
        year = pd.to_numeric(chunk["year"], errors="coerce").dropna().astype(int)
        counts = year.value_counts().rename_axis("year").reset_index(name="count")
        chunks.append(counts)
    if not chunks:
        return pd.DataFrame(columns=["dataset_key", "year", "count"])
    df = pd.concat(chunks, ignore_index=True).groupby("year", as_index=False)["count"].sum()
    df["dataset_key"] = dataset_key
    return df[["dataset_key", "year", "count"]]


def plot_exports2_year_trend(output_dir: Path, manifest: list[dict]) -> None:
    paths = {
        "C0": EXPORTS2_PROCESSED_DIR / "C0_publication_level.csv",
        "C1": EXPORTS2_PROCESSED_DIR / "C1_publication_level.csv",
        "S0": EXPORTS2_PROCESSED_DIR / "S0_publication_level.csv",
        "S1": EXPORTS2_PROCESSED_DIR / "S1_publication_level.csv",
    }
    df = pd.concat([read_year_counts(path, key) for key, path in paths.items()], ignore_index=True)
    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    for key, group in df.groupby("dataset_key"):
        group = group.sort_values("year")
        ax.plot(group["year"], group["count"], marker="o", linewidth=2.0, label=key, color=COLORS.get(key, None))
    ax.set_title("exports2 出願年別Publication件数", fontsize=15, fontweight="bold")
    ax.set_xlabel("出願年")
    ax.set_ylabel("Publication件数")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, ncol=4)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig09_exports2_filing_year_trend.png",
        "出願年トレンド",
        "C0/C1/S0/S1の年次件数推移。分析対象期間とデータ偏りの説明に使う。",
        manifest,
    )


def plot_ab_field_similarity(output_dir: Path, manifest: list[dict]) -> None:
    path = FULL_PROCESSED_DIR / "similarity" / "field_level_similarity_summary_full.csv"
    df = read_csv_if_exists(path)
    if df.empty:
        return
    row = df.iloc[0]
    labels = ["Problem", "Solution", "Full text"]
    values = [
        row.get("problem_field_similarity", np.nan),
        row.get("solution_field_similarity", np.nan),
        row.get("fulltext_field_similarity", np.nan),
    ]
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    bars = ax.bar(labels, values, color=["#2B6CB0", "#DD6B20", "#805AD5"])
    ax.bar_label(bars, labels=[f"{v:.3f}" for v in values], padding=3)
    ax.set_ylim(0, 1.05)
    ax.set_title("A0/B0 分野レベル類似度", fontsize=15, fontweight="bold")
    ax.set_ylabel("Cosine similarity")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig10_ab_full_field_similarity.png",
        "A0/B0分野類似度",
        "problem/solution/fulltextごとのA0-B0分野レベル類似度。",
        manifest,
    )


def plot_ab_gapscore_top10(output_dir: Path, manifest: list[dict]) -> None:
    path = FULL_PROCESSED_DIR / "ranking" / "method_gap_ranking_all_full.csv"
    df = read_csv_if_exists(path)
    if df.empty:
        return
    df = df.head(10).copy().iloc[::-1]
    label_col = "method_display" if "method_display" in df.columns else "method"
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df[label_col], df["gap_score_v2"], color="#2B6CB0")
    ax.bar_label(bars, labels=[f"{v:.4f}" for v in df["gap_score_v2"]], padding=3, fontsize=8)
    ax.set_title("GapScore v2 ランキング Top10", fontsize=15, fontweight="bold")
    ax.set_xlabel("gap_score_v2")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig11_ab_full_gapscore_v2_top10.png",
        "GapScore v2 Top10",
        "A0で高くB0で低い手法を、positive_gapを使ったv2スコアで並べた図。",
        manifest,
    )


def plot_ab_specific_methods(output_dir: Path, manifest: list[dict]) -> None:
    path = FULL_PROCESSED_DIR / "ranking" / "method_gap_ranking_specific_methods_full.csv"
    df = read_csv_if_exists(path)
    if df.empty:
        return
    df = df.sort_values("gap_score_v2", ascending=True).copy()
    label_col = "method_display" if "method_display" in df.columns else "method"
    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(9, max(4.5, 0.42 * len(df))))
    ax.barh(y - 0.16, df["A_pre_rate"], height=0.32, label="A0 pre rate", color="#1F77B4")
    ax.barh(y + 0.16, df["B_pre_rate"], height=0.32, label="B0 pre rate", color="#D62728")
    ax.set_yticks(y)
    ax.set_yticklabels(df[label_col])
    ax.set_title("具体手法候補のA0/B0出現率", fontsize=15, fontweight="bold")
    ax.set_xlabel("出現率")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig12_ab_full_specific_method_rates.png",
        "具体手法候補の出現率",
        "U-Net/CNN/GANなど具体手法候補についてA0/B0のpre期間出現率を比較する図。",
        manifest,
    )


def plot_ab_future_growth(output_dir: Path, manifest: list[dict]) -> None:
    path = FULL_PROCESSED_DIR / "ranking" / "method_gap_ranking_with_future_full.csv"
    df = read_csv_if_exists(path)
    if df.empty:
        return
    df = df.head(12).copy()
    label_col = "method_display" if "method_display" in df.columns else "method"
    x = np.arange(len(df))
    width = 0.36
    fig, ax = plt.subplots(figsize=(12, 5.8))
    ax.bar(x - width / 2, df["B_pre_rate"], width, label="B0 pre", color="#A0AEC0")
    ax.bar(x + width / 2, df["B_future_rate"], width, label="B0 future", color="#38A169")
    ax.set_xticks(x)
    ax.set_xticklabels(df[label_col], rotation=45, ha="right")
    ax.set_title("B0における将来期間の出現率変化", fontsize=15, fontweight="bold")
    ax.set_ylabel("出現率")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig13_ab_full_future_growth_top12.png",
        "B0将来期間の伸び",
        "GapScore v2上位手法について、B0で将来期間に増えたかを確認する図。",
        manifest,
    )


def plot_ab_unet_check(output_dir: Path, manifest: list[dict]) -> None:
    path = FULL_PROCESSED_DIR / "ranking" / "unet_ranking_check_full.csv"
    df = read_csv_if_exists(path)
    if df.empty:
        return
    row = df.iloc[0]
    labels = ["A0 pre", "B0 pre", "B0 future"]
    values = [row.get("A_pre_rate", 0), row.get("B_pre_rate", 0), row.get("B_future_rate", 0)]
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    bars = ax.bar(labels, values, color=["#1F77B4", "#D62728", "#38A169"])
    ax.bar_label(bars, labels=[pct_label(v) for v in values], padding=3)
    ax.set_title(f"U-Netランキング確認: rank {int(row.get('rank', 0))}", fontsize=15, fontweight="bold")
    ax.set_ylabel("出現率")
    ax.grid(axis="y", alpha=0.25)
    ymax = max(values) * 1.35 if max(values) > 0 else 0.05
    ax.set_ylim(0, ymax)
    fig.tight_layout()
    save_figure(
        fig,
        output_dir,
        "fig14_ab_full_unet_ranking_check.png",
        "U-Netランキング確認",
        "U-NetのA0/B0 pre出現率とB0 future出現率を比較し、既知の将来出現を確認する図。",
        manifest,
    )


def write_readme(output_dir: Path, manifest: list[dict]) -> None:
    lines = [
        "# Thesis Figures",
        "",
        "卒論本文・発表資料に貼るための図一覧です。",
        "",
        "| No. | File | Title | Description |",
        "|---:|---|---|---|",
    ]
    for i, row in enumerate(manifest, start=1):
        lines.append(f"| {i} | `{row['filename']}` | {row['title']} | {row['description']} |")
    (output_dir / "thesis_figures_readme.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    pd.DataFrame(manifest).to_csv(output_dir / "figure_manifest.csv", index=False, encoding="utf-8")

    tex_lines = [
        "% 卒論本文に貼るためのfigure環境スニペット",
        "% 必要な図だけ本文側に移してください。",
        "",
    ]
    for i, row in enumerate(manifest, start=1):
        stem = Path(row["filename"]).stem.replace("_", "-")
        tex_lines.extend([
            "\\begin{figure}[tbp]",
            "  \\centering",
            f"  \\includegraphics[width=0.92\\linewidth]{{pipeline/outputs/thesis_figures/{row['filename']}}}",
            f"  \\caption{{{row['title']}。{row['description']}}}",
            f"  \\label{{fig:{stem}}}",
            "\\end{figure}",
            "",
        ])
    (output_dir / "thesis_figures_includegraphics.tex").write_text("\n".join(tex_lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    logger = setup_logger()
    setup_font(logger)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    summary = read_csv_if_exists(HET_OUTPUT_DIR / "dataset_summary.csv")
    vector_summary = read_csv_if_exists(HET_OUTPUT_DIR / "vectorization_summary.csv")
    ranking = read_csv_if_exists(HET_OUTPUT_DIR / "heterogeneous_candidate_ranking.csv")
    s1_summary = read_csv_if_exists(HET_OUTPUT_DIR / "s1_known_positive_summary.csv")

    if not summary.empty:
        plot_exports2_dataset_size(summary, output_dir, manifest)
        plot_exports2_text_coverage(summary, output_dir, manifest)
    plot_exports2_vector_empty(vector_summary, output_dir, manifest)
    plot_exports2_top_candidates(ranking, output_dir, manifest)
    plot_exports2_similarity_scatter(ranking, output_dir, manifest)
    plot_exports2_score_components(ranking, output_dir, manifest)
    plot_exports2_s1_known_positive(s1_summary, output_dir, manifest)
    plot_exports2_source_share(ranking, output_dir, manifest)
    plot_exports2_year_trend(output_dir, manifest)

    plot_ab_field_similarity(output_dir, manifest)
    plot_ab_gapscore_top10(output_dir, manifest)
    plot_ab_specific_methods(output_dir, manifest)
    plot_ab_future_growth(output_dir, manifest)
    plot_ab_unet_check(output_dir, manifest)

    write_readme(output_dir, manifest)
    logger.info("created %d figures: %s", len(manifest), output_dir)


if __name__ == "__main__":
    main()
