#!/usr/bin/env python3
from __future__ import annotations

import math
import os
import shutil
import textwrap
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-sotsuron-cache")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/sotsuron-xdg-cache")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "pipeline/outputs/thesis_figures_tables"
FIG_DIR = OUT_DIR / "figures"
TABLE_DIR = OUT_DIR / "tables"
ROOT_FIG_DIR = PROJECT_ROOT / "figures"
ROOT_TABLE_DIR = PROJECT_ROOT / "tables"

P1 = PROJECT_ROOT / "pipeline/outputs/experiment1_data_bundle/outputs"
P2 = PROJECT_ROOT / "pipeline/outputs/experiment2_heterogeneous_bundle/outputs"
TABLE_SOURCE = PROJECT_ROOT / "pipeline/outputs/tables"

LABEL_MAP = {"◎": "◎ 強い候補", "○": "○ 妥当候補", "△": "△ 弱い候補", "×": "× 不適切候補"}
LABEL_ORDER = ["◎", "○", "△", "×"]
LABEL_COLORS = {
    "◎ 強い候補": "#2b8cbe",
    "○ 妥当候補": "#7bccc4",
    "△ 弱い候補": "#fdae61",
    "× 不適切候補": "#d7191c",
}

plt.rcParams.update(
    {
        "font.family": "Hiragino Sans",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 140,
        "savefig.dpi": 240,
    }
)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    ROOT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    ROOT_TABLE_DIR.mkdir(parents=True, exist_ok=True)


def save_figure(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def box(ax, xy, width, height, text, fc="#eef5fb", ec="#3a6ea5", fontsize=10):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=1.4,
        edgecolor=ec,
        facecolor=fc,
    )
    ax.add_patch(patch)
    wrapped = "\n".join(textwrap.wrap(text, 22))
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        wrapped,
        ha="center",
        va="center",
        fontsize=fontsize,
        color="#1d2b36",
    )
    return patch


def arrow(ax, start, end, color="#555555"):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=16,
            linewidth=1.4,
            color=color,
            shrinkA=4,
            shrinkB=4,
        )
    )


def draw_linear_pipeline(name: str, title: str, steps: list[str], colors: list[str] | None = None) -> None:
    fig, ax = plt.subplots(figsize=(14, 2.5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.02, 0.85, title, fontsize=15, fontweight="bold", ha="left", va="center")
    n = len(steps)
    width = 0.88 / n
    colors = colors or ["#eef5fb"] * n
    y = 0.35
    for i, step in enumerate(steps):
        x = 0.05 + i * width
        box(ax, (x, y), width * 0.82, 0.20, step, fc=colors[i % len(colors)], fontsize=8)
        if i < n - 1:
            arrow(ax, (x + width * 0.82, y + 0.10), (x + width * 0.95, y + 0.10))
    save_figure(fig, name)


def fig_framework_overview() -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.04, 0.94, "課題・解決手段分離に基づくクロスドメイン技術候補抽出", fontsize=16, fontweight="bold")

    box(ax, (0.05, 0.68), 0.23, 0.16, "特許文書\nTitle / Abstract / Claims", "#f4f4f4", "#666666")
    box(ax, (0.38, 0.68), 0.23, 0.16, "LLM文脈抽出\n課題 / 解決手段 / 技術手段", "#edf8fb", "#2b8cbe")
    box(ax, (0.72, 0.68), 0.23, 0.16, "候補ランキング\n類似度 + 時系列条件", "#f0f9e8", "#4d9221")
    arrow(ax, (0.28, 0.76), (0.38, 0.76))
    arrow(ax, (0.61, 0.76), (0.72, 0.76))

    box(ax, (0.16, 0.36), 0.28, 0.17, "実験1（主分析）\nU-Net候補抽出\nA0 -> B0", "#fff7bc", "#d95f0e")
    box(ax, (0.57, 0.36), 0.28, 0.17, "実験2（補助分析）\n洗浄・除去系候補\nS0/C1 -> S1", "#fee8c8", "#e34a33")
    arrow(ax, (0.50, 0.68), (0.30, 0.53))
    arrow(ax, (0.50, 0.68), (0.71, 0.53))

    box(ax, (0.30, 0.10), 0.40, 0.13, "LLM支援付き著者確認評価\n専門家確認候補としての解釈可能性", "#f7f7f7", "#525252")
    arrow(ax, (0.30, 0.36), (0.43, 0.23))
    arrow(ax, (0.71, 0.36), (0.57, 0.23))
    save_figure(fig, "framework_overview")


