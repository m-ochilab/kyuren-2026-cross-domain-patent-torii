"""
Script: 01_preprocess_patents.py
Purpose: A0/B0のCSV（またはXLSX）データを読み込み、前処理してPublication/Familyレベルで保存する。
         テキスト列がない場合はplaceholderを設定してテキストなしモードで動作する。
Input:   config.yaml で指定されたCSV/XLSXファイル
Output:
  - data/processed/A0_publication_level.csv
  - data/processed/B0_publication_level.csv
  - data/processed/A0_family_level.csv
  - data/processed/B0_family_level.csv
  - outputs/tables/dataset_summary.csv
"""

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

UNET_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:U\s*-\s*Net|U\s+Net|UNet|nnU\s*-\s*Net|U\s*-\s*Net\+\+|UNet\+\+)(?![A-Za-z0-9])",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# 列名エイリアス（00_check_columns.py と同じ定義）                               #
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


def flag_unet(text: pd.Series) -> pd.Series:
    return text.fillna("").astype(str).str.contains(UNET_RE, na=False).astype(int)


def choose_unet_final(pub_df: pd.DataFrame, cfg: dict) -> pd.Series:
    source = cfg.get("methods", {}).get("unet_final_source", "title_abstract")
    source_map = {
        "title_abstract": "is_unet_title_abstract",
        "claims": "is_unet_claims",
        "full_text": "is_unet_full_text",
        "raw": "is_unet_raw",
    }
    col = source_map.get(source, "is_unet_title_abstract")
    return pub_df[col] if col in pub_df.columns else pub_df["is_unet_title_abstract"]


def normalize_columns(columns: list) -> dict:
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


def load_data(filepath: str, logger: logging.Logger, nrows: int | None = None) -> pd.DataFrame:
    """CSVまたはXLSXを読み込む。"""
    p = Path(filepath)
    if not p.exists():
        logger.warning(f"ファイルが存在しません: {filepath}")
        return None
    ext = p.suffix.lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(filepath, nrows=nrows)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(filepath, nrows=nrows)
        else:
            logger.error(f"未対応の形式: {ext}")
            return None
        suffix = f", nrows={nrows}" if nrows else ""
        logger.info(f"読み込み完了: {filepath} ({len(df)}行, {len(df.columns)}列{suffix})")
        return df
    except Exception as e:
        logger.error(f"読み込みエラー: {filepath} — {e}")
        return None


def preprocess_domain(df: pd.DataFrame, domain: str, sample_n: int,
                       cfg: dict, logger: logging.Logger) -> tuple:
    """
    DataFrameを前処理してPublication/Familyレベルを返す。
    Returns: (pub_df, fam_df)
    """
    col_map = normalize_columns(list(df.columns))
    logger.info(f"[{domain}] 列マッピング: {col_map}")

    # サンプリング
    if sample_n and sample_n < len(df):
        df = df.sample(n=sample_n, random_state=cfg["sample"]["seed"]).reset_index(drop=True)
        logger.info(f"[{domain}] サンプリング後: {len(df)}行")

    # --- 必須列の正規化 ---
    pub_df = pd.DataFrame()

    # publication_number
    if "publication_number" in col_map:
        pub_df["publication_number"] = df[col_map["publication_number"]].astype(str)
    else:
        pub_df["publication_number"] = [f"{domain}_{i}" for i in range(len(df))]

    # family_id
    if "family_id" in col_map:
        pub_df["family_id"] = df[col_map["family_id"]]
    else:
        pub_df["family_id"] = range(len(df))

    # year
    if "year" in col_map:
        pub_df["year"] = pd.to_numeric(df[col_map["year"]], errors="coerce").fillna(0).astype(int)
    else:
        pub_df["year"] = 0
        logger.warning(f"[{domain}] year列なし — 0で埋めます")

    # is_unet_raw: 元CSV由来のU-Net判定。再構築済みrawではTitle/Abstract由来。
    if "is_unet" in col_map:
        pub_df["is_unet_raw"] = pd.to_numeric(df[col_map["is_unet"]], errors="coerce").fillna(0).astype(int)
    else:
        pub_df["is_unet_raw"] = 0
        logger.warning(f"[{domain}] is_unet列なし — 0で埋めます")

    # テキスト列（なければ空文字）
    has_text = False
    for col in ["title", "abstract", "claims"]:
        if col in col_map:
            pub_df[col] = df[col_map[col]].fillna("").astype(str)
            has_text = True
        else:
            pub_df[col] = ""

    # full_text / title_abstract_text
    pub_df["full_text"] = (
        pub_df["title"] + " " + pub_df["abstract"] + " " + pub_df["claims"]
    ).str.strip()
    pub_df["title_abstract_text"] = (
        pub_df["title"] + " " + pub_df["abstract"]
    ).str.strip()

    pub_df["is_unet_title_abstract"] = flag_unet(pub_df["title_abstract_text"])
    pub_df["is_unet_claims"] = flag_unet(pub_df["claims"])
    pub_df["is_unet_full_text"] = flag_unet(pub_df["full_text"])
    pub_df["is_unet_final"] = choose_unet_final(pub_df, cfg).astype(int)
    # 既存スクリプトとの互換性のため、is_unet は最終判定を指す。
    pub_df["is_unet"] = pub_df["is_unet_final"]
    pub_df["has_text"] = has_text

    pub_df["domain"] = domain

    # --- Family Level ---
    agg_dict = {
        "is_unet": "max",       # いずれか1 publicationでも該当すれば1
        "is_unet_raw": "max",
        "is_unet_title_abstract": "max",
        "is_unet_claims": "max",
        "is_unet_full_text": "max",
        "is_unet_final": "max",
        "year": "min",          # 最初の出願年
        "full_text": "first",
        "title_abstract_text": "first",
        "title": "first",
        "abstract": "first",
        "claims": "first",
        "has_text": "first",
        "domain": "first",
        "publication_number": "count",  # ファミリー内の特許数
    }
    fam_df = (
        pub_df.groupby("family_id", as_index=False)
        .agg(agg_dict)
        .rename(columns={"publication_number": "patent_count"})
    )

    logger.info(f"[{domain}] Publication: {len(pub_df)}行, Family: {len(fam_df)}行")
    logger.info(f"[{domain}] テキストあり: {has_text}")
    logger.info(
        f"[{domain}] is_unet_final=1: {pub_df['is_unet_final'].sum()} "
        f"({pub_df['is_unet_final'].mean()*100:.1f}%)"
    )
    logger.info(
        f"[{domain}] U-Net判定内訳: "
        f"title_abstract={int(pub_df['is_unet_title_abstract'].sum())}, "
        f"claims={int(pub_df['is_unet_claims'].sum())}, "
        f"full_text={int(pub_df['is_unet_full_text'].sum())}"
    )

    return pub_df, fam_df


