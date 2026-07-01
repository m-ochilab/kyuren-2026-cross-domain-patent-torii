#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLUSTER_DIR = PROJECT_ROOT / "pipeline/outputs/heterogeneous_clusters"
DATA_DIR = PROJECT_ROOT / "pipeline/data/processed_heterogeneous"
TOP_K = 50
MANUAL_REVIEW_TOP_N = 20

CLUSTER_USAGE_TERMS = {
    "silicon_wafer_cleaning": [
        "silicon wafer",
        "wafer cleaning",
        "rinse",
        "particle removal",
    ],
    "semiconductor_substrate_cleaning": [
        "semiconductor substrate",
        "semiconductor device substrate",
        "substrate cleaning",
    ],
    "cmp_polishing_post_cleaning": [
        "CMP",
        "post-CMP",
        "chemical mechanical polishing",
        "slurry",
        "polishing residue",
        "residue removal",
    ],
    "flux_electronic_component_cleaning": [
        "flux",
        "solder",
        "electronic parts",
        "mounting",
        "printed circuit",
    ],
    "photoresist_resin_mask_removal": [
        "photoresist",
        "resist",
        "resin mask",
        "copper corrosion",
        "removal",
    ],
    "adhesive_cleaning": [
        "adhesive",
        "bonding",
        "temporary fixing",
        "resin residue",
    ],
    "circuit_board_cleaning": [
        "circuit board",
        "printed wiring board",
        "PCB",
        "solder",
        "flux residue",
    ],
}

TEXT_COLUMNS_FOR_FILTER = [
    "title",
    "problem_context",
    "solution_context",
    "technical_means",
    "text_for_embedding",
    "cpc_main",
    "cpc_others",
    "ipc_main",
    "ipc_others",
]


def compact_text(series: pd.Series, limit: int = 1200) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.slice(0, limit)
    )


def joined_text(df: pd.DataFrame) -> pd.Series:
    text = pd.Series("", index=df.index, dtype=str)
    for col in TEXT_COLUMNS_FOR_FILTER:
        if col in df.columns:
            text = (text + " " + df[col].fillna("").astype(str)).str.strip()
    return text.str.replace(r"\s+", " ", regex=True).str.strip()


def term_pattern(term: str) -> re.Pattern:
    escaped = re.escape(term).replace(r"\ ", r"[\s\-/]*")
    if term.upper() in {"CMP", "PCB"}:
        return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


def filter_s0_by_usage_terms(s0_pre: pd.DataFrame) -> pd.DataFrame:
    out_frames = []
    for cluster, terms in CLUSTER_USAGE_TERMS.items():
        subset = s0_pre[s0_pre["target_cluster"] == cluster].copy()
        text = joined_text(subset)
        matched_terms = []
        keep = pd.Series(False, index=subset.index)
        patterns = [(term, term_pattern(term)) for term in terms]

        for idx, value in text.items():
            hits = [term for term, pattern in patterns if pattern.search(value)]
            matched_terms.append("; ".join(hits))
            if hits:
                keep.loc[idx] = True

        subset["usage_filter_terms"] = "; ".join(terms)
        subset["matched_usage_terms"] = matched_terms
        subset["usage_filter_keep"] = keep.astype(int).values
        out_frames.append(subset[subset["usage_filter_keep"] == 1].copy())

    return pd.concat(out_frames, ignore_index=True) if out_frames else pd.DataFrame()


def ensure_c1_context(c1_pre: pd.DataFrame, enriched_ranking: pd.DataFrame) -> pd.DataFrame:
    context_cols = ["problem_context", "solution_context", "technical_means"]
    if all(col in c1_pre.columns for col in context_cols):
        return c1_pre

    key_cols = ["target_cluster", "family_id_simple"]
    enrich_cols = key_cols + [col for col in context_cols if col in enriched_ranking.columns]
    enriched = enriched_ranking[enrich_cols].drop_duplicates(key_cols)
    return c1_pre.merge(enriched, on=key_cols, how="left")