def fig_solution_type_quadrant() -> None:
    fig, ax = plt.subplots(figsize=(10, 9))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    
    # 背景に象限の色を付ける（透明度0.1）
    ax.add_patch(plt.Rectangle((0, 0.5), 0.5, 0.5, facecolor="#e8f1f5", edgecolor="none", zorder=0))  # 左上：淡青
    ax.add_patch(plt.Rectangle((0.5, 0.5), 0.5, 0.5, facecolor="#e8f8f1", edgecolor="none", zorder=0))  # 右上：淡緑
    ax.add_patch(plt.Rectangle((0, 0), 0.5, 0.5, facecolor="#f0ebe8", edgecolor="none", zorder=0))  # 左下：淡灰
    ax.add_patch(plt.Rectangle((0.5, 0), 0.5, 0.5, facecolor="#ffe8d6", edgecolor="none", zorder=0))  # 右下：淡橙
    
    # グリッド線（中央）
    ax.axhline(0.5, color="#666666", linewidth=2, linestyle="-", zorder=1)
    ax.axvline(0.5, color="#666666", linewidth=2, linestyle="-", zorder=1)
    
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.5)
    ax.spines["bottom"].set_linewidth(1.5)
    
    # 軸ラベル
    ax.set_xlabel("課題文脈の類似度（低 → 高）", fontsize=13, fontweight="bold", labelpad=12)
    ax.set_ylabel("解決手段文脈の類似度（低 → 高）", fontsize=13, fontweight="bold", labelpad=12)
    
    # 象限ラベル（大きく、見やすく）
    ax.text(0.25, 0.75, "解決手段類似型", fontsize=14, fontweight="bold", ha="center", color="#555555")
    ax.text(0.75, 0.75, "近接解決策型\n（実験1）", fontsize=14, fontweight="bold", ha="center", color="#1a5490")
    ax.text(0.25, 0.25, "低関連", fontsize=14, fontweight="bold", ha="center", color="#555555")
    ax.text(0.75, 0.25, "異質解決策型\n（実験2）", fontsize=14, fontweight="bold", ha="center", color="#a85a1a")
    
    ax.set_title("候補タイプと実験の位置づけ", fontsize=16, fontweight="bold", pad=20)
    
    plt.tight_layout()
    save_figure(fig, "solution_type_quadrant")


def fig_method_pipeline() -> None:
    draw_linear_pipeline(
        "method_pipeline",
        "提案手法の全体処理フロー",
        [
            "特許データ",
            "ファミリー単位整理",
            "課題/解決手段分離",
            "ベクトル化とランキング",
            "候補集合",
            "著者確認評価",
            "卒論用図表",
        ],
        ["#f7f7f7", "#edf8fb", "#edf8fb", "#f0f9e8", "#fff7bc", "#fee8c8", "#f7f7f7"],
    )


def fig_experiment1_pipeline() -> None:
    draw_linear_pipeline(
        "experiment1_pipeline",
        "実験1フロー：U-Netを対象とした近接解決策型",
        [
            "A0/A1\n医療画像解析",
            "B0/B1\n製造欠陥検出",
            "過去/将来期間分割",
            "U-Net候補抽出",
            "ベースライン比較",
            "著者確認評価",
        ],
        ["#edf8fb", "#edf8fb", "#fff7bc", "#f0f9e8", "#fee8c8", "#f7f7f7"],
    )


def fig_experiment1_unet_trend() -> None:
    df = read_csv(TABLE_SOURCE / "method_counts_by_year.csv")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    if df.empty or "is_unet" not in df.columns:
        ax.text(0.5, 0.5, "U-Net年次データが見つかりません", ha="center", va="center")
    else:
        for domain, group in df.groupby("domain"):
            group = group.sort_values("year")
            ax.plot(group["year"], group["is_unet"], marker="o", linewidth=2.2, label=f"{domain}: U-Net関連特許数")
        ax.set_xlabel("出願・公開年")
        ax.set_ylabel("U-Net関連特許数")
        ax.legend(frameon=False)
        ax.grid(axis="y", alpha=0.25)
    ax.set_title("実験1：U-Net関連特許の年次推移", fontsize=14, fontweight="bold")
    save_figure(fig, "experiment1_unet_trend")


