"""
Script: 10_export_for_thesis.py
Purpose: 論文用の図表を生成する。matplotlib + Hiragino Sansフォント（日本語対応）。
         埋め込みがない場合は一部の図をスキップする。
Input:
  - outputs/tables/ 以下の各CSVファイル
  - outputs/rankings/ 以下の各CSVファイル
Output:
  - outputs/figures/*.png  （各種グラフ）
  - outputs/tables/*.tex   （LaTeX用テーブル）
"""

import argparse
import logging
import sys
import warnings
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import yaml

warnings.filterwarnings("ignore")


# --------------------------------------------------------------------------- #
# フォント設定（日本語）                                                         #
# --------------------------------------------------------------------------- #
def setup_font(logger: logging.Logger):
    """日本語フォントを設定する。利用可能なフォントを自動選択。"""
    font_candidates = [
        "Hiragino Sans",
        "Hiragino Kaku Gothic Pro",
        "AppleGothic",
        "IPAGothic",
        "Noto Sans CJK JP",
        "DejaVu Sans",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in font_candidates:
        if font in available:
            plt.rcParams["font.family"] = font
            plt.rcParams["axes.unicode_minus"] = False
            logger.info(f"フォント設定: {font}")
            return font
    logger.warning("日本語フォントが見つかりません。デフォルトフォントを使用します。")
    return "default"


COLORS = {
    "A0": "#2196F3",
    "B0": "#FF5722",
    "past": "#607D8B",
    "future": "#4CAF50",
    "unet": "#9C27B0",
    "baseline": "#FF9800",
}

PERIOD_COLORS = {
    "past": "#E3F2FD",
    "future": "#E8F5E9",
}


# --------------------------------------------------------------------------- #
# 図1: データセット概要                                                          #
# --------------------------------------------------------------------------- #
def plot_dataset_overview(summary_df: pd.DataFrame, figures_dir: Path, logger: logging.Logger):
    """A0/B0の件数棒グラフを生成する。"""
    pub_df = summary_df[summary_df["level"] == "publication"]
    fam_df = summary_df[summary_df["level"] == "family"]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("データセット概要 (Dataset Overview)", fontsize=14, fontweight="bold")

    for ax, df, title in zip(axes, [pub_df, fam_df], ["Publication Level", "Family Level"]):
        domains = df["domain"].tolist()
        totals = df["total_records"].tolist()
        past_counts = df["past_records"].tolist()
        future_counts = df["future_records"].tolist()
        unet_counts = df["is_unet_total"].tolist()

        x = np.arange(len(domains))
        width = 0.2

        ax.bar(x - 1.5 * width, totals, width, label="総件数 (Total)", color=COLORS["A0"], alpha=0.8)
        ax.bar(x - 0.5 * width, past_counts, width, label=f"過去期間 (Past)", color=COLORS["past"], alpha=0.8)
        ax.bar(x + 0.5 * width, future_counts, width, label=f"将来期間 (Future)", color=COLORS["future"], alpha=0.8)
        ax.bar(x + 1.5 * width, unet_counts, width, label="U-Net件数", color=COLORS["unet"], alpha=0.8)

        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(domains)
        ax.set_ylabel("件数")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(axis="y", alpha=0.3)

        # 値ラベル
        for rect in ax.patches:
            h = rect.get_height()
            if h > 0:
                ax.text(rect.get_x() + rect.get_width() / 2, h + 0.5,
                        str(int(h)), ha="center", va="bottom", fontsize=7)

    plt.tight_layout()
    out = figures_dir / "dataset_overview.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"保存: {out}")


# --------------------------------------------------------------------------- #
# 図2: U-Net年次出現率                                                          #
# --------------------------------------------------------------------------- #
def plot_unet_annual_rate(processed_dir: Path, figures_dir: Path,
                           cfg: dict, logger: logging.Logger):
    """U-Net年次出現率（A0/B0）を折れ線グラフで描画する。"""
    periods = cfg["periods"]
    rows = []

    for domain in ["A0", "B0"]:
        # publication_level か with_methods を優先
        for fname in [f"{domain}_with_methods.csv", f"{domain}_publication_level.csv"]:
            p = processed_dir / fname
            if p.exists():
                df = pd.read_csv(p)
                break
        else:
            logger.warning(f"[{domain}] データファイルが見つかりません。スキップ。")
            continue

        unet_col = "is_unet_final" if "is_unet_final" in df.columns else "is_unet"
        if "year" not in df.columns or unet_col not in df.columns:
            continue

        yearly = df.groupby("year").agg(
            total=(unet_col, "count"),
            unet_count=(unet_col, "sum"),
        ).reset_index()
        yearly["unet_rate"] = yearly["unet_count"] / yearly["total"]
        yearly["domain"] = domain
        rows.append(yearly)

    if not rows:
        logger.warning("年次データが取得できませんでした。図2をスキップします。")
        return

    all_df = pd.concat(rows, ignore_index=True)
    fig, ax = plt.subplots(figsize=(10, 5))

    for domain, color in [("A0", COLORS["A0"]), ("B0", COLORS["B0"])]:
        d = all_df[all_df["domain"] == domain].sort_values("year")
        if len(d) == 0:
            continue
        ax.plot(d["year"], d["unet_rate"] * 100, marker="o", label=domain,
                color=color, linewidth=2, markersize=6)

    # 期間帯の背景色
    ax.axvspan(periods["past_start"] - 0.5, periods["past_end"] + 0.5,
               alpha=0.15, color=COLORS["past"], label=f"過去期間 ({periods['past_start']}-{periods['past_end']})")
    ax.axvspan(periods["future_start"] - 0.5, periods["future_end"] + 0.5,
               alpha=0.15, color=COLORS["future"], label=f"将来期間 ({periods['future_start']}-{periods['future_end']})")

    ax.set_title("U-Net年次出現率 (Annual U-Net Presence Rate)", fontsize=13, fontweight="bold")
    ax.set_xlabel("年 (Year)")
    ax.set_ylabel("U-Net出現率 (%)")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    ax.set_xlim(periods["all_start"] - 0.5, periods["all_end"] + 0.5)

    plt.tight_layout()
    out = figures_dir / "unet_annual_rate_publication.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"保存: {out}")


# --------------------------------------------------------------------------- #
# 図3 & 4: U-Net期間別棒グラフ                                                  #
# --------------------------------------------------------------------------- #
def plot_unet_period_comparison(summary_df: pd.DataFrame, figures_dir: Path,
                                 cfg: dict, logger: logging.Logger):
    """期間別U-Net出現率を棒グラフで描画する。"""
    periods = cfg["periods"]

    for level in ["publication", "family"]:
        df = summary_df[summary_df["level"] == level]
        if len(df) == 0:
            continue

        domains = df["domain"].tolist()
        past_rates = df["is_unet_past"].values / df["past_records"].values.clip(min=1) * 100
        future_rates = df["is_unet_future"].values / df["future_records"].values.clip(min=1) * 100

        x = np.arange(len(domains))
        width = 0.35

        fig, ax = plt.subplots(figsize=(8, 5))
        bars1 = ax.bar(x - width / 2, past_rates, width,
                       label=f"過去期間 ({periods['past_start']}-{periods['past_end']})",
                       color=COLORS["past"], alpha=0.8)
        bars2 = ax.bar(x + width / 2, future_rates, width,
                       label=f"将来期間 ({periods['future_start']}-{periods['future_end']})",
                       color=COLORS["future"], alpha=0.8)

        ax.set_title(f"U-Net期間別出現率 ({level.capitalize()} Level)",
                     fontsize=13, fontweight="bold")
        ax.set_xlabel("ドメイン")
        ax.set_ylabel("U-Net出現率 (%)")
        ax.set_xticks(x)
        ax.set_xticklabels(domains)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        def add_labels(bars):
            for bar in bars:
                h = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.1,
                        f"{h:.1f}%", ha="center", va="bottom", fontsize=9)

        add_labels(bars1)
        add_labels(bars2)

        plt.tight_layout()
        out = figures_dir / f"unet_period_comparison_{level}.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info(f"保存: {out}")


