"""
Script: 06_compute_method_gap.py
Purpose: 各技術手法のA0/B0間出現率差（Method Gap）を期間別に計算する。
         埋め込みなしでも動作する（頻度ベース計算のみ）。
Input:
  - data/processed/A0_with_methods.csv
  - data/processed/B0_with_methods.csv
  - data/processed/A0_family_level.csv
  - data/processed/B0_family_level.csv
Output:
  - outputs/tables/method_gap_by_period_publication.csv
  - outputs/tables/method_gap_by_period_family.csv
"""

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def method_to_col(method: str) -> str:
    return "is_" + re.sub(r'[^A-Za-z0-9]', '_', method).lower().strip('_')


def compute_method_gap(df_a: pd.DataFrame, df_b: pd.DataFrame,
                        methods: list, year_min: int, year_max: int,
                        period_label: str, epsilon: float) -> list:
    """
    期間でフィルタリングした後、各手法のGapを計算する。
    Returns: list of dicts
    """
    # 期間フィルタ
    if year_min is not None and year_max is not None:
        mask_a = (df_a["year"] >= year_min) & (df_a["year"] <= year_max)
        mask_b = (df_b["year"] >= year_min) & (df_b["year"] <= year_max)
        df_a_filt = df_a[mask_a]
        df_b_filt = df_b[mask_b]
    else:
        df_a_filt = df_a
        df_b_filt = df_b

    n_a = len(df_a_filt)
    n_b = len(df_b_filt)

    rows = []

    def count_rate(df: pd.DataFrame, method: str, col: str, n: int) -> tuple[int, float]:
        if method.lower() in ["u-net", "unet"]:
            unet_col = "is_unet_final" if "is_unet_final" in df.columns else "is_unet"
            if unet_col in df.columns:
                count = int(pd.to_numeric(df[unet_col], errors="coerce").fillna(0).sum())
                return count, count / n if n > 0 else 0.0
        if col in df.columns and df[col].dtype != object:
            count = int(df[col].sum()) if not df[col].isna().all() else 0
            return count, count / n if n > 0 else 0.0
        return 0, float("nan")

    for method in methods:
        col = method_to_col(method)

        count_a, rate_a = count_rate(df_a_filt, method, col, n_a)
        count_b, rate_b = count_rate(df_b_filt, method, col, n_b)

        if not (np.isnan(rate_a) or np.isnan(rate_b)):
            gap = rate_a - rate_b
            ratio = rate_a / (rate_b + epsilon)
        else:
            gap = float("nan")
            ratio = float("nan")

        rows.append({
            "period": period_label,
            "method": method,
            "n_A": n_a,
            "n_B": n_b,
            "count_A": count_a,  # A0での出現件数
            "count_B": count_b,  # B0での出現件数
            "rate_A": round(rate_a, 6) if not np.isnan(rate_a) else float("nan"),  # A0出現率
            "rate_B": round(rate_b, 6) if not np.isnan(rate_b) else float("nan"),  # B0出現率
            "gap": round(gap, 6) if not np.isnan(gap) else float("nan"),           # 出現率差
            "ratio": round(ratio, 4) if not np.isnan(ratio) else float("nan"),     # 比率
        })

    return rows


def main():
    parser = argparse.ArgumentParser(description="Method Gap の計算")
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
    log_file = log_dir / f"06_compute_method_gap_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 06_compute_method_gap.py 開始 ===")

    processed_dir = script_dir / cfg["data"]["processed_dir"]
    tables_dir = script_dir / cfg["data"]["output_dir"] / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    periods = cfg["periods"]
    epsilon = cfg["scoring"]["epsilon"]
    methods = cfg["methods"]["target_methods"]

    period_defs = {
        f"past({periods['past_start']}-{periods['past_end']})": (periods["past_start"], periods["past_end"]),
        f"future({periods['future_start']}-{periods['future_end']})": (periods["future_start"], periods["future_end"]),
        f"all({periods['all_start']}-{periods['all_end']})": (periods["all_start"], periods["all_end"]),
    }

    for level in ["publication", "family"]:
        suffix = "with_methods" if level == "publication" else "family_level"
        in_a = processed_dir / f"A0_{suffix}.csv"
        in_b = processed_dir / f"B0_{suffix}.csv"

        if not in_a.exists():
            # フォールバック
            in_a = processed_dir / f"A0_publication_level.csv"
            logger.warning(f"with_methods ファイルが存在しないため publication_level を使用します: {in_a}")
        if not in_b.exists():
            in_b = processed_dir / f"B0_publication_level.csv"

        if not in_a.exists() or not in_b.exists():
            logger.error(f"[{level}] 入力ファイルが存在しません。スキップします。")
            continue

        df_a = pd.read_csv(in_a)
        df_b = pd.read_csv(in_b)
        logger.info(f"[{level}] A0: {len(df_a)}行, B0: {len(df_b)}行")

        if args.sample:
            df_a = df_a.sample(min(args.sample, len(df_a)), random_state=42).reset_index(drop=True)
            df_b = df_b.sample(min(args.sample, len(df_b)), random_state=42).reset_index(drop=True)

        all_rows = []
        for period_label, (y_min, y_max) in period_defs.items():
            rows = compute_method_gap(df_a, df_b, methods, y_min, y_max, period_label, epsilon)
            all_rows.extend(rows)
            logger.info(f"[{level}/{period_label}] {len(rows)} 手法を計算")

        result_df = pd.DataFrame(all_rows)
        out_path = tables_dir / f"method_gap_by_period_{level}.csv"
        result_df.to_csv(out_path, index=False, encoding="utf-8")
        logger.info(f"[{level}] 保存: {out_path}")

        print(f"\n=== Method Gap ({level}) ===")
        # 過去期間のみ表示
        past_key = f"past({periods['past_start']}-{periods['past_end']})"
        past_df = result_df[result_df["period"] == past_key].sort_values("gap", ascending=False)
        print(past_df[["method", "count_A", "count_B", "rate_A", "rate_B", "gap", "ratio"]].to_string(index=False))

    logger.info("=== 06_compute_method_gap.py 完了 ===")


if __name__ == "__main__":
    main()