def fig_experiment1_baseline_comparison() -> None:
    df = read_csv(P1 / "final_candidate_type_summary.csv")
    fig, ax = plt.subplots(figsize=(11, 5.5))
    if df.empty:
        ax.text(0.5, 0.5, "実験1集計データが見つかりません", ha="center", va="center")
    else:
        label_map = {
            "proposed_top": "提案手法",
            "fulltext_top_baseline": "全文類似\n上位ベースライン",
        }
        df = df[df["group_value"].isin(label_map)].copy()
        df["label"] = df["group_value"].map(label_map)
        df = df.sort_values("group_value", ascending=False)
        labels = df["label"].tolist()
        x = np.arange(len(df))
        ax.bar(x - 0.18, df["candidate_score_mean"], width=0.36, label="候補平均スコア", color="#2b8cbe")
        ax2 = ax.twinx()
        ax2.bar(x + 0.18, df["valid_candidate_rate_score_ge_2"], width=0.36, label="妥当候補率", color="#fdae61")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=0, fontsize=8)
        ax.set_ylim(0, 3.2)
        ax2.set_ylim(0, 1.05)
        ax.set_ylabel("候補平均スコア")
        ax2.set_ylabel("妥当候補率")
        handles1, labels1 = ax.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(handles1 + handles2, labels1 + labels2, frameon=False, loc="upper right")
        ax.grid(axis="y", alpha=0.25)
    fig.text(
        0.5,
        0.01,
        "補助比較：単純な勝敗ではなく、候補集合の性質差を確認する。",
        ha="center",
        va="bottom",
        fontsize=9,
        color="#555555",
    )
    ax.set_title("実験1：提案手法と全文類似上位ベースライン", fontsize=14, fontweight="bold")
    save_figure(fig, "experiment1_baseline_comparison")


def fig_experiment2_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(13, 5.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.02, 0.94, "実験2フロー：異質解決策型の補助分析", fontsize=15, fontweight="bold")
    steps = [
        ("S1既知事例", "#edf8fb"),
        ("7用途クラスタ", "#edf8fb"),
        ("C1非半導体系\npre候補", "#fff7bc"),
        ("クラスタ別\nランキング", "#f0f9e8"),
        ("各クラスタ上位20件\n7クラスタ分", "#f0f9e8"),
        ("ファミリー単位\n重複統合", "#fff7bc"),
        ("46件の\nユニークファミリー", "#fee8c8"),
        ("LLM支援付き\n著者確認評価", "#fee8c8"),
    ]
    positions = [
        (0.04, 0.64), (0.29, 0.64), (0.54, 0.64), (0.79, 0.64),
        (0.79, 0.30), (0.54, 0.30), (0.29, 0.30), (0.04, 0.30),
    ]
    w, h = 0.17, 0.18
    for i, ((text, color), pos) in enumerate(zip(steps, positions)):
        box(ax, pos, w, h, text, fc=color, fontsize=9)
        if i < len(steps) - 1:
            sx, sy = pos[0] + w, pos[1] + h / 2
            nx, ny = positions[i + 1][0], positions[i + 1][1] + h / 2
            if i == 3:
                sx, sy = pos[0] + w / 2, pos[1]
                nx, ny = positions[i + 1][0] + w / 2, positions[i + 1][1] + h
            elif i > 3:
                sx, sy = pos[0], pos[1] + h / 2
                nx, ny = positions[i + 1][0] + w, positions[i + 1][1] + h / 2
            arrow(ax, (sx, sy), (nx, ny))
    ax.text(
        0.50,
        0.10,
        "目的：技術導入可能性の証明ではなく、専門家確認候補を抽出する。",
        ha="center",
        va="center",
        fontsize=10,
        color="#555555",
    )
    save_figure(fig, "experiment2_pipeline")


def fig_experiment2_label_distribution() -> None:
    df = read_csv(P2 / "heterogeneous_manual_review_final_strict.csv")
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    if df.empty or "human_label" not in df.columns:
        ax.text(0.5, 0.5, "実験2評価ラベルが見つかりません", ha="center", va="center")
    else:
        counts = df["human_label"].value_counts()
        labels = [LABEL_MAP[k] for k in LABEL_ORDER]
        values = [int(counts.get(k, 0)) for k in LABEL_ORDER]
        colors = [LABEL_COLORS[l] for l in labels]
        ax.bar(labels, values, color=colors)
        for i, v in enumerate(values):
            ax.text(i, v + 0.4, str(v), ha="center", va="bottom")
        ax.set_ylabel("ファミリー数")
        ax.grid(axis="y", alpha=0.25)
    ax.set_title("実験2：評価ラベル分布", fontsize=14, fontweight="bold")
    save_figure(fig, "experiment2_label_distribution")


