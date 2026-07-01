#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "pipeline/data/processed_heterogeneous"
OUT_DIR = PROJECT_ROOT / "pipeline/outputs/heterogeneous_clusters"

TEXT_COLUMNS = [
    "title",
    "abstract",
    "claims",
    "title_abstract_text",
    "full_text",
    "cpc_main",
    "cpc_others",
    "ipc_main",
    "ipc_others",
]

CLUSTER_ORDER = [
    "silicon_wafer_cleaning",
    "semiconductor_substrate_cleaning",
    "cmp_polishing_post_cleaning",
    "flux_electronic_component_cleaning",
    "photoresist_resin_mask_removal",
    "adhesive_cleaning",
    "circuit_board_cleaning",
]

S1_CLUSTER_BY_FAMILY = {
    "62150760": "silicon_wafer_cleaning",
    "67305382": "silicon_wafer_cleaning",
    "68337444": "silicon_wafer_cleaning",
    "62627454": "silicon_wafer_cleaning",
    "69098733": "semiconductor_substrate_cleaning",
    "76540853": "semiconductor_substrate_cleaning",
    "86539140": "semiconductor_substrate_cleaning",
    "71013302": "semiconductor_substrate_cleaning",
    "62707565": "cmp_polishing_post_cleaning",
    "74097753": "cmp_polishing_post_cleaning",
    "74097299": "cmp_polishing_post_cleaning",
    "75898261": "cmp_polishing_post_cleaning",
    "85514801": "cmp_polishing_post_cleaning",
    "70974716": "flux_electronic_component_cleaning",
    "70974735": "flux_electronic_component_cleaning",
    "78084566": "photoresist_resin_mask_removal",
    "1173244172": "photoresist_resin_mask_removal",
    "1158858571": "photoresist_resin_mask_removal",
    "93796082": "photoresist_resin_mask_removal",
    "88919422": "adhesive_cleaning",
    "89191379": "adhesive_cleaning",
    "89191399": "adhesive_cleaning",
    "99358725": "circuit_board_cleaning",
}

SEMICONDUCTOR_DIRECT_PATTERNS = {
    "semiconductor": r"semiconductor|semi[- ]?conductor|semi[- ]?conducteur|semicondutor|半導体|半導體",
    "wafer": r"\bwafer(?:s)?\b|ウェーハ|ウエハ|晶片|晶圓|晶圆|硅晶片|矽晶圓",
    "photoresist_or_resin_mask": r"photo[- ]?resist|resist mask|resin mask|レジスト|樹脂マスク|树脂掩膜|感光性樹脂",
    "cmp": r"\bCMP\b|chemical mechanical polishing|chemical-mechanical polishing|化学機械研磨|化學機械研磨",
    "semiconductor_class": r"\bH01L\b|\bH10[DKNP]\b",
}

SUBSTRATE_RE = re.compile(r"\bsubstrate(?:s)?\b|基板|基材|substrat|sustrato", re.IGNORECASE)


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, dtype=str, keep_default_na=False)


def coalesce_date(priority_date: pd.Series, filing_date: pd.Series) -> pd.Series:
    priority = priority_date.fillna("").astype(str).str.strip()
    filing = filing_date.fillna("").astype(str).str.strip()
    return priority.where(priority.ne(""), filing)


def add_family_first_date(family_df: pd.DataFrame, publication_df: pd.DataFrame) -> pd.DataFrame:
    pubs = publication_df.copy()
    pubs["date_basis"] = coalesce_date(pubs["priority_date"], pubs["filing_date"])
    pubs["_date_basis_dt"] = pd.to_datetime(pubs["date_basis"], errors="coerce")
    first = (
        pubs.dropna(subset=["_date_basis_dt"])
        .sort_values(["family_id_simple", "_date_basis_dt"])
        .groupby("family_id_simple", as_index=False)
        .first()[["family_id_simple", "date_basis"]]
        .rename(columns={"date_basis": "family_first_date"})
    )
    out = family_df.merge(first, on="family_id_simple", how="left")
    out["date_basis"] = coalesce_date(out["priority_date"], out["filing_date"])
    out["family_first_date"] = out["family_first_date"].where(
        out["family_first_date"].fillna("").astype(str).str.strip().ne(""),
        out["date_basis"],
    )
    return out


def joined_text(df: pd.DataFrame) -> pd.Series:
    existing = [col for col in TEXT_COLUMNS if col in df.columns]
    text = pd.Series("", index=df.index, dtype=str)
    for col in existing:
        text = (text + " " + df[col].fillna("").astype(str)).str.strip()
    return text


def match_direct_terms(text: str) -> str:
    hits = []
    for label, pattern in SEMICONDUCTOR_DIRECT_PATTERNS.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(label)
    return ";".join(hits)


def add_c1_exclusion_flags(c1_family: pd.DataFrame, s1_family_ids: set[str]) -> pd.DataFrame:
    out = c1_family.copy()
    text = joined_text(out)
    out["exclude_same_s1_family"] = out["family_id_simple"].isin(s1_family_ids).astype(int)
    out["semiconductor_direct_match_terms"] = text.map(match_direct_terms)
    out["contains_semiconductor_direct_term"] = (
        out["semiconductor_direct_match_terms"].str.strip().ne("")
    ).astype(int)
    out["contains_substrate_term"] = text.str.contains(SUBSTRATE_RE, na=False).astype(int)
    out["substrate_only_review_flag"] = (
        (out["contains_substrate_term"] == 1)
        & (out["contains_semiconductor_direct_term"] == 0)
    ).astype(int)
    out["c1_pre_base_keep"] = (
        (out["exclude_same_s1_family"] == 0)
        & (out["contains_semiconductor_direct_term"] == 0)
    ).astype(int)
    return out


