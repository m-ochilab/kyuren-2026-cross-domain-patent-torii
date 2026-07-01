"""
Script: 08_temporal_evaluation.py
Purpose: 後ろ向き評価。過去期間のランキングにおけるU-Netの順位と
         将来期間でのB0 U-Net出現増加を評価する。Hit@k指標を計算する。
Input:
  - outputs/rankings/method_gap_ranking_past.csv
  - outputs/tables/method_gap_by_period_publication.csv
  - data/processed/A0_with_methods.csv
  - data/processed/B0_with_methods.csv
Output:
  - outputs/tables/temporal_evaluation_summary.csv
  - outputs/tables/future_growth_by_method.csv
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml


UNET_CANONICAL = "U-Net"  # ランキングでのU-Netの代表名


def find_unet_rank(ranking_df: pd.DataFrame) -> dict:
    """ランキングにおけるU-Net関連手法の順位を検索する。"""
    unet_keywords = ["u-net", "unet", "nnu-net", "u-net++", "unet++"]
    result = {}
    for _, row in ranking_df.iterrows():
        method_lower = str(row["method"]).lower()
        for kw in unet_keywords:
            if kw in method_lower:
                result[row["method"]] = int(row["rank"])
                break
    return result


def compute_hit_at_k(ranking_df: pd.DataFrame, target_methods: list,
                      k_values: list) -> dict:
    """
    Hit@k: 上位k件の中にtarget_methodsのいずれかが含まれるか。
    ここではU-Net系手法の順位でHit@kを計算する。
    """
    unet_keywords = ["u-net", "unet"]
    hit_results = {}
    for k in k_values:
        top_k = ranking_df[ranking_df["rank"] <= k]
        hit = any(
            any(kw in str(m).lower() for kw in unet_keywords)
            for m in top_k["method"]
        )
        hit_results[f"Hit@{k}"] = int(hit)
    return hit_results


def compute_future_growth(df_b_past: pd.DataFrame, df_b_future: pd.DataFrame,
                           methods: list) -> pd.DataFrame:
    """
    B0の過去→将来でのU-Net出現率変化を計算する。
    """
    rows = []
    for method in methods:
        col = "is_" + method.lower().replace("-", "_").replace("+", "p").replace(" ", "_")
        # U-Net の場合は最終判定列を優先
        if method.lower() in ["u-net", "unet"]:
            col_past = "is_unet_final" if "is_unet_final" in df_b_past.columns else "is_unet"
            col_future = "is_unet_final" if "is_unet_final" in df_b_future.columns else "is_unet"
        else:
            col_past = col
            col_future = col

        def get_rate(df, col_name):
            if col_name not in df.columns:
                return float("nan"), 0, len(df)
            if df[col_name].isna().all():
                return float("nan"), 0, len(df)
            n = len(df)
            count = int(df[col_name].sum())
            rate = count / n if n > 0 else 0.0
            return rate, count, n

        rate_past, count_past, n_past = get_rate(df_b_past, col_past)
        rate_future, count_future, n_future = get_rate(df_b_future, col_future)

        if not (pd.isna(rate_past) or pd.isna(rate_future)):
            growth = rate_future - rate_past
            growth_ratio = rate_future / (rate_past + 1e-10)
        else:
            growth = float("nan")
            growth_ratio = float("nan")

        rows.append({
            "method": method,
            "B0_rate_past": round(rate_past, 6) if not pd.isna(rate_past) else float("nan"),
            "B0_count_past": count_past,
            "B0_n_past": n_past,
            "B0_rate_future": round(rate_future, 6) if not pd.isna(rate_future) else float("nan"),
            "B0_count_future": count_future,
            "B0_n_future": n_future,
            "growth_absolute": round(growth, 6) if not pd.isna(growth) else float("nan"),
            "growth_ratio": round(growth_ratio, 4) if not pd.isna(growth_ratio) else float("nan"),
        })

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="後ろ向き評価")
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
    log_file = log_dir / f"08_temporal_evaluation_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 08_temporal_evaluation.py 開始 ===")

    rankings_dir = script_dir / cfg["data"]["output_dir"] / "rankings"
    tables_dir = script_dir / cfg["data"]["output_dir"] / "tables"
    processed_dir = script_dir / cfg["data"]["processed_dir"]
    tables_dir.mkdir(parents=True, exist_ok=True)

    periods = cfg["periods"]
    methods = cfg["methods"]["target_methods"]

    # --- ランキングからU-Netの順位を取得 ---
    ranking_path = rankings_dir / "method_gap_ranking_past.csv"
    unet_rank = {}
    hit_results = {}
    if ranking_path.exists():
        ranking_df = pd.read_csv(ranking_path)
        unet_rank = find_unet_rank(ranking_df)
        hit_results = compute_hit_at_k(ranking_df, methods, k_values=[1, 3, 5, 10])
        logger.info(f"U-Net系の順位: {unet_rank}")
        logger.info(f"Hit@k: {hit_results}")
    else:
        logger.warning(f"ランキングファイルが存在しません: {ranking_path}")
        logger.warning("先に 07_rank_candidates.py を実行してください。")

    # --- B0のデータ読み込み ---
    in_b_path = processed_dir / "B0_with_methods.csv"
    if not in_b_path.exists():
        in_b_path = processed_dir / "B0_publication_level.csv"
        logger.warning(f"B0_with_methods.csv が存在しないため B0_publication_level.csv を使用します。")

    if not in_b_path.exists():
        logger.error(f"B0データが見つかりません。スキップします。")
        growth_df = pd.DataFrame()
    else:
        df_b = pd.read_csv(in_b_path)
        if args.sample:
            df_b = df_b.sample(min(args.sample, len(df_b)), random_state=42).reset_index(drop=True)

        mask_past = (df_b["year"] >= periods["past_start"]) & (df_b["year"] <= periods["past_end"])
        mask_future = (df_b["year"] >= periods["future_start"]) & (df_b["year"] <= periods["future_end"])
        df_b_past = df_b[mask_past]
        df_b_future = df_b[mask_future]

        logger.info(f"B0 過去期間: {len(df_b_past)}行, 将来期間: {len(df_b_future)}行")

        growth_df = compute_future_growth(df_b_past, df_b_future, methods)
        growth_out = tables_dir / "future_growth_by_method.csv"
        growth_df.to_csv(growth_out, index=False, encoding="utf-8")
        logger.info(f"保存: {growth_out}")

        print("\n=== B0 将来期間成長率 ===")
        print(growth_df.to_string(index=False))

    # --- 評価サマリー ---
    summary_rows = []

    # U-Netの順位
    for method, rank in unet_rank.items():
        summary_rows.append({
            "metric": f"rank_in_past_ranking",
            "method": method,
            "value": rank,
            "description": f"過去期間ランキングにおける {method} の順位",
        })

    # Hit@k
    for metric, value in hit_results.items():
        summary_rows.append({
            "metric": metric,
            "method": "U-Net系",
            "value": value,
            "description": f"上位{metric.split('@')[1]}件以内にU-Net系が含まれるか（1=含む, 0=含まない）",
        })

    # B0成長率（U-Netのみ）
    if len(growth_df) > 0:
        unet_growth = growth_df[growth_df["method"].str.lower().isin(["u-net", "unet"])]
        for _, row in unet_growth.iterrows():
            summary_rows.append({
                "metric": "B0_future_growth_absolute",
                "method": row["method"],
                "value": row["growth_absolute"],
                "description": "B0における将来期間の出現率増加（絶対値）",
            })
            summary_rows.append({
                "metric": "B0_future_growth_ratio",
                "method": row["method"],
                "value": row["growth_ratio"],
                "description": "B0における将来期間の出現率比率（将来/過去）",
            })

    # 過去期間でのMethod Gap読み込み（検証）
    gap_path = tables_dir / "method_gap_by_period_publication.csv"
    if gap_path.exists():
        gap_df = pd.read_csv(gap_path)
        past_key = f"past({periods['past_start']}-{periods['past_end']})"
        past_gap = gap_df[gap_df["period"] == past_key]
        unet_gap = past_gap[past_gap["method"].str.lower().isin(["u-net", "unet"])]
        for _, row in unet_gap.iterrows():
            summary_rows.append({
                "metric": "past_gap_A0_minus_B0",
                "method": row["method"],
                "value": row["gap"],
                "description": f"過去期間({periods['past_start']}-{periods['past_end']})のA0-B0出現率差",
            })

    summary_df = pd.DataFrame(summary_rows)
    summary_out = tables_dir / "temporal_evaluation_summary.csv"
    summary_df.to_csv(summary_out, index=False, encoding="utf-8")
    logger.info(f"保存: {summary_out}")

    print("\n=== 後ろ向き評価サマリー ===")
    print(summary_df.to_string(index=False))

    logger.info("=== 08_temporal_evaluation.py 完了 ===")


if __name__ == "__main__":
    main()