def fig_experiment2_cluster_distribution() -> None:
    df = read_csv(P2 / "heterogeneous_manual_review_by_cluster.csv")
    fig, ax = plt.subplots(figsize=(11, 6))
    if df.empty:
        ax.text(0.5, 0.5, "実験2クラスタ集計が見つかりません", ha="center", va="center")
    else:
        df = df.sort_values("strong_or_plausible_rate_◎○", ascending=True)
        y = np.arange(len(df))
        left = np.zeros(len(df))
        for raw in LABEL_ORDER:
            col = f"label_{raw}_count"
            values = df[col].fillna(0).astype(int).values if col in df.columns else np.zeros(len(df))
            label = LABEL_MAP[raw]
            ax.barh(y, values, left=left, label=label, color=LABEL_COLORS[label])
            left += values
        ax.set_yticks(y)
        cluster_map = {
            "adhesive_cleaning": "接着剤洗浄",
            "circuit_board_cleaning": "回路基板洗浄",
            "cmp_polishing_post_cleaning": "CMP後洗浄",
            "flux_electronic_component_cleaning": "フラックス・\n電子部品洗浄",
            "photoresist_resin_mask_removal": "フォトレジスト・\n樹脂除去",
            "semiconductor_substrate_cleaning": "半導体基板洗浄",
            "silicon_wafer_cleaning": "シリコンウェーハ洗浄",
        }
        ax.set_yticklabels([cluster_map.get(str(x), str(x).replace("_", "\n")) for x in df["cluster"]], fontsize=8)
        ax.set_xlabel("評価対象ファミリー数")
        ax.legend(frameon=False, ncol=4, loc="lower right")
        ax.grid(axis="x", alpha=0.25)
    ax.set_title("実験2：クラスタ別評価ラベル分布", fontsize=14, fontweight="bold")
    save_figure(fig, "experiment2_cluster_distribution")


def fig_experiment2_fulltext_overlap() -> None:
    df = read_csv(P2 / "proposed_vs_fulltext_overlap.csv")
    fig, ax = plt.subplots(figsize=(8.5, 5))
    if df.empty:
        ax.text(0.5, 0.5, "ベースライン比較データが見つかりません", ha="center", va="center")
    else:
        overall = df[df["level"] == "overall"].set_index("metric")["value"].to_dict()
        metrics = ["overlap_family_count", "proposed_only_count", "fulltext_only_count"]
        labels = ["重複", "提案手法のみ", "ベースラインのみ"]
        values = [int(overall.get(m, 0)) for m in metrics]
        colors = ["#2b8cbe", "#fdae61", "#bdbdbd"]
        ax.bar(labels, values, color=colors)
        for i, v in enumerate(values):
            ax.text(i, v + 0.6, str(v), ha="center", va="bottom")
        ax.set_ylabel("ユニークファミリー数")
        ax.grid(axis="y", alpha=0.25)
    fig.text(
        0.5,
        0.01,
        "補助比較：厳密なBERT型全文埋め込みではなく、軽量全文テキストベースラインを用いる。",
        ha="center",
        va="bottom",
        fontsize=9,
        color="#555555",
    )
    ax.set_title("実験2：提案手法と軽量全文テキストベースラインの比較", fontsize=14, fontweight="bold")
    save_figure(fig, "experiment2_fulltext_overlap")