def fit_vectors(s0_filtered: pd.DataFrame, c1_pre: pd.DataFrame):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    s0_text = s0_filtered["problem_context"].fillna("").astype(str)
    s0_text = s0_text.where(s0_text.str.strip().ne(""), s0_filtered["text_for_embedding"].fillna("").astype(str))

    c1_text = c1_pre["problem_context"].fillna("").astype(str)
    c1_text = c1_text.where(c1_text.str.strip().ne(""), c1_pre.get("full_text", "").fillna("").astype(str))

    corpus = pd.concat([s0_text, c1_text], ignore_index=True)
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
        max_features=30000,
        lowercase=True,
        norm="l2",
    )
    matrix = vectorizer.fit_transform(corpus)
    s0_vec = normalize(matrix[: len(s0_filtered)], norm="l2", copy=False)
    c1_vec = normalize(matrix[len(s0_filtered):], norm="l2", copy=False)
    return s0_vec, c1_vec


def rank_c1_by_filtered_s0(s0_filtered: pd.DataFrame, c1_pre: pd.DataFrame) -> pd.DataFrame:
    s0_vec, c1_vec = fit_vectors(s0_filtered, c1_pre)
    s0 = s0_filtered.reset_index(drop=True).copy()
    c1 = c1_pre.reset_index(drop=True).copy()
    frames = []

    for cluster in CLUSTER_USAGE_TERMS:
        s0_idx = s0.index[s0["target_cluster"] == cluster].to_numpy()
        c1_idx = c1.index[c1["target_cluster"] == cluster].to_numpy()
        if len(s0_idx) == 0 or len(c1_idx) == 0:
            continue

        query = np.asarray(s0_vec[s0_idx].mean(axis=0))
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            sims = np.zeros(len(c1_idx), dtype=float)
        else:
            query = query / query_norm
            sims = np.asarray(c1_vec[c1_idx] @ query.T).ravel()

        ranked = c1.iloc[c1_idx].copy()
        ranked["problem_similarity_to_filtered_s0_centroid"] = sims
        ranked["s0_pre_filtered_family_count_for_cluster"] = len(s0_idx)
        ranked["c1_pre_family_count_for_cluster"] = len(c1_idx)
        ranked = ranked.sort_values(
            ["problem_similarity_to_filtered_s0_centroid", "family_first_date", "family_id_simple"],
            ascending=[False, True, True],
        ).reset_index(drop=True)
        ranked.insert(0, "cluster_rank", np.arange(1, len(ranked) + 1))
        frames.append(ranked)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def slim_s0_filtered(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "target_cluster",
        "cluster_first_date",
        "family_id",
        "family_id_simple",
        "family_first_date",
        "date_basis",
        "filing_date",
        "priority_date",
        "publication_date",
        "patent_count",
        "title",
        "problem_context",
        "solution_context",
        "technical_means",
        "text_for_embedding",
        "usage_filter_terms",
        "matched_usage_terms",
        "cpc_main",
        "cpc_others",
        "ipc_main",
        "ipc_others",
        "cluster_representative_family_id_simple",
        "cluster_representative_title",
    ]
    out = df[[col for col in cols if col in df.columns]].copy()
    if "text_for_embedding" in out.columns:
        out["text_for_embedding"] = compact_text(out["text_for_embedding"])
    return out


def slim_ranking(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "target_cluster",
        "cluster_rank",
        "problem_similarity_to_filtered_s0_centroid",
        "family_id",
        "family_id_simple",
        "family_first_date",
        "date_basis",
        "filing_date",
        "priority_date",
        "publication_date",
        "patent_count",
        "title",
        "problem_context",
        "solution_context",
        "technical_means",
        "semiconductor_direct_match_terms",
        "contains_substrate_term",
        "substrate_only_review_flag",
        "s0_pre_filtered_family_count_for_cluster",
        "c1_pre_family_count_for_cluster",
        "cluster_first_date",
        "cluster_representative_family_id_simple",
        "cluster_representative_title",
    ]
    return df[[col for col in cols if col in df.columns]].copy()