# --------------------------------------------------------------------------- #
# 図5: Method Gap Ranking                                                      #
# --------------------------------------------------------------------------- #
def plot_method_gap_ranking(rankings_dir: Path, figures_dir: Path,
                             cfg: dict, logger: logging.Logger):
    """GapScoreランキング棒グラフを描画する。"""
    ranking_path = rankings_dir / "method_gap_ranking_past.csv"
    if not ranking_path.exists():
        logger.warning("GapScoreランキングファイルが存在しません。図5をスキップ。")
        return

    df = pd.read_csv(ranking_path)
    top_k = cfg["scoring"]["top_k"]
    df = df.head(top_k)

    if "gap_score" not in df.columns:
        logger.warning("gap_score列が存在しません。図5をスキップ。")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [COLORS["unet"] if any(kw in str(m).lower() for kw in ["u-net", "unet"])
              else COLORS["A0"] for m in df["method"]]

    bars = ax.barh(df["method"][::-1], df["gap_score"][::-1], color=colors[::-1], alpha=0.85)
    ax.set_title(f"GapScoreランキング Top{top_k} (Past Period)", fontsize=13, fontweight="bold")
    ax.set_xlabel("GapScore")
    ax.grid(axis="x", alpha=0.3)

    for bar, score in zip(bars, df["gap_score"][::-1]):
        ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height() / 2,
                f"{score:.4f}", va="center", fontsize=8)

    # 凡例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLORS["unet"], alpha=0.85, label="U-Net系手法"),
        Patch(facecolor=COLORS["A0"], alpha=0.85, label="その他の手法"),
    ]
    ax.legend(handles=legend_elements, loc="lower right")

    plt.tight_layout()
    out = figures_dir / "method_gap_ranking.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"保存: {out}")