def latex_escape(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def fmt(value: object) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        if abs(value) <= 1:
            return f"{value:.3f}"
        return f"{value:.2f}"
    return str(value)


def write_tex_table(df: pd.DataFrame, path: Path, caption: str, label: str) -> None:
    col_spec = "l" * len(df.columns)
    lines = [
        r"\begin{table}[tbp]",
        r"\centering",
        r"\small",
        rf"\caption{{{latex_escape(caption)}}}",
        rf"\label{{{latex_escape(label)}}}",
        rf"\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        " & ".join(latex_escape(c) for c in df.columns) + r" \\",
        r"\midrule",
    ]
    for _, row in df.iterrows():
        lines.append(" & ".join(latex_escape(fmt(v)) for v in row.tolist()) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def make_tables() -> None:
    dataset = read_csv(TABLE_SOURCE / "dataset_summary.csv")
    if not dataset.empty:
        df = dataset[["domain", "level", "total_records", "past_records", "future_records", "is_unet_rate"]].copy()
        df.columns = ["分野", "レベル", "合計", "過去", "将来", "U-Net率"]
        write_tex_table(df, TABLE_DIR / "dataset_summary.tex", "実験1のデータセットサマリー", "tab:dataset_summary")

    extraction_fields = pd.DataFrame(
        [
            ["problem_context", "特許文書から抽出された問題、目的、または技術的課題"],
            ["solution_context", "問題を解決するために提案された構成、プロセス、または方法"],
            ["technical_means", "名付けられた技術、モデル、材料、組成、または操作"],
            ["target_object", "方法が適用されるオブジェクト"],
            ["effect_context", "特許で説明されている期待される効果または改善"],
        ],
        columns=["フィールド", "定義"],
    )
    write_tex_table(extraction_fields, TABLE_DIR / "extraction_fields.tex", "候補レビューで使用される抽出フィールド", "tab:extraction_fields")

    exp1_method = read_csv(P1 / "final_method_comparison_summary.csv")
    if not exp1_method.empty:
        df = exp1_method[exp1_method["group_type"] == "proposed_or_baseline"][
            ["group_value", "count", "candidate_score_mean", "valid_candidate_rate_score_ge_2", "representative_flag_count"]
        ].copy()
        df.columns = ["グループ", "件数", "平均スコア", "妥当性率", "代表的フラグ"]
        write_tex_table(df, TABLE_DIR / "experiment1_results.tex", "実験1の著者確認評価サマリー", "tab:experiment1_results")

    exp1_candidate = read_csv(P1 / "final_candidate_type_summary.csv")
    if not exp1_candidate.empty:
        df = exp1_candidate[
            ["group_value", "count", "candidate_score_mean", "valid_candidate_rate_score_ge_2", "label_◎", "label_○", "label_△", "label_×"]
        ].copy()
        df.columns = ["候補タイプ", "件数", "平均スコア", "妥当性率", "強い", "妥当", "弱い", "不適切"]
        write_tex_table(df, TABLE_DIR / "experiment1_baseline_comparison.tex", "実験1ベースライン比較", "tab:experiment1_baseline_comparison")

    exp2_final = read_csv(P2 / "heterogeneous_manual_review_final_strict.csv")
    if not exp2_final.empty:
        counts = exp2_final["human_label"].value_counts()
        df = pd.DataFrame(
            [[LABEL_MAP[k], int(counts.get(k, 0))] for k in LABEL_ORDER],
            columns=["ラベル", "件数"],
        )
        write_tex_table(df, TABLE_DIR / "experiment2_label_summary.tex", "実験2評価ラベルサマリー", "tab:experiment2_label_summary")

    exp2_cluster = read_csv(P2 / "heterogeneous_manual_review_by_cluster.csv")
    if not exp2_cluster.empty:
        df = exp2_cluster[
            [
                "cluster",
                "total_rows",
                "label_◎_count",
                "label_○_count",
                "label_△_count",
                "label_×_count",
                "strong_or_plausible_rate_◎○",
                "broad_candidate_rate_◎○△",
            ]
        ].copy()
        df.columns = ["クラスタ", "件数", "強い", "妥当", "弱い", "不適切", "強い/妥当率", "広い候補率"]
        write_tex_table(df, TABLE_DIR / "experiment2_cluster_summary.tex", "実験2クラスタレベルの評価サマリー", "tab:experiment2_cluster_summary")

    exp2_overlap = read_csv(P2 / "proposed_vs_fulltext_overlap.csv")
    exp1_final = read_csv(P1 / "final_human_review_all.csv")
    rows = []
    if not exp1_final.empty:
        exp1_score = pd.to_numeric(exp1_final.get("human_candidate_score"), errors="coerce")
        rows.append(
            [
                "実験1",
                int(exp1_final["review_id"].nunique()),
                float(exp1_score.mean()),
                int((exp1_score >= 2).sum()),
                float((exp1_score >= 2).mean()),
            ]
        )
    if not exp2_final.empty:
        exp2_valid = exp2_final["human_label"].isin(["◎", "○"])
        label_score = exp2_final["human_label"].map({"◎": 3, "○": 2, "△": 1, "×": 0})
        rows.append(
            [
                "実験2",
                int(exp2_final["family_id_simple"].nunique()),
                float(label_score.mean()),
                int(exp2_valid.sum()),
                float(exp2_valid.mean()),
            ]
        )
    if rows:
        df = pd.DataFrame(rows, columns=["実験", "評価ユニット数", "平均スコア", "妥当件数", "妥当性率"])
        write_tex_table(df, TABLE_DIR / "experiment1_experiment2_comparison.tex", "実験1と実験2の評価結果比較", "tab:experiment_comparison")

    limitations = pd.DataFrame(
        [
            ["Human review", "Labels indicate interpretability as expert-check candidates, not proof of technical transfer."],
            ["Text extraction", "Patent text can be noisy, multilingual, and unevenly translated."],
            ["Temporal filtering", "Pre-date constraints reduce leakage but do not establish causality."],
            ["Baseline", "The fulltext comparison is auxiliary and characterizes ranking behavior."],
            ["Domain validity", "Specialist confirmation is needed before treating candidates as deployable technology."],
        ],
        columns=["Aspect", "Limitation"],
    )
    write_tex_table(limitations, TABLE_DIR / "limitations.tex", "Limitations of the evaluation", "tab:limitations")

    _ = exp2_overlap  # loaded for completeness and for consistency with figure generation.


def write_readme() -> None:
    text = """# Thesis Figures and Tables

Generated by `pipeline/src/27_generate_thesis_figures_tables.py`.

## Suggested Chapter Placement

### Method chapter

- `figures/framework_overview.(png|pdf)`: overall research framework.
- `figures/solution_type_quadrant.(png|pdf)`: positioning of Experiment 1 and Experiment 2.
- `figures/method_pipeline.(png|pdf)`: common extraction/ranking/review pipeline.
- `tables/dataset_summary.tex`: dataset overview.
- `tables/extraction_fields.tex`: extracted fields used in review.

### Experiment 1 chapter

- `figures/experiment1_pipeline.(png|pdf)`: Experiment 1 workflow.
- `figures/experiment1_unet_trend.(png|pdf)`: annual U-Net appearance trend.
- `figures/experiment1_baseline_comparison.(png|pdf)`: proposed/baseline quality comparison.
- `tables/experiment1_results.tex`: human-review summary.
- `tables/experiment1_baseline_comparison.tex`: baseline comparison table.

### Experiment 2 chapter

- `figures/experiment2_pipeline.(png|pdf)`: heterogeneous-solution workflow.
- `figures/experiment2_label_distribution.(png|pdf)`: final human-label distribution.
- `figures/experiment2_cluster_distribution.(png|pdf)`: cluster-level label distribution.
- `figures/experiment2_fulltext_overlap.(png|pdf)`: proposed vs lightweight fulltext text baseline overlap.
- `tables/experiment2_label_summary.tex`: final label counts.
- `tables/experiment2_cluster_summary.tex`: cluster-level summary.

### Discussion / Limitations

- `tables/experiment1_experiment2_comparison.tex`: compact comparison between experiments.
- `tables/limitations.tex`: limitations to mention in the discussion.

## Notes

- Figures are saved as both PNG and PDF for LaTeX `\\includegraphics`.
- Most figure labels are in Japanese; some internal table labels remain in English where they correspond to source column names.
- Regenerate all assets with:

```bash
python3 pipeline/src/27_generate_thesis_figures_tables.py
```
"""
    (OUT_DIR / "README.md").write_text(text, encoding="utf-8")


def write_manifest() -> None:
    rows = []
    for p in sorted(OUT_DIR.rglob("*")):
        if p.is_file() and p.name != "manifest.csv":
            rows.append({"relative_path": str(p.relative_to(OUT_DIR)), "bytes": p.stat().st_size})
    pd.DataFrame(rows).to_csv(OUT_DIR / "manifest.csv", index=False, encoding="utf-8-sig")


def mirror_to_latex_dirs() -> None:
    for p in FIG_DIR.glob("*"):
        if p.suffix.lower() in {".png", ".pdf"}:
            shutil.copy2(p, ROOT_FIG_DIR / p.name)
    for p in TABLE_DIR.glob("*.tex"):
        shutil.copy2(p, ROOT_TABLE_DIR / p.name)


def main() -> None:
    ensure_dirs()
    fig_framework_overview()
    fig_solution_type_quadrant()
    fig_method_pipeline()
    fig_experiment1_pipeline()
    fig_experiment1_unet_trend()
    fig_experiment1_baseline_comparison()
    fig_experiment2_pipeline()
    fig_experiment2_label_distribution()
    fig_experiment2_cluster_distribution()
    fig_experiment2_fulltext_overlap()
    make_tables()
    write_readme()
    mirror_to_latex_dirs()
    write_manifest()
    print(f"Generated thesis assets in {OUT_DIR}")
    print(f"Figures: {FIG_DIR}")
    print(f"Tables: {TABLE_DIR}")


if __name__ == "__main__":
    main()