def main():
    parser = argparse.ArgumentParser(description="特許データの前処理")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--sample", type=int, default=None, help="処理件数上限")
    parser.add_argument("--processed-dir", default=None, help="出力先processedディレクトリ（configより優先）")
    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent  # pipeline/
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = script_dir / config_path

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    # ログ設定
    log_dir = script_dir / cfg["data"]["output_dir"] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"01_preprocess_patents_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 01_preprocess_patents.py 開始 ===")

    processed_dir = Path(args.processed_dir) if args.processed_dir else Path(cfg["data"]["processed_dir"])
    if not processed_dir.is_absolute():
        processed_dir = script_dir / processed_dir
    processed_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = script_dir / cfg["data"]["output_dir"] / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    def resolve(rel: str | None) -> str | None:
        if not rel:
            return None
        p = Path(rel)
        return str(p if p.is_absolute() else script_dir / p)

    sample_n = args.sample or (cfg["sample"]["n"] if cfg["sample"]["enabled"] else None)

    summary_rows = []
    domains = [("A0", resolve(cfg["data"].get("a0_csv")), resolve(cfg["data"].get("a0_xlsx"))),
               ("B0", resolve(cfg["data"].get("b0_csv")), resolve(cfg["data"].get("b0_xlsx")))]

    for domain, csv_path, xlsx_path in domains:
        # CSV優先、なければXLSX
        df = load_data(csv_path, logger, nrows=sample_n)
        source = "CSV"
        if df is None and xlsx_path:
            df = load_data(xlsx_path, logger, nrows=sample_n)
            source = "XLSX"
        if df is None:
            logger.error(f"[{domain}] データを読み込めませんでした。スキップします。")
            continue

        logger.info(f"[{domain}] ソース: {source}")
        pub_df, fam_df = preprocess_domain(df, domain, sample_n, cfg, logger)

        # 保存
        pub_out = processed_dir / f"{domain}_publication_level.csv"
        fam_out = processed_dir / f"{domain}_family_level.csv"
        pub_df.to_csv(pub_out, index=False, encoding="utf-8")
        fam_df.to_csv(fam_out, index=False, encoding="utf-8")
        logger.info(f"[{domain}] 保存: {pub_out}")
        logger.info(f"[{domain}] 保存: {fam_out}")

        # サマリー行
        periods = cfg["periods"]
        past_mask = (pub_df["year"] >= periods["past_start"]) & (pub_df["year"] <= periods["past_end"])
        future_mask = (pub_df["year"] >= periods["future_start"]) & (pub_df["year"] <= periods["future_end"])

        summary_rows.append({
            "domain": domain,
            "level": "publication",
            "total_records": len(pub_df),
            "past_records": int(past_mask.sum()),
            "future_records": int(future_mask.sum()),
            "is_unet_total": int(pub_df["is_unet"].sum()),
            "is_unet_rate": round(pub_df["is_unet"].mean(), 4),
            "is_unet_past": int(pub_df.loc[past_mask, "is_unet"].sum()),
            "is_unet_future": int(pub_df.loc[future_mask, "is_unet"].sum()),
            "has_text": bool(pub_df["has_text"].iloc[0]) if len(pub_df) > 0 else False,
        })
        summary_rows.append({
            "domain": domain,
            "level": "family",
            "total_records": len(fam_df),
            "past_records": int(((fam_df["year"] >= periods["past_start"]) & (fam_df["year"] <= periods["past_end"])).sum()),
            "future_records": int(((fam_df["year"] >= periods["future_start"]) & (fam_df["year"] <= periods["future_end"])).sum()),
            "is_unet_total": int(fam_df["is_unet"].sum()),
            "is_unet_rate": round(fam_df["is_unet"].mean(), 4),
            "is_unet_past": int(fam_df.loc[(fam_df["year"] >= periods["past_start"]) & (fam_df["year"] <= periods["past_end"]), "is_unet"].sum()),
            "is_unet_future": int(fam_df.loc[(fam_df["year"] >= periods["future_start"]) & (fam_df["year"] <= periods["future_end"]), "is_unet"].sum()),
            "has_text": bool(fam_df["has_text"].iloc[0]) if len(fam_df) > 0 else False,
        })

    # データセットサマリー保存
    summary_df = pd.DataFrame(summary_rows)
    summary_out = tables_dir / "dataset_summary.csv"
    summary_df.to_csv(summary_out, index=False, encoding="utf-8")
    logger.info(f"サマリー保存: {summary_out}")

    print("\n=== データセットサマリー ===")
    print(summary_df.to_string(index=False))

    logger.info("=== 01_preprocess_patents.py 完了 ===")


if __name__ == "__main__":
    main()
