#!/usr/bin/env python3
"""
Preprocess exports2 publication-level CSV files into publication/family tables.

Input:
  pipeline/data/raw_exports2/{C0,S0,C1,S1}_orbis_publication_level.csv

Output:
  pipeline/data/processed_exports2/{domain}_publication_level.csv
  pipeline/data/processed_exports2/{domain}_family_level.csv
  pipeline/data/processed_exports2/dataset_summary_exports2.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any

import pandas as pd


UNET_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:U\s*-\s*Net|U\s+Net|UNet|nnU\s*-\s*Net|U\s*-\s*Net\+\+|UNet\+\+)(?![A-Za-z0-9])",
    re.IGNORECASE,
)

PUBLICATION_COLUMNS = [
    "publication_number",
    "family_id",
    "family_id_simple",
    "family_id_extended",
    "year",
    "filing_date",
    "publication_date",
    "priority_date",
    "title",
    "abstract",
    "claims",
    "title_abstract_text",
    "full_text",
    "applicant_names",
    "applicant_country_codes",
    "cpc_main",
    "cpc_others",
    "ipc_main",
    "ipc_others",
    "is_unet_raw",
    "is_unet_title_abstract",
    "is_unet_claims",
    "is_unet_full_text",
    "is_unet_final",
    "is_unet",
    "has_text",
    "domain",
    "source_files",
]

FAMILY_FIRST_COLUMNS = [
    "family_id_simple",
    "family_id_extended",
    "filing_date",
    "publication_date",
    "priority_date",
    "title",
    "abstract",
    "claims",
    "title_abstract_text",
    "full_text",
    "applicant_names",
    "applicant_country_codes",
    "cpc_main",
    "cpc_others",
    "ipc_main",
    "ipc_others",
    "domain",
]

FAMILY_COLUMNS = [
    "family_id",
    "patent_count",
    "year",
    *FAMILY_FIRST_COLUMNS,
    "is_unet_raw",
    "is_unet_title_abstract",
    "is_unet_claims",
    "is_unet_full_text",
    "is_unet_final",
    "is_unet",
    "has_text",
]


def as_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value)
    if text.lower() == "nan":
        return ""
    return text.strip()


def flag_unet_series(text: pd.Series) -> pd.Series:
    return text.fillna("").astype(str).str.contains(UNET_RE, na=False).astype(int)


def build_publication_chunk(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["publication_number"] = df.get("publication_number", "").fillna("").astype(str)
    out["family_id_simple"] = df.get("family_id_simple", "").fillna("").astype(str)
    out["family_id_extended"] = df.get("family_id_extended", "").fillna("").astype(str)
    out["family_id"] = out["family_id_simple"]
    missing_family = out["family_id"].str.strip().eq("")
    out.loc[missing_family, "family_id"] = out.loc[missing_family, "family_id_extended"]
    missing_family = out["family_id"].str.strip().eq("")
    out.loc[missing_family, "family_id"] = out.loc[missing_family, "publication_number"]

    out["filing_date"] = df.get("filing_date", "").fillna("").astype(str)
    out["publication_date"] = df.get("publication_date", "").fillna("").astype(str)
    out["priority_date"] = df.get("priority_date", "").fillna("").astype(str)
    out["year"] = pd.to_numeric(df.get("filing_year", 0), errors="coerce").fillna(0).astype(int)

    for col in ["title", "abstract", "claims", "applicant_names", "applicant_country_codes", "cpc_main", "cpc_others", "ipc_main", "ipc_others", "source_files"]:
        out[col] = df.get(col, "").fillna("").astype(str)

    out["title_abstract_text"] = (out["title"] + " " + out["abstract"]).str.strip()
    out["full_text"] = (out["title_abstract_text"] + " " + out["claims"]).str.strip()

    out["is_unet_raw"] = pd.to_numeric(df.get("is_unet", 0), errors="coerce").fillna(0).astype(int)
    out["is_unet_title_abstract"] = flag_unet_series(out["title_abstract_text"])
    out["is_unet_claims"] = flag_unet_series(out["claims"])
    out["is_unet_full_text"] = flag_unet_series(out["full_text"])
    out["is_unet_final"] = out["is_unet_title_abstract"]
    out["is_unet"] = out["is_unet_final"]
    out["has_text"] = (
        out["title"].str.strip().ne("") | out["abstract"].str.strip().ne("") | out["claims"].str.strip().ne("")
    )
    out["domain"] = domain
    return out[PUBLICATION_COLUMNS]


def update_family(families: dict[str, dict[str, Any]], row: dict[str, Any]) -> None:
    family_id = as_text(row.get("family_id")) or as_text(row.get("publication_number"))
    if family_id not in families:
        families[family_id] = {
            "family_id": family_id,
            "patent_count": 0,
            "year": 0,
            "is_unet_raw": 0,
            "is_unet_title_abstract": 0,
            "is_unet_claims": 0,
            "is_unet_full_text": 0,
            "is_unet_final": 0,
            "is_unet": 0,
            "has_text": False,
            **{col: "" for col in FAMILY_FIRST_COLUMNS},
        }

    fam = families[family_id]
    fam["patent_count"] += 1

    year = int(row.get("year") or 0)
    if year and (not fam["year"] or year < fam["year"]):
        fam["year"] = year

    for col in FAMILY_FIRST_COLUMNS:
        value = as_text(row.get(col))
        if value and not fam[col]:
            fam[col] = value

    for col in ["is_unet_raw", "is_unet_title_abstract", "is_unet_claims", "is_unet_full_text", "is_unet_final", "is_unet"]:
        fam[col] = max(int(fam[col]), int(row.get(col) or 0))
    fam["has_text"] = bool(fam["has_text"] or row.get("has_text"))


def preprocess_domain(raw_path: Path, out_dir: Path, domain: str, chunksize: int) -> dict[str, Any]:
    pub_out = out_dir / f"{domain}_publication_level.csv"
    fam_out = out_dir / f"{domain}_family_level.csv"
    families: dict[str, dict[str, Any]] = {}
    total = 0
    title_nonempty = 0
    abstract_nonempty = 0
    claims_nonempty = 0
    unet_total = 0
    seen_publications: set[str] = set()
    duplicate_publications = 0

    if pub_out.exists():
        pub_out.unlink()

    first_write = True
    for chunk in pd.read_csv(raw_path, chunksize=chunksize, dtype=str, keep_default_na=False):
        pub_df = build_publication_chunk(chunk, domain)
        total += len(pub_df)
        duplicate_publications += int(pub_df["publication_number"].isin(seen_publications).sum())
        seen_publications.update(pub_df["publication_number"].tolist())
        title_nonempty += int(pub_df["title"].str.strip().ne("").sum())
        abstract_nonempty += int(pub_df["abstract"].str.strip().ne("").sum())
        claims_nonempty += int(pub_df["claims"].str.strip().ne("").sum())
        unet_total += int(pub_df["is_unet_final"].sum())

        pub_df.to_csv(pub_out, index=False, encoding="utf-8", mode="w" if first_write else "a", header=first_write)
        first_write = False

        for row in pub_df.to_dict("records"):
            update_family(families, row)

    fam_df = pd.DataFrame(families.values(), columns=FAMILY_COLUMNS)
    fam_df.to_csv(fam_out, index=False, encoding="utf-8")

    return {
        "domain": domain,
        "publication_records": total,
        "unique_publications": len(seen_publications),
        "duplicate_publications": duplicate_publications,
        "family_records": len(fam_df),
        "title_nonempty_rate": round(title_nonempty / total, 6) if total else 0,
        "abstract_nonempty_rate": round(abstract_nonempty / total, 6) if total else 0,
        "claims_nonempty_rate": round(claims_nonempty / total, 6) if total else 0,
        "is_unet_final_count": unet_total,
        "is_unet_final_rate": round(unet_total / total, 6) if total else 0,
        "publication_output": str(pub_out),
        "family_output": str(fam_out),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess exports2 CSV files into publication/family tables.")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--raw-dir", default="pipeline/data/raw_exports2", help="Directory containing exports2 raw CSV files")
    parser.add_argument("--out-dir", default="pipeline/data/processed_exports2", help="Output directory")
    parser.add_argument("--domains", nargs="+", default=["C0", "S0", "C1", "S1"], choices=["C0", "S0", "C1", "S1"])
    parser.add_argument("--chunksize", type=int, default=2000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    raw_dir = (root / args.raw_dir).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict[str, Any]] = []
    for domain in args.domains:
        raw_path = raw_dir / f"{domain}_orbis_publication_level.csv"
        if not raw_path.exists():
            raise FileNotFoundError(raw_path)
        print(f"[{domain}] preprocessing {raw_path.name}", flush=True)
        summary = preprocess_domain(raw_path, out_dir, domain, args.chunksize)
        summaries.append(summary)
        print(f"[{domain}] {summary}", flush=True)

    summary_out = out_dir / "dataset_summary_exports2.csv"
    with summary_out.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)
    print(f"summary saved: {summary_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