# --------------------------------------------------------------------------- #
# 図6: ドメイン類似度ヒートマップ                                                #
# --------------------------------------------------------------------------- #
def plot_domain_similarity_heatmap(tables_dir: Path, figures_dir: Path, logger: logging.Logger):
    """ドメイン類似度ヒートマップを描画する。"""
    sim_path = tables_dir / "domain_similarity_summary.csv"
    if not sim_path.exists():
        logger.warning("ドメイン類似度ファイルが存在しません。図6をスキップ。")
        return

    df = pd.read_csv(sim_path)
    if df["similarity"].isna().all():
        logger.warning("類似度データがNaNです。図6をスキップ。")
        return

    # ピボット
    try:
        pivot = df.pivot_table(index="comparison", columns="emb_type", values="similarity")
    except Exception as e:
        logger.warning(f"ピボット失敗: {e}。図6をスキップ。")
        return

    import seaborn as sns
    fig, ax = plt.subplots(figsize=(8, max(4, len(pivot) * 0.6)))
    sns.heatmap(
        pivot, annot=True, fmt=".3f", cmap="YlOrRd",
        ax=ax, linewidths=0.5, annot_kws={"size": 9},
        vmin=0, vmax=1,
    )
    ax.set_title("ドメイン間コサイン類似度 (Domain Similarity)", fontsize=13, fontweight="bold")
    ax.set_xlabel("埋め込みタイプ (Embedding Type)")
    ax.set_ylabel("比較対象 (Comparison)")
    plt.xticks(rotation=30, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    out = figures_dir / "domain_similarity_heatmap.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"保存: {out}")


# --------------------------------------------------------------------------- #
# 図7: ベースライン比較                                                          #
# --------------------------------------------------------------------------- #
def plot_baseline_comparison(tables_dir: Path, figures_dir: Path, logger: logging.Logger):
    """ベースライン比較（U-Netの各手法でのランク）を棒グラフで描画する。"""
    bl_path = tables_dir / "baseline_comparison.csv"
    if not bl_path.exists():
        logger.warning("ベースライン比較ファイルが存在しません。図7をスキップ。")
        return

    df = pd.read_csv(bl_path)
    df = df[df["available"] == True].copy()
    if len(df) == 0:
        logger.warning("利用可能なベースラインデータがありません。図7をスキップ。")
        return

    # unet_rankが数値のもののみ
    def to_rank(v):
        try:
            return int(v)
        except:
            return None

    df["rank_val"] = df["unet_rank"].apply(to_rank)
    df = df.dropna(subset=["rank_val"])
    if len(df) == 0:
        return

    df = df.sort_values("rank_val")
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [COLORS["unet"] if "Proposed" in str(n) else COLORS["baseline"]
              for n in df["method_name"]]
    bars = ax.barh(df["method_name"][::-1], df["rank_val"][::-1], color=colors[::-1], alpha=0.85)

    ax.set_title("ベースライン比較: U-Netの順位 (Baseline Comparison)", fontsize=13, fontweight="bold")
    ax.set_xlabel("U-Netの順位（低い=良い）")
    ax.grid(axis="x", alpha=0.3)
    ax.invert_xaxis()  # 低い順位（=良い）が左に

    for bar, rank in zip(bars, df["rank_val"][::-1]):
        ax.text(bar.get_width() - 0.05, bar.get_y() + bar.get_height() / 2,
                f"  {int(rank)}位", va="center", ha="right", fontsize=9)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLORS["unet"], alpha=0.85, label="提案手法 (Proposed)"),
        Patch(facecolor=COLORS["baseline"], alpha=0.85, label="ベースライン (Baseline)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right")

    plt.tight_layout()
    out = figures_dir / "baseline_comparison.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"保存: {out}")


