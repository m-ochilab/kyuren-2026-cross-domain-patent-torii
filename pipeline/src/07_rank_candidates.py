"""
Script: 07_rank_candidates.py
Purpose: GapScoreを計算して技術候補をランキングする。
         埋め込みあり: GapScore = problem_similarity × normalized_gap × log(1+A_count) × low_presence_bonus_B
         埋め込みなし: GapScore_simple = gap × log(1+A_count) × low_presence_bonus_B
Input:
  - outputs/tables/method_gap_by_period_publication.csv
  - outputs/embeddings/A0_problem_embeddings.npy  （オプション）
  - outputs/embeddings/B0_problem_embeddings.npy  （オプション）
  - outputs/embeddings/{domain}_metadata.csv       （オプション）
Output:
  - outputs/rankings/method_gap_ranking_past.csv
  - outputs/rankings/method_gap_ranking_all.csv
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def cosine_sim_centroids(emb_a: np.ndarray, emb_b: np.ndarray) -> float:
    """2つの埋め込み集合の重心間コサイン類似度を計算する。"""
    if len(emb_a) == 0 or len(emb_b) == 0:
        return float("nan")
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


def compute_unet_problem_similarity(emb_dir: Path, period_mask_a: np.ndarray,
                                     period_mask_b: np.ndarray,
                                     meta_a: pd.DataFrame, meta_b: pd.DataFrame,
                                     logger: logging.Logger) -> float:
    """
    A0のU-Net特許のproblem embeddingと
    B0全体のproblem embeddingのコサイン類似度を計算する。
    """
    emb_a_path = emb_dir / "A0_problem_embeddings.npy"
    emb_b_path = emb_dir / "B0_problem_embeddings.npy"
    if not emb_a_path.exists() or not emb_b_path.exists():
        return float("nan")

    emb_a_all = np.load(emb_a_path)
    emb_b_all = np.load(emb_b_path)
    if len(emb_a_all) != len(meta_a) or len(emb_b_all) != len(meta_b):
        logger.warning(
            "埋め込みとメタデータの件数が一致しません: "
            f"A0 emb={len(emb_a_all)}, meta={len(meta_a)}; "
            f"B0 emb={len(emb_b_all)}, meta={len(meta_b)}"
        )
        return float("nan")

    emb_a = emb_a_all[period_mask_a]
    emb_b = emb_b_all[period_mask_b]

    # A0のU-Netのみ
    unet_col = "is_unet_final" if "is_unet_final" in meta_a.columns else "is_unet"
    if unet_col in meta_a.columns:
        unet_mask = (meta_a.iloc[period_mask_a][unet_col] == 1).values
        emb_a = emb_a[unet_mask]

    return cosine_sim_centroids(emb_a, emb_b)


def compute_gap_score(row: pd.Series, problem_sim: float,
                      max_gap: float, epsilon: float,
                      low_presence_bonus_cap: float) -> dict:
    """
    GapScoreを計算する。

    GapScore (embedding あり):
        problem_similarity × normalized_gap × log(1+A_count) × low_presence_bonus_B

    GapScore_simple (embedding なし):
        gap × log(1+A_count) × low_presence_bonus_B
    """
    gap = row.get("gap", float("nan"))
    count_a = row.get("count_A", 0)
    rate_b = row.get("rate_B", float("nan"))

    if pd.isna(gap) or gap < 0:
        gap = 0.0

    # normalized_gap: gap を最大gapで正規化
    if max_gap > 0:
        normalized_gap = gap / (max_gap + epsilon)
    else:
        normalized_gap = 0.0

    # log(1 + A_count): A0での出現頻度の対数スケール重み
    log_a_count = float(np.log1p(count_a))

    # low_presence_bonus_B: B0での出現率が低いほど高くなるボーナス
    if pd.isna(rate_b):
        low_presence_bonus = 1.0
    else:
        low_presence_bonus = min(1.0 / (rate_b + epsilon), low_presence_bonus_cap)

    if not pd.isna(problem_sim) and problem_sim > 0:
        # 埋め込みあり版
        gap_score = problem_sim * normalized_gap * log_a_count * low_presence_bonus
        note = "embedding-based"
    else:
        # 埋め込みなし版（シンプル版）
        gap_score = gap * log_a_count * low_presence_bonus
        note = "simple (no embedding)"

    return {
        "gap_score": gap_score,
        "problem_similarity": problem_sim if not pd.isna(problem_sim) else None,
        "normalized_gap": normalized_gap,
        "log_a_count": log_a_count,
        "low_presence_bonus": round(low_presence_bonus, 4),
        "note": note,
    }


def rank_for_period(gap_df: pd.DataFrame, period_label: str,
                    emb_dir: Path, meta_a: pd.DataFrame, meta_b: pd.DataFrame,
                    year_min: int, year_max: int,
                    cfg: dict, logger: logging.Logger) -> pd.DataFrame:
    """特定期間のGapScoreランキングを作成する。"""
    period_df = gap_df[gap_df["period"].str.startswith(f"past" if "past" in period_label else period_label.split("(")[0])]

    # period_labelに合わせてフィルタ
    mask = gap_df["period"].str.contains(str(year_min), na=False) & gap_df["period"].str.contains(str(year_max), na=False)
    period_df = gap_df[mask]
    if len(period_df) == 0:
        # フォールバック: period列全体から探す
        for label in gap_df["period"].unique():
            if str(year_min) in label and str(year_max) in label:
                period_df = gap_df[gap_df["period"] == label]
                break

    if len(period_df) == 0:
        logger.warning(f"期間 {period_label} のデータが見つかりません。")
        return pd.DataFrame()

    epsilon = cfg["scoring"]["epsilon"]
    bonus_cap = cfg["scoring"]["low_presence_bonus_cap"]

    # 期間マスク（メタデータがある場合）
    period_mask_a = np.ones(len(meta_a), dtype=bool) if meta_a is not None else None
    period_mask_b = np.ones(len(meta_b), dtype=bool) if meta_b is not None else None

    if meta_a is not None and "year" in meta_a.columns:
        period_mask_a = ((meta_a["year"] >= year_min) & (meta_a["year"] <= year_max)).values
    if meta_b is not None and "year" in meta_b.columns:
        period_mask_b = ((meta_b["year"] >= year_min) & (meta_b["year"] <= year_max)).values

    # problem_similarity: A0 U-Net vs B0 全体
    if emb_dir.exists() and meta_a is not None and meta_b is not None and period_mask_a is not None:
        problem_sim = compute_unet_problem_similarity(
            emb_dir, period_mask_a, period_mask_b, meta_a, meta_b, logger
        )
    else:
        problem_sim = float("nan")

    logger.info(f"[{period_label}] problem_similarity: {problem_sim}")

    max_gap = period_df["gap"].dropna().max()
    if pd.isna(max_gap):
        max_gap = 0.0

    rows = []
    for _, row in period_df.iterrows():
        score_dict = compute_gap_score(row, problem_sim, max_gap, epsilon, bonus_cap)
        rows.append({
            "method": row["method"],
            "gap_score": score_dict["gap_score"],
            "problem_similarity": score_dict["problem_similarity"],
            "A_rate": row.get("rate_A", float("nan")),
            "B_rate": row.get("rate_B", float("nan")),
            "A_count": row.get("count_A", 0),
            "B_count": row.get("count_B", 0),
            "gap": row.get("gap", float("nan")),
            "ratio": row.get("ratio", float("nan")),
            "low_presence_bonus": score_dict["low_presence_bonus"],
            "note": score_dict["note"],
        })

    result_df = pd.DataFrame(rows)
    result_df = result_df.sort_values("gap_score", ascending=False).reset_index(drop=True)
    result_df.insert(0, "rank", range(1, len(result_df) + 1))
    return result_df


def main():
    parser = argparse.ArgumentParser(description="GapScoreによる候補ランキング")
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
    log_file = log_dir / f"07_rank_candidates_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 07_rank_candidates.py 開始 ===")

    tables_dir = script_dir / cfg["data"]["output_dir"] / "tables"
    rankings_dir = script_dir / cfg["data"]["output_dir"] / "rankings"
    rankings_dir.mkdir(parents=True, exist_ok=True)
    emb_dir = script_dir / cfg["data"]["output_dir"] / "embeddings"

    # Method Gap テーブル読み込み
    gap_path = tables_dir / "method_gap_by_period_publication.csv"
    if not gap_path.exists():
        logger.error(f"Method Gap ファイルが存在しません: {gap_path}")
        logger.error("先に 06_compute_method_gap.py を実行してください。")
        sys.exit(1)

    gap_df = pd.read_csv(gap_path)
    logger.info(f"Method Gap 読み込み: {len(gap_df)}行")

    # メタデータ読み込み（problem embedding がある場合のみ）
    meta_a, meta_b = None, None
    meta_a_path = emb_dir / "A0_metadata.csv"
    meta_b_path = emb_dir / "B0_metadata.csv"
    emb_a_path = emb_dir / "A0_problem_embeddings.npy"
    emb_b_path = emb_dir / "B0_problem_embeddings.npy"
    if emb_a_path.exists() and emb_b_path.exists() and meta_a_path.exists():
        meta_a = pd.read_csv(meta_a_path)
        logger.info(f"A0メタデータ読み込み: {len(meta_a)}行")
    if emb_a_path.exists() and emb_b_path.exists() and meta_b_path.exists():
        meta_b = pd.read_csv(meta_b_path)
        logger.info(f"B0メタデータ読み込み: {len(meta_b)}行")

    periods = cfg["periods"]

    # 過去期間ランキング
    past_ranking = rank_for_period(
        gap_df,
        period_label=f"past({periods['past_start']}-{periods['past_end']})",
        emb_dir=emb_dir,
        meta_a=meta_a, meta_b=meta_b,
        year_min=periods["past_start"], year_max=periods["past_end"],
        cfg=cfg, logger=logger,
    )
    if len(past_ranking) > 0:
        past_out = rankings_dir / "method_gap_ranking_past.csv"
        past_ranking.to_csv(past_out, index=False, encoding="utf-8")
        logger.info(f"保存: {past_out}")
        print(f"\n=== 過去期間ランキング ({periods['past_start']}-{periods['past_end']}) ===")
        print(past_ranking[["rank", "method", "gap_score", "A_rate", "B_rate", "gap", "note"]].to_string(index=False))

    # 全期間ランキング
    all_ranking = rank_for_period(
        gap_df,
        period_label=f"all({periods['all_start']}-{periods['all_end']})",
        emb_dir=emb_dir,
        meta_a=meta_a, meta_b=meta_b,
        year_min=periods["all_start"], year_max=periods["all_end"],
        cfg=cfg, logger=logger,
    )
    if len(all_ranking) > 0:
        all_out = rankings_dir / "method_gap_ranking_all.csv"
        all_ranking.to_csv(all_out, index=False, encoding="utf-8")
        logger.info(f"保存: {all_out}")

    logger.info("=== 07_rank_candidates.py 完了 ===")


if __name__ == "__main__":
    main()