def cluster_s1_family(s1_family: pd.DataFrame) -> pd.DataFrame:
    out = s1_family.copy()
    out["usage_cluster"] = out["family_id_simple"].map(S1_CLUSTER_BY_FAMILY).fillna("")
    missing = out[out["usage_cluster"].eq("")]
    if not missing.empty:
        missing_ids = ", ".join(missing["family_id_simple"].tolist())
        raise RuntimeError(f"S1 family cluster mapping missing for: {missing_ids}")
    out["usage_cluster"] = pd.Categorical(out["usage_cluster"], categories=CLUSTER_ORDER, ordered=True)
    return out.sort_values(["usage_cluster", "family_first_date", "family_id_simple"])


def build_cluster_summary(s1_clustered: pd.DataFrame) -> pd.DataFrame:
    work = s1_clustered.copy()
    work["_family_first_date_dt"] = pd.to_datetime(work["family_first_date"], errors="coerce")
    idx = work.sort_values(["usage_cluster", "_family_first_date_dt", "family_id_simple"]).groupby("usage_cluster").head(1).index
    reps = work.loc[idx].copy()
    reps["cluster_family_count"] = work.groupby("usage_cluster")["family_id_simple"].transform("count").loc[idx].values
    return reps[
        [
            "usage_cluster",
            "family_first_date",
            "family_id_simple",
            "title",
            "cluster_family_count",
        ]
    ].rename(
        columns={
            "family_first_date": "cluster_first_date",
            "family_id_simple": "representative_family_id_simple",
            "title": "representative_title",
        }
    )


def build_c1_pre_outputs(c1_flags: pd.DataFrame, cluster_summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    c1 = c1_flags.copy()
    c1["_family_first_date_dt"] = pd.to_datetime(c1["family_first_date"], errors="coerce")
    base = c1[(c1["c1_pre_base_keep"] == 1) & c1["_family_first_date_dt"].notna()].copy()

    overall_threshold = pd.to_datetime(cluster_summary["cluster_first_date"], errors="coerce").min()
    overall = base[base["_family_first_date_dt"] < overall_threshold].copy()
    overall["overall_s1_first_date"] = overall_threshold.date().isoformat()
    overall = overall.drop(columns=["_family_first_date_dt"])

    rows = []
    for cluster in cluster_summary.to_dict("records"):
        threshold = pd.to_datetime(cluster["cluster_first_date"], errors="coerce")
        subset = base[base["_family_first_date_dt"] < threshold].copy()
        subset["target_cluster"] = cluster["usage_cluster"]
        subset["cluster_first_date"] = cluster["cluster_first_date"]
        subset["cluster_representative_family_id_simple"] = cluster["representative_family_id_simple"]
        subset["cluster_representative_title"] = cluster["representative_title"]
        rows.append(subset)
    by_cluster = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if not by_cluster.empty:
        by_cluster = by_cluster.drop(columns=["_family_first_date_dt"])

    return overall, by_cluster


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    s1_publication = load_csv("S1_publication_level.csv")
    s1_family = load_csv("S1_family_level.csv")
    c1_publication = load_csv("C1_publication_level.csv")
    c1_family = load_csv("C1_family_level.csv")

    s1_family = add_family_first_date(s1_family, s1_publication)
    s1_clustered = cluster_s1_family(s1_family)
    cluster_summary = build_cluster_summary(s1_clustered)

    c1_family = add_family_first_date(c1_family, c1_publication)
    c1_flags = add_c1_exclusion_flags(c1_family, set(s1_family["family_id_simple"]))
    c1_overall, c1_by_cluster = build_c1_pre_outputs(c1_flags, cluster_summary)

    s1_clustered.to_csv(DATA_DIR / "S1_family_level_clustered.csv", index=False, encoding="utf-8")
    cluster_summary.to_csv(OUT_DIR / "S1_cluster_first_dates.csv", index=False, encoding="utf-8")
    c1_flags.to_csv(OUT_DIR / "C1_family_exclusion_flags.csv", index=False, encoding="utf-8")
    c1_overall.to_csv(OUT_DIR / "C1_pre_nonsemi_overall.csv", index=False, encoding="utf-8")
    c1_by_cluster.to_csv(OUT_DIR / "C1_pre_for_each_cluster.csv", index=False, encoding="utf-8")

    summary = pd.DataFrame(
        [
            {
                "metric": "s1_family_count",
                "value": len(s1_clustered),
            },
            {
                "metric": "s1_cluster_count",
                "value": s1_clustered["usage_cluster"].nunique(),
            },
            {
                "metric": "c1_family_count",
                "value": len(c1_flags),
            },
            {
                "metric": "c1_excluded_same_s1_family",
                "value": int(c1_flags["exclude_same_s1_family"].sum()),
            },
            {
                "metric": "c1_excluded_semiconductor_direct_term",
                "value": int(c1_flags["contains_semiconductor_direct_term"].sum()),
            },
            {
                "metric": "c1_substrate_only_review_flag",
                "value": int(c1_flags["substrate_only_review_flag"].sum()),
            },
            {
                "metric": "c1_pre_nonsemi_overall_count",
                "value": len(c1_overall),
            },
            {
                "metric": "c1_pre_for_each_cluster_rows",
                "value": len(c1_by_cluster),
            },
        ]
    )
    summary.to_csv(OUT_DIR / "s1_c1_preparation_summary.csv", index=False, encoding="utf-8")
    print(summary.to_string(index=False))
    print(cluster_summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