def build_summary_filtered(cluster_summary: pd.DataFrame, s0_raw: pd.DataFrame, s0_filtered: pd.DataFrame, c1_pre: pd.DataFrame) -> pd.DataFrame:
    out = cluster_summary.rename(columns={"usage_cluster": "target_cluster"}).copy()
    before = s0_raw.groupby("target_cluster")["family_id_simple"].nunique().rename("s0_pre_family_count_before_filter")
    after = s0_filtered.groupby("target_cluster")["family_id_simple"].nunique().rename("s0_pre_family_count_filtered")
    c1_count = c1_pre.groupby("target_cluster")["family_id_simple"].nunique().rename("c1_pre_family_count")
    out = out.merge(before, on="target_cluster", how="left")
    out = out.merge(after, on="target_cluster", how="left")
    out = out.merge(c1_count, on="target_cluster", how="left")
    for col in ["s0_pre_family_count_before_filter", "s0_pre_family_count_filtered", "c1_pre_family_count"]:
        out[col] = out[col].fillna(0).astype(int)
    out["s0_filter_retention_rate"] = (
        out["s0_pre_family_count_filtered"] / out["s0_pre_family_count_before_filter"].replace(0, np.nan)
    ).fillna(0).round(6)
    out["usage_filter_terms"] = out["target_cluster"].map(lambda c: "; ".join(CLUSTER_USAGE_TERMS.get(c, [])))
    return out


def build_manual_review(topk: pd.DataFrame, cluster_summary: pd.DataFrame) -> pd.DataFrame:
    reps = cluster_summary.rename(
        columns={
            "usage_cluster": "target_cluster",
            "representative_family_id_simple": "matched_s1_representative_family",
            "representative_title": "matched_s1_title",
        }
    )[["target_cluster", "matched_s1_representative_family", "matched_s1_title"]]

    manual = topk[topk["cluster_rank"].astype(int) <= MANUAL_REVIEW_TOP_N].copy()
    manual = manual.merge(reps, on="target_cluster", how="left")
    manual["review_problem_match"] = ""
    manual["review_solution_match"] = ""
    manual["review_overall_label"] = ""
    manual["review_note"] = ""
    manual = manual.rename(columns={"target_cluster": "cluster", "cluster_rank": "rank"})
    return manual[
        [
            "cluster",
            "rank",
            "family_id_simple",
            "family_first_date",
            "title",
            "problem_context",
            "solution_context",
            "technical_means",
            "matched_s1_representative_family",
            "matched_s1_title",
            "review_problem_match",
            "review_solution_match",
            "review_overall_label",
            "review_note",
        ]
    ]


def main() -> int:
    cluster_summary = pd.read_csv(CLUSTER_DIR / "S1_cluster_first_dates.csv", dtype=str, keep_default_na=False)
    s0_pre = pd.read_csv(CLUSTER_DIR / "S0_pre_for_each_cluster.csv", dtype=str, keep_default_na=False)
    c1_pre = pd.read_csv(CLUSTER_DIR / "C1_pre_for_each_cluster.csv", dtype=str, keep_default_na=False)
    enriched_ranking = pd.read_csv(CLUSTER_DIR / "C1_candidate_ranking_by_cluster.csv", dtype=str, keep_default_na=False)
    _ = pd.read_csv(DATA_DIR / "S1_family_level_clustered.csv", dtype=str, keep_default_na=False)

    c1_pre = ensure_c1_context(c1_pre, enriched_ranking)
    s0_filtered = filter_s0_by_usage_terms(s0_pre)
    summary_filtered = build_summary_filtered(cluster_summary, s0_pre, s0_filtered, c1_pre)
    ranking = rank_c1_by_filtered_s0(s0_filtered, c1_pre)
    topk = ranking[ranking["cluster_rank"] <= TOP_K].copy()
    manual_review = build_manual_review(topk, cluster_summary)

    slim_s0_filtered(s0_filtered).to_csv(CLUSTER_DIR / "S0_pre_for_each_cluster_filtered.csv", index=False, encoding="utf-8")
    summary_filtered.to_csv(CLUSTER_DIR / "heterogeneous_cluster_dataset_summary_filtered.csv", index=False, encoding="utf-8")
    slim_ranking(topk).to_csv(CLUSTER_DIR / "C1_problem_topk_by_cluster_filtered.csv", index=False, encoding="utf-8")
    slim_ranking(ranking).to_csv(CLUSTER_DIR / "C1_candidate_ranking_by_cluster_filtered.csv", index=False, encoding="utf-8")
    manual_review.to_csv(CLUSTER_DIR / "C1_candidate_manual_review_by_cluster.csv", index=False, encoding="utf-8")

    print(summary_filtered.to_string(index=False))
    print(f"saved filtered S0 rows={len(s0_filtered)}")
    print(f"saved filtered ranking rows={len(ranking)} topk_rows={len(topk)} manual_review_rows={len(manual_review)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