# --------------------------------------------------------------------------- #
# LaTeX テーブル生成                                                            #
# --------------------------------------------------------------------------- #
def df_to_latex(df: pd.DataFrame, caption: str, label: str,
                float_fmt: str = ".4f") -> str:
    """DataFrameをLaTeXのtabular環境に変換する。"""
    col_fmt = "l" + "r" * (len(df.columns) - 1)
    lines = [
        "\\begin{table}[htbp]",
        "  \\centering",
        f"  \\caption{{{caption}}}",
        f"  \\label{{{label}}}",
        f"  \\begin{{tabular}}{{{col_fmt}}}",
        "    \\hline",
    ]
    # ヘッダ
    header = " & ".join(str(c).replace("_", "\\_") for c in df.columns)
    lines.append(f"    {header} \\\\")
    lines.append("    \\hline")
    # データ行
    for _, row in df.iterrows():
        cells = []
        for val in row:
            if isinstance(val, float):
                if pd.isna(val):
                    cells.append("--")
                else:
                    cells.append(f"{val:{float_fmt}}")
            else:
                cells.append(str(val).replace("_", "\\_").replace("%", "\\%"))
        lines.append("    " + " & ".join(cells) + " \\\\")
    lines += [
        "    \\hline",
        "  \\end{tabular}",
        "\\end{table}",
    ]
    return "\n".join(lines)


def export_latex_tables(tables_dir: Path, logger: logging.Logger):
    """各CSVをLaTeXテーブルに変換して保存する。"""
    tasks = [
        ("method_gap_by_period_publication.csv", "table_method_gap.tex",
         "Method Gap（ドメイン間手法出現率差）", "tab:method_gap"),
        ("temporal_evaluation_summary.csv", "table_temporal_evaluation.tex",
         "後ろ向き評価サマリー（Temporal Evaluation）", "tab:temporal_eval"),
        ("baseline_comparison.csv", "table_baseline_comparison.tex",
         "ベースライン比較（U-Netの順位）", "tab:baseline"),
        ("domain_similarity_summary.csv", "table_domain_similarity.tex",
         "ドメイン間コサイン類似度", "tab:domain_sim"),
    ]

    for csv_name, tex_name, caption, label in tasks:
        csv_path = tables_dir / csv_name
        if not csv_path.exists():
            logger.warning(f"LaTeX変換スキップ: {csv_name} が存在しません。")
            continue
        df = pd.read_csv(csv_path)
        # 行数が多い場合は先頭20行
        if len(df) > 20:
            df = df.head(20)
            caption += "（先頭20行）"
        tex_str = df_to_latex(df, caption, label)
        out_path = tables_dir / tex_name
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(tex_str)
        logger.info(f"LaTeX保存: {out_path}")


# --------------------------------------------------------------------------- #
# メイン                                                                        #
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="論文用図表の生成")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--sample", type=int, default=None)
    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = script_dir / config_path

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    log_dir = script_dir / cfg["data"]["output_dir"] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"10_export_for_thesis_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 10_export_for_thesis.py 開始 ===")

    setup_font(logger)

    figures_dir = script_dir / cfg["data"]["output_dir"] / "figures"
    tables_dir = script_dir / cfg["data"]["output_dir"] / "tables"
    rankings_dir = script_dir / cfg["data"]["output_dir"] / "rankings"
    processed_dir = script_dir / cfg["data"]["processed_dir"]
    figures_dir.mkdir(parents=True, exist_ok=True)

    # データセットサマリー読み込み
    summary_path = tables_dir / "dataset_summary.csv"
    if summary_path.exists():
        summary_df = pd.read_csv(summary_path)
        # 図1: データセット概要
        plot_dataset_overview(summary_df, figures_dir, logger)
        # 図3 & 4: 期間別棒グラフ
        plot_unet_period_comparison(summary_df, figures_dir, cfg, logger)
    else:
        logger.warning("dataset_summary.csv が存在しません。図1,3,4をスキップ。")

    # 図2: U-Net年次出現率
    plot_unet_annual_rate(processed_dir, figures_dir, cfg, logger)

    # 図5: GapScoreランキング
    plot_method_gap_ranking(rankings_dir, figures_dir, cfg, logger)

    # 図6: ドメイン類似度ヒートマップ
    plot_domain_similarity_heatmap(tables_dir, figures_dir, logger)

    # 図7: ベースライン比較
    plot_baseline_comparison(tables_dir, figures_dir, logger)

    # LaTeX テーブル
    export_latex_tables(tables_dir, logger)

    logger.info("=== 10_export_for_thesis.py 完了 ===")
    print("\n出力先:")
    print(f"  図: {figures_dir}")
    print(f"  LaTeXテーブル: {tables_dir}")


if __name__ == "__main__":
    main()
