"""
Script: 00_check_columns.py
Purpose: CSVやXLSXファイルの列構造を確認し、パイプラインで利用可能な列をレポートする。
Input:   config.yaml で指定されたCSV/XLSXファイル（またはコマンドライン指定ファイル）
Output:  outputs/logs/column_check.json
"""

import argparse
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml


# --------------------------------------------------------------------------- #
# 列名の正規化マッピング                                                        #
# --------------------------------------------------------------------------- #
KNOWN_ALIASES = {
    "publication_number": [
        "Publication number", "publication_number", "PublicationNumber",
        "pub_number", "pub_no", "patent_number", "PatentNumber",
    ],
    "family_id": [
        "family_idx", "family_id", "FamilyId", "FamilyID", "PatentFamily",
        "family_index", "family_id_simple", "family_id_extended",
        "Family Identifier (Simple)", "Family Identifier (Extended)",
    ],
    "year": [
        "year", "Year", "publication_year", "PublicationYear",
        "filing_year", "FilingYear", "priority_year",
    ],
    "title": [
        "title", "Title", "invention_title", "InventionTitle",
        "patent_title", "PatentTitle",
    ],
    "abstract": [
        "abstract", "Abstract", "patent_abstract", "PatentAbstract",
    ],
    "claims": [
        "claims", "Claims", "patent_claims", "PatentClaims",
    ],
    "is_unet": [
        "is_unet", "IsUnet", "unet_flag", "unet",
    ],
}


def normalize_columns(columns: list) -> dict:
    """実際の列名を正規化名にマッピングして返す。"""
    col_map = {}
    for norm_name, aliases in KNOWN_ALIASES.items():
        for alias in aliases:
            for col in columns:
                if col.strip().lower() == alias.strip().lower():
                    col_map[norm_name] = col
                    break
            if norm_name in col_map:
                break
    return col_map


def check_file(filepath: str, label: str, logger: logging.Logger) -> dict:
    """単一ファイルの列チェック結果を辞書で返す。"""
    result = {
        "label": label,
        "filepath": filepath,
        "exists": False,
        "columns": [],
        "nrows": None,
        "column_map": {},
        "missing_important": [],
        "summary": {},
    }

    if not os.path.exists(filepath):
        logger.warning(f"[{label}] ファイルが存在しません: {filepath}")
        return result

    result["exists"] = True
    ext = Path(filepath).suffix.lower()

    try:
        if ext == ".csv":
            df = pd.read_csv(filepath, nrows=5)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(filepath, nrows=5)
        else:
            logger.error(f"[{label}] 未対応のファイル形式: {ext}")
            return result
    except Exception as e:
        logger.error(f"[{label}] 読み込みエラー: {e}")
        return result

    result["columns"] = list(df.columns)
    result["column_map"] = normalize_columns(list(df.columns))

    # 行数（全体）
    try:
        if ext == ".csv":
            full_df = pd.read_csv(filepath)
        else:
            full_df = pd.read_excel(filepath)
        result["nrows"] = len(full_df)

        # 統計サマリー（year/is_unetがあれば）
        col_map = result["column_map"]
        if "year" in col_map:
            yr_col = col_map["year"]
            result["summary"]["year_min"] = int(full_df[yr_col].min())
            result["summary"]["year_max"] = int(full_df[yr_col].max())
            result["summary"]["year_counts"] = full_df[yr_col].value_counts().sort_index().to_dict()
        if "is_unet" in col_map:
            iu_col = col_map["is_unet"]
            result["summary"]["is_unet_total"] = int(full_df[iu_col].sum())
            result["summary"]["is_unet_rate"] = float(full_df[iu_col].mean())
        if "family_id" in col_map:
            fi_col = col_map["family_id"]
            result["summary"]["unique_families"] = int(full_df[fi_col].nunique())

    except Exception as e:
        logger.warning(f"[{label}] 統計計算エラー: {e}")

    # 重要な列の欠損チェック
    important_cols = ["year", "family_id", "title", "abstract", "claims"]
    result["missing_important"] = [c for c in important_cols if c not in result["column_map"]]

    logger.info(f"[{label}] OK: {len(result['columns'])} 列, {result['nrows']} 行")
    logger.info(f"[{label}] 列マッピング: {result['column_map']}")
    if result["missing_important"]:
        logger.warning(f"[{label}] 重要列なし（テキストなしモードで動作します）: {result['missing_important']}")

    return result


def main():
    parser = argparse.ArgumentParser(description="CSVやXLSXの列構造を確認する")
    parser.add_argument("--config", default="config/config.yaml", help="設定ファイルパス")
    parser.add_argument("--input", nargs="*", help="追加でチェックするファイルパス（省略可）")
    parser.add_argument("--sample", type=int, default=None, help="確認する件数上限（省略可、列チェックのみで使用しない）")
    args = parser.parse_args()

    # config 読み込み
    config_path = Path(args.config)
    script_dir = Path(__file__).parent.parent  # pipeline/
    if not config_path.is_absolute():
        config_path = script_dir / config_path

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    # ログ設定
    log_dir = script_dir / cfg["data"]["output_dir"] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"00_check_columns_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 00_check_columns.py 開始 ===")

    # チェック対象ファイル
    files_to_check = []
    data_cfg = cfg["data"]

    def resolve(rel_path: str) -> str:
        p = Path(rel_path)
        if not p.is_absolute():
            p = script_dir / p
        return str(p)

    for key, label in [
        ("a0_csv", "A0_CSV"),
        ("b0_csv", "B0_CSV"),
        ("a0_xlsx", "A0_XLSX"),
        ("b0_xlsx", "B0_XLSX"),
    ]:
        if data_cfg.get(key):
            files_to_check.append((resolve(data_cfg[key]), label))

    if args.input:
        for fp in args.input:
            files_to_check.append((fp, Path(fp).name))

    # 各ファイルをチェック
    all_results = {}
    for filepath, label in files_to_check:
        result = check_file(filepath, label, logger)
        all_results[label] = result

    # 出力
    out_path = log_dir / "column_check.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"結果を保存: {out_path}")

    # コンソールサマリー
    print("\n=== チェック結果サマリー ===")
    for label, res in all_results.items():
        exists_str = "存在" if res["exists"] else "不存在"
        nrows_str = f"{res['nrows']}行" if res["nrows"] is not None else "不明"
        print(f"  [{label}] {exists_str} | {nrows_str} | 列数:{len(res['columns'])}")
        if res["column_map"]:
            print(f"          マッピング: {res['column_map']}")
        if res["missing_important"]:
            print(f"          欠損重要列: {res['missing_important']} → テキストなしモード")
        if res.get("summary"):
            for k, v in res["summary"].items():
                if k != "year_counts":
                    print(f"          {k}: {v}")

    logger.info("=== 00_check_columns.py 完了 ===")


if __name__ == "__main__":
    main()
