"""
Script: 02_extract_method_terms.py
Purpose: 特許テキストから技術手法語（U-Net, YOLO, GANなど）の有無を抽出する。
         テキスト列がない場合は is_unet フラグのみを使用してテキストなしモードで動作する。
Input:
  - data/processed/A0_publication_level.csv
  - data/processed/B0_publication_level.csv
Output:
  - data/processed/A0_with_methods.csv
  - data/processed/B0_with_methods.csv
  - outputs/tables/method_counts_by_domain.csv
  - outputs/tables/method_counts_by_year.csv
"""

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml


def build_pattern(method: str) -> re.Pattern:
    """手法名の正規表現パターンを構築する（単語境界・大文字小文字対応）。"""
    escaped = re.escape(method)
    # U-Net++, nnU-Net などハイフンや+を含む場合は単語境界が機能しないため
    # 前後に非英数字または文字列境界を要求
    pattern = r'(?<![A-Za-z0-9])' + escaped + r'(?![A-Za-z0-9])'
    return re.compile(pattern, re.IGNORECASE)


def method_to_col(method: str) -> str:
    """手法名を列名に変換する。"""
    return "is_" + re.sub(r'[^A-Za-z0-9]', '_', method).lower().strip('_')


def extract_methods_from_text(text: str, patterns: dict) -> dict:
    """テキストから手法フラグを抽出する。"""
    flags = {}
    if not isinstance(text, str) or text.strip() == "":
        return {col: 0 for col in patterns.keys()}
    for col, pattern in patterns.items():
        flags[col] = 1 if pattern.search(text) else 0
    return flags


def main():
    parser = argparse.ArgumentParser(description="技術手法語の抽出")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument("--processed-dir", default=None, help="入出力processedディレクトリ（configより優先）")
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
    log_file = log_dir / f"02_extract_method_terms_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 02_extract_method_terms.py 開始 ===")

    processed_dir = Path(args.processed_dir) if args.processed_dir else Path(cfg["data"]["processed_dir"])
    if not processed_dir.is_absolute():
        processed_dir = script_dir / processed_dir
    tables_dir = script_dir / cfg["data"]["output_dir"] / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    target_methods = cfg["methods"]["target_methods"]
    unet_variants = cfg["methods"]["unet_variants"]

    # 手法パターン辞書 {列名: パターン}
    patterns = {}
    for method in target_methods:
        if method.lower() in {"u-net", "unet"}:
            continue
        col = method_to_col(method)
        patterns[col] = build_pattern(method)

    # U-Net variantsの統合パターン
    unet_pattern = re.compile(
        r'(?<![A-Za-z0-9])(' +
        '|'.join(re.escape(v) for v in unet_variants) +
        r')(?![A-Za-z0-9])',
        re.IGNORECASE
    )

    all_domain_counts = []
    all_year_counts = []

    for domain in ["A0", "B0"]:
        in_path = processed_dir / f"{domain}_publication_level.csv"
        if not in_path.exists():
            logger.error(f"[{domain}] 入力ファイルが存在しません: {in_path}")
            logger.error("先に 01_preprocess_patents.py を実行してください。")
            continue

        df = pd.read_csv(in_path)
        logger.info(f"[{domain}] 読み込み: {len(df)}行")

        if args.sample and args.sample < len(df):
            df = df.sample(n=args.sample, random_state=42).reset_index(drop=True)
            logger.info(f"[{domain}] サンプリング: {len(df)}行")

        has_text = bool(df.get("has_text", pd.Series([False])).iloc[0])
        logger.info(f"[{domain}] テキストあり: {has_text}")

        if has_text:
            # 候補手法全般はTitle/Abstract/Claimsから抽出する。
            method_text_col = "full_text" if "full_text" in df.columns else "title_abstract_text"
            logger.info(f"[{domain}] 手法語テキスト列: {method_text_col}")

            method_flags_list = []
            for idx, row in df.iterrows():
                method_text = row.get(method_text_col, "")
                flags = extract_methods_from_text(method_text, patterns)
                if "is_unet_title_abstract" not in df.columns:
                    flags["is_unet_title_abstract"] = 1 if unet_pattern.search(str(row.get("title_abstract_text", ""))) else 0
                if "is_unet_claims" not in df.columns:
                    flags["is_unet_claims"] = 1 if unet_pattern.search(str(row.get("claims", ""))) else 0
                if "is_unet_full_text" not in df.columns:
                    flags["is_unet_full_text"] = 1 if unet_pattern.search(str(row.get("full_text", ""))) else 0
                method_flags_list.append(flags)

            flags_df = pd.DataFrame(method_flags_list, index=df.index)
            for col in flags_df.columns:
                if col != "is_unet":
                    df[col] = flags_df[col]
            if "is_unet_final" not in df.columns:
                df["is_unet_final"] = df.get("is_unet_title_abstract", pd.Series(0, index=df.index))
            df["is_unet"] = df["is_unet_final"]
        else:
            # テキストなしモード: is_unet フラグのみ使用
            logger.info(f"[{domain}] テキストなしモード: is_unet フラグのみ使用")
            for col in patterns.keys():
                if col == "is_u_net" or col == "is_unet":
                    # すでにある is_unet をそのまま使う
                    if col not in df.columns:
                        df[col] = 0
                else:
                    df[col] = float("nan")  # 不明

        # 出力
        out_path = processed_dir / f"{domain}_with_methods.csv"
        df.to_csv(out_path, index=False, encoding="utf-8")
        logger.info(f"[{domain}] 保存: {out_path}")

        # 手法別カウント
        method_cols = [c for c in df.columns if c.startswith("is_")]
        domain_counts = {"domain": domain}
        for col in method_cols:
            if df[col].dtype == float:
                domain_counts[col] = "N/A (no text)"
            else:
                domain_counts[col] = int(df[col].sum())
        all_domain_counts.append(domain_counts)
        logger.info(f"[{domain}] 手法カウント: {domain_counts}")

        # 年別カウント
        if "year" in df.columns and has_text:
            year_grp = df.groupby("year")[method_cols].sum().reset_index()
            year_grp["domain"] = domain
            all_year_counts.append(year_grp)

    # method_counts_by_domain.csv
    if all_domain_counts:
        domain_df = pd.DataFrame(all_domain_counts)
        domain_out = tables_dir / "method_counts_by_domain.csv"
        domain_df.to_csv(domain_out, index=False, encoding="utf-8")
        logger.info(f"保存: {domain_out}")
        print("\n=== 手法別カウント（ドメイン別）===")
        print(domain_df.to_string(index=False))

    # method_counts_by_year.csv
    if all_year_counts:
        year_df = pd.concat(all_year_counts, ignore_index=True)
        year_out = tables_dir / "method_counts_by_year.csv"
        year_df.to_csv(year_out, index=False, encoding="utf-8")
        logger.info(f"保存: {year_out}")

    logger.info("=== 02_extract_method_terms.py 完了 ===")


if __name__ == "__main__":
    main()
