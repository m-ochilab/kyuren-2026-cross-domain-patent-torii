"""
Script: 09_baseline_comparison.py
Purpose: 提案手法とベースライン手法のランキング比較を行う。
         U-Netの各手法でのランク（順位）を出力する。

Baselines:
  1. A0_past頻度順（count_Aの降順）
  2. gapのみ（rate_A - rate_B の降順）
  3. full_text_embeddingのみ（A0 vs B0コサイン類似度 — embeddingない場合はスキップ）
  4. problem_embeddingのみ（同）
Proposed:
  5. GapScore（07_rank_candidates.py の出力）

Input:
  - outputs/tables/method_gap_by_period_publication.csv
  - outputs/rankings/method_gap_ranking_past.csv
  - outputs/embeddings/{domain}_{type}_embeddings.npy  （オプション）
  - outputs/embeddings/{domain}_metadata.csv           （オプション）
Output:
  - outputs/tables/baseline_comparison.csv
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def get_unet_rank(ranking_df: pd.DataFrame) -> int:
    """ランキングデータフレームにおけるU-Net（またはUNet）の順位を返す。"""
    unet_kws = ["u-net", "unet"]
    for _, row in ranking_df.iterrows():
        if any(kw in str(row.get("method", "")).lower() for kw in unet_kws):
            return int(row.get("rank", row.name + 1))
    return -1  # 見つからない場合


def cosine_sim_per_method(emb_a_all: np.ndarray, meta_a: pd.DataFrame,
                           emb_b_all: np.ndarray, meta_b: pd.DataFrame,
                           method_col: str, year_min: int, year_max: int) -> float:
    """
    A0の特定手法特許 vs B0全体のコサイン類似度を返す。
    """
    # 期間フィルタ
    if "year" in meta_a.columns:
        mask_a = ((meta_a["year"] >= year_min) & (meta_a["year"] <= year_max)).values
    else:
        mask_a = np.ones(len(meta_a), dtype=bool)

    if "year" in meta_b.columns:
        mask_b = ((meta_b["year"] >= year_min) & (meta_b["year"] <= year_max)).values
    else:
        mask_b = np.ones(len(meta_b), dtype=bool)

    emb_a = emb_a_all[mask_a]
    emb_b = emb_b_all[mask_b]
    meta_a_filt = meta_a[mask_a]

    # 手法フィルタ
    if method_col in meta_a_filt.columns:
        method_mask = (meta_a_filt[method_col] == 1).values
        emb_a = emb_a[method_mask]

    if len(emb_a) == 0 or len(emb_b) == 0:
        return float("nan")

    # 重心間コサイン類似度
    norm_a = np.linalg.norm(emb_a, axis=1)
    norm_b = np.linalg.norm(emb_b, axis=1)
    emb_a = emb_a[norm_a > 1e-8]
    emb_b = emb_b[norm_b > 1e-8]
    if len(emb_a) == 0 or len(emb_b) == 0:
        return float("nan")

    c_a = emb_a.mean(axis=0)
    c_b = emb_b.mean(axis=0)
    c_a /= (np.linalg.norm(c_a) + 1e-10)
    c_b /= (np.linalg.norm(c_b) + 1e-10)
    return float(np.dot(c_a, c_b))


def rank_by_embedding_similarity(methods: list, gap_df_past: pd.DataFrame,
                                  emb_a: np.ndarray, meta_a: pd.DataFrame,
                                  emb_b: np.ndarray, meta_b: pd.DataFrame,
                                  year_min: int, year_max: int) -> pd.DataFrame:
    """
    各手法のA0 vs B0全体コサイン類似度でランキングを作成する。
    """
    rows = []
    for _, row in gap_df_past.iterrows():
        method = row["method"]
        col = "is_" + method.lower().replace("-", "_").replace("+", "p").replace(" ", "_").replace(" ", "_")
        if method.lower() in ["u-net", "unet"]:
            col = "is_unet_final" if "is_unet_final" in meta_a.columns else "is_unet"

        sim = cosine_sim_per_method(emb_a, meta_a, emb_b, meta_b,
                                    col, year_min, year_max)
        rows.append({"method": method, "similarity": sim})

    result_df = pd.DataFrame(rows)
    result_df = result_df.sort_values("similarity", ascending=False).reset_index(drop=True)
    result_df.insert(0, "rank", range(1, len(result_df) + 1))
    return result_df


def main():
    parser = argparse.ArgumentParser(description="ベースライン比較")
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
    log_file = log_dir / f"09_baseline_comparison_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 09_baseline_comparison.py 開始 ===")

    tables_dir = script_dir / cfg["data"]["output_dir"] / "tables"
    rankings_dir = script_dir / cfg["data"]["output_dir"] / "rankings"
    emb_dir = script_dir / cfg["data"]["output_dir"] / "embeddings"
    processed_dir = script_dir / cfg["data"]["processed_dir"]
    tables_dir.mkdir(parents=True, exist_ok=True)

    periods = cfg["periods"]
    year_min = periods["past_start"]
    year_max = periods["past_end"]

    # Method Gapデータ読み込み
    gap_path = tables_dir / "method_gap_by_period_publication.csv"
    if not gap_path.exists():
        logger.error(f"Method Gapファイルが存在しません: {gap_path}")
        sys.exit(1)

    gap_df = pd.read_csv(gap_path)
    past_mask = gap_df["period"].str.contains(str(year_min)) & gap_df["period"].str.contains(str(year_max))
    gap_df_past = gap_df[past_mask].copy()

    if len(gap_df_past) == 0:
        logger.error("過去期間のデータが見つかりません。")
        sys.exit(1)

    comparison_rows = []

    # ===== Baseline 1: A0_past 頻度順 =====
    baseline1 = gap_df_past.sort_values("count_A", ascending=False).reset_index(drop=True)
    baseline1.insert(0, "rank", range(1, len(baseline1) + 1))
    unet_rank_bl1 = get_unet_rank(baseline1)
    logger.info(f"Baseline1 (A0頻度順) U-Net rank: {unet_rank_bl1}")
    comparison_rows.append({
        "method_name": "Baseline1: A0_past frequency",
        "description": "A0過去期間の出現件数降順",
        "unet_rank": unet_rank_bl1,
        "available": True,
    })

    # ===== Baseline 2: gap のみ =====
    baseline2 = gap_df_past.dropna(subset=["gap"]).sort_values("gap", ascending=False).reset_index(drop=True)
    baseline2.insert(0, "rank", range(1, len(baseline2) + 1))
    unet_rank_bl2 = get_unet_rank(baseline2)
    logger.info(f"Baseline2 (gap順) U-Net rank: {unet_rank_bl2}")
    comparison_rows.append({
        "method_name": "Baseline2: gap only",
        "description": "rate_A - rate_B の降順",
        "unet_rank": unet_rank_bl2,
        "available": True,
    })

    # ===== Baseline 3 & 4: embedding ベース =====
    emb_available = False
    meta_a, meta_b = None, None
    meta_a_path = emb_dir / "A0_metadata.csv"
    meta_b_path = emb_dir / "B0_metadata.csv"

    if meta_a_path.exists() and meta_b_path.exists():
        meta_a = pd.read_csv(meta_a_path)
        meta_b = pd.read_csv(meta_b_path)
        ctx_a_path = processed_dir / "A0_contexts.csv"
        ctx_b_path = processed_dir / "B0_contexts.csv"
        if ctx_a_path.exists() and ctx_b_path.exists():
            ctx_a_len = len(pd.read_csv(ctx_a_path, usecols=["publication_number"]))
            ctx_b_len = len(pd.read_csv(ctx_b_path, usecols=["publication_number"]))
            emb_available = len(meta_a) == ctx_a_len and len(meta_b) == ctx_b_len
            if not emb_available:
                logger.warning(
                    "現在のcontexts.csvとメタデータの件数が一致しないため埋め込みベースラインをスキップ: "
                    f"A0 meta={len(meta_a)}, contexts={ctx_a_len}; "
                    f"B0 meta={len(meta_b)}, contexts={ctx_b_len}"
                )
        else:
            emb_available = True
        if emb_available:
            logger.info("メタデータ読み込み完了")

    for emb_type, baseline_label in [("full", "Baseline3"), ("problem", "Baseline4")]:
        emb_a_path = emb_dir / f"A0_{emb_type}_embeddings.npy"
        emb_b_path = emb_dir / f"B0_{emb_type}_embeddings.npy"

        if not (emb_available and emb_a_path.exists() and emb_b_path.exists()):
            logger.warning(f"{baseline_label} ({emb_type}埋め込み): スキップ（ファイルなし）")
            comparison_rows.append({
                "method_name": f"{baseline_label}: {emb_type}_embedding only",
                "description": f"{emb_type}埋め込みのA0vsB0コサイン類似度順",
                "unet_rank": "N/A (no embedding)",
                "available": False,
            })
            continue

        emb_a = np.load(emb_a_path)
        emb_b = np.load(emb_b_path)
        logger.info(f"{baseline_label}: A0{emb_a.shape}, B0{emb_b.shape}")

        # メタデータとサイズ確認
        if len(emb_a) != len(meta_a) or len(emb_b) != len(meta_b):
            logger.warning(f"{baseline_label}: メタデータと埋め込みのサイズ不一致。スキップ。")
            comparison_rows.append({
                "method_name": f"{baseline_label}: {emb_type}_embedding only",
                "description": f"{emb_type}埋め込みのA0vsB0コサイン類似度順",
                "unet_rank": "N/A (size mismatch)",
                "available": False,
            })
            continue

        baseline_emb = rank_by_embedding_similarity(
            list(gap_df_past["method"]),
            gap_df_past,
            emb_a, meta_a, emb_b, meta_b,
            year_min, year_max,
        )
        unet_rank_emb = get_unet_rank(baseline_emb)
        logger.info(f"{baseline_label} ({emb_type}埋め込み) U-Net rank: {unet_rank_emb}")
        comparison_rows.append({
            "method_name": f"{baseline_label}: {emb_type}_embedding only",
            "description": f"{emb_type}埋め込みのA0vsB0コサイン類似度順",
            "unet_rank": unet_rank_emb,
            "available": True,
        })

    # ===== Proposed: GapScore =====
    ranking_path = rankings_dir / "method_gap_ranking_past.csv"
    if ranking_path.exists():
        proposed_ranking = pd.read_csv(ranking_path)
        unet_rank_proposed = get_unet_rank(proposed_ranking)
        note = proposed_ranking["note"].iloc[0] if "note" in proposed_ranking.columns else "N/A"
        logger.info(f"Proposed (GapScore) U-Net rank: {unet_rank_proposed}")
        comparison_rows.append({
            "method_name": "Proposed: GapScore",
            "description": f"提案手法 GapScore ({note})",
            "unet_rank": unet_rank_proposed,
            "available": True,
        })
    else:
        logger.warning("GapScoreランキングファイルが存在しません。07を先に実行してください。")
        comparison_rows.append({
            "method_name": "Proposed: GapScore",
            "description": "提案手法 GapScore",
            "unet_rank": "N/A",
            "available": False,
        })

    # 結果保存
    result_df = pd.DataFrame(comparison_rows)
    out_path = tables_dir / "baseline_comparison.csv"
    result_df.to_csv(out_path, index=False, encoding="utf-8")
    logger.info(f"保存: {out_path}")

    print("\n=== ベースライン比較（U-Netの順位）===")
    print(result_df[["method_name", "unet_rank", "description"]].to_string(index=False))

    logger.info("=== 09_baseline_comparison.py 完了 ===")


if __name__ == "__main__":
    main()
