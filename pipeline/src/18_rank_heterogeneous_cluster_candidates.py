#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "pipeline/data/processed_heterogeneous"
CLUSTER_DIR = PROJECT_ROOT / "pipeline/outputs/heterogeneous_clusters"

CONTEXT_COLUMNS = ["problem_context", "solution_context", "technical_means"]
TEXT_PART_COLUMNS = ["title", "abstract", "claims"]
TOP_K_DEFAULT = 50
MAX_ABSTRACT_CHARS = 2500
MAX_CLAIMS_CHARS = 3500
MAX_CONTEXT_CHARS = 1200
MAX_EXPORT_TEXT_CHARS = 1000

PROBLEM_RE = re.compile(
    r"problem|issue|challenge|drawback|difficulty|need|required|prevent|suppress|"
    r"residue|remaining|corrosion|damage|contamination|particle|defect|removability|"
    r"課題|問題|困難|必要|抑制|防止|低減|残留|残渣|腐食|汚染|異物|除去性|"
    r"问题|困难|抑制|防止|降低|残留|腐蚀|污染|颗粒|粒子|去除性",
    re.IGNORECASE,
)
SOLUTION_RE = re.compile(
    r"composition|method|process|comprises|includes|containing|using|treating|cleaning|"
    r"polishing|rinsing|removing|agent|surfactant|polymer|solvent|alkali|acid|amine|"
    r"組成物|方法|工程|含有|用いて|洗浄|研磨|リンス|剥離|除去|剤|界面活性剤|"
    r"聚合物|溶剤|アルカリ|酸|胺|组合物|方法|包含|清洗|去除",
    re.IGNORECASE,
)
TECHNICAL_RULES = [
    ("洗浄剤組成物", r"cleaning composition|detergent composition|cleaning agent|洗浄剤|清洗剂|清潔劑|組成物|组合物"),
    ("基板洗浄方法", r"substrate cleaning|cleaning method|洗浄方法|清洗方法|基板.*洗浄|基板.*清洗"),
    ("シリコンウェーハ洗浄・リンス", r"silicon wafer|wafer.*rinse|rinsing agent|ウェーハ|ウエハ|晶片|晶圓|晶圆|リンス"),
    ("CMP後洗浄", r"CMP|chemical mechanical polishing|polishing.*substrate|研磨.*洗浄|化学機械研磨|化學機械研磨|酸化セリウム|ceria"),
    ("樹脂マスク・レジスト除去", r"resin mask|photoresist|resist|樹脂マスク|レジスト|树脂掩膜|剥離"),
    ("接着剤除去", r"adhesive|接着剤|adhésif|粘着"),
    ("フラックス残渣除去", r"flux|フラックス|助焊|solder"),
    ("電子部品・回路基板洗浄", r"circuit board|printed wiring|electronic part|回路基板|電子部品|プリント配線"),
    ("腐食抑制", r"corrosion|腐食|腐蚀|変色|discoloration"),
    ("粒子・残渣除去", r"particle|residue|残渣|残留|粒子|颗粒"),
]


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value)
    if text.lower() == "nan":
        return ""
    return re.sub(r"\s+", " ", text).strip()


def coalesce_date(priority: pd.Series, filing: pd.Series) -> pd.Series:
    p = priority.fillna("").astype(str).str.strip()
    f = filing.fillna("").astype(str).str.strip()
    return p.where(p.ne(""), f)


def make_text_for_embedding(df: pd.DataFrame) -> pd.Series:
    parts = []
    for col in TEXT_PART_COLUMNS:
        if col in df.columns:
            parts.append(df[col].fillna("").astype(str))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return (parts[0] + " " + parts[1] + " " + parts[2]).str.replace(r"\s+", " ", regex=True).str.strip()


def compact_text_series(series: pd.Series, limit: int = MAX_EXPORT_TEXT_CHARS) -> pd.Series:
    return series.fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip().str.slice(0, limit)


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    text = text[:MAX_CLAIMS_CHARS]
    pieces = re.split(r"(?<=[.!?。！？])\s+|(?<=。)|(?<=！)|(?<=？)|\n+", text)
    return [p.strip(" |")[:MAX_CONTEXT_CHARS] for p in pieces if len(p.strip()) >= 8]


def first_matching(sentences: Iterable[str], pattern: re.Pattern, limit: int) -> list[str]:
    out: list[str] = []
    for sentence in sentences:
        if pattern.search(sentence) and sentence not in out:
            out.append(sentence)
        if len(out) >= limit:
            break
    return out


def detect_technical_means(text: str) -> str:
    hits = []
    for label, pattern in TECHNICAL_RULES:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(label)
    return "; ".join(hits[:5])


def add_context_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    out = df.copy()
    out["text_for_embedding"] = make_text_for_embedding(out)
    if all(col in out.columns and out[col].fillna("").astype(str).str.strip().ne("").any() for col in CONTEXT_COLUMNS):
        return out, False

    problems = []
    solutions = []
    means = []
    for row in out.to_dict("records"):
        title = clean_text(row.get("title", ""))
        abstract = clean_text(row.get("abstract", ""))[:MAX_ABSTRACT_CHARS]
        claims = clean_text(row.get("claims", ""))[:MAX_CLAIMS_CHARS]
        full = clean_text(row.get("text_for_embedding", ""))
        sentences = split_sentences(abstract) + split_sentences(claims)

        problem = " ".join(first_matching(sentences, PROBLEM_RE, 2))
        if not problem:
            problem = clean_text(abstract)[:MAX_CONTEXT_CHARS] or title

        solution = " ".join(first_matching(sentences, SOLUTION_RE, 2))
        if not solution:
            solution = clean_text(claims)[:MAX_CONTEXT_CHARS] or abstract[:MAX_CONTEXT_CHARS] or title

        technical_means = detect_technical_means(full)
        if not technical_means:
            technical_means = detect_technical_means(solution)

        problems.append(problem)
        solutions.append(solution)
        means.append(technical_means)

    out["problem_context"] = problems
    out["solution_context"] = solutions
    out["technical_means"] = means
    return out, True


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

    out = family_df.copy()
    out["date_basis"] = coalesce_date(out["priority_date"], out["filing_date"])
    if "family_first_date" in out.columns:
        out = out.drop(columns=["family_first_date"])
    out = out.merge(first, on="family_id_simple", how="left")
    out["family_first_date"] = out["family_first_date"].where(
        out["family_first_date"].fillna("").astype(str).str.strip().ne(""),
        out["date_basis"],
    )
    return out


def build_s0_pre_for_each_cluster(s0_family: pd.DataFrame, cluster_summary: pd.DataFrame) -> pd.DataFrame:
    s0 = s0_family.copy()
    s0["_family_first_date_dt"] = pd.to_datetime(s0["family_first_date"], errors="coerce")
    rows = []
    for cluster in cluster_summary.to_dict("records"):
        cluster_first = pd.to_datetime(cluster["cluster_first_date"], errors="coerce")
        subset = s0[s0["_family_first_date_dt"] < cluster_first].copy()
        subset["target_cluster"] = cluster["usage_cluster"]
        subset["cluster_first_date"] = cluster["cluster_first_date"]
        subset["cluster_representative_family_id_simple"] = cluster["representative_family_id_simple"]
        subset["cluster_representative_title"] = cluster["representative_title"]
        rows.append(subset)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if "_family_first_date_dt" in out.columns:
        out = out.drop(columns=["_family_first_date_dt"])
    return out


def fit_problem_vectors(s0_pre: pd.DataFrame, c1_pre: pd.DataFrame):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.preprocessing import normalize
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for local TF-IDF vector ranking") from exc

    s0_text = s0_pre["problem_context"].fillna("").astype(str)
    c1_text = c1_pre["problem_context"].fillna("").astype(str)
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
    s0_vec = matrix[: len(s0_pre)]
    c1_vec = matrix[len(s0_pre):]
    s0_vec = normalize(s0_vec, norm="l2", copy=False)
    c1_vec = normalize(c1_vec, norm="l2", copy=False)
    return s0_vec, c1_vec


def rank_candidates_by_cluster(s0_pre: pd.DataFrame, c1_pre: pd.DataFrame, top_k: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    s0_vec, c1_vec = fit_problem_vectors(s0_pre, c1_pre)
    ranking_frames = []

    c1_pre = c1_pre.reset_index(drop=True).copy()
    s0_pre = s0_pre.reset_index(drop=True).copy()
    c1_pre["_vector_idx"] = np.arange(len(c1_pre))
    s0_pre["_vector_idx"] = np.arange(len(s0_pre))

    for cluster in s0_pre["target_cluster"].dropna().unique():
        s0_idx = s0_pre.index[s0_pre["target_cluster"] == cluster].to_numpy()
        c1_idx = c1_pre.index[c1_pre["target_cluster"] == cluster].to_numpy()
        if len(s0_idx) == 0 or len(c1_idx) == 0:
            continue

        query = np.asarray(s0_vec[s0_idx].mean(axis=0))
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            sims = np.zeros(len(c1_idx), dtype=float)
        else:
            query = query / query_norm
            sims = np.asarray(c1_vec[c1_idx] @ query.T).ravel()

        ranked = c1_pre.iloc[c1_idx].copy()
        ranked["problem_similarity_to_s0_pre_centroid"] = sims
        ranked["s0_pre_family_count_for_cluster"] = len(s0_idx)
        ranked["c1_pre_family_count_for_cluster"] = len(c1_idx)
        ranked = ranked.sort_values(
            ["problem_similarity_to_s0_pre_centroid", "family_first_date", "family_id_simple"],
            ascending=[False, True, True],
        ).reset_index(drop=True)
        ranked.insert(0, "cluster_rank", np.arange(1, len(ranked) + 1))
        ranking_frames.append(ranked)

    ranking = pd.concat(ranking_frames, ignore_index=True) if ranking_frames else pd.DataFrame()
    topk = ranking[ranking["cluster_rank"] <= top_k].copy() if not ranking.empty else ranking.copy()
    return ranking, topk


def build_dataset_summary(cluster_summary: pd.DataFrame, s0_pre: pd.DataFrame, c1_pre: pd.DataFrame, c1_overall: pd.DataFrame) -> pd.DataFrame:
    s0_counts = s0_pre.groupby("target_cluster")["family_id_simple"].nunique().rename("s0_pre_family_count")
    c1_counts = c1_pre.groupby("target_cluster")["family_id_simple"].nunique().rename("c1_pre_family_count")
    out = cluster_summary.rename(columns={"usage_cluster": "target_cluster"}).copy()
    out = out.merge(s0_counts, on="target_cluster", how="left")
    out = out.merge(c1_counts, on="target_cluster", how="left")
    out["s0_pre_family_count"] = out["s0_pre_family_count"].fillna(0).astype(int)
    out["c1_pre_family_count"] = out["c1_pre_family_count"].fillna(0).astype(int)
    out["c1_pre_nonsemi_overall_family_count"] = c1_overall["family_id_simple"].nunique()
    return out


def save_context_extraction_input(df: pd.DataFrame, path: Path) -> None:
    cols = [
        col for col in [
            "family_id_simple",
            "family_first_date",
            "title",
            "text_for_embedding",
        ] if col in df.columns
    ]
    out = df[cols].drop_duplicates(subset=["family_id_simple"]).copy()
    for col in ["text_for_embedding"]:
        if col in out.columns:
            out[col] = compact_text_series(out[col])
    out.to_csv(path, index=False, encoding="utf-8")


def slim_s0_pre(df: pd.DataFrame) -> pd.DataFrame:
    preferred = [
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
        "cpc_main",
        "cpc_others",
        "ipc_main",
        "ipc_others",
        "cluster_representative_family_id_simple",
        "cluster_representative_title",
    ]
    cols = [col for col in preferred if col in df.columns]
    out = df[cols].copy()
    if "text_for_embedding" in out.columns:
        out["text_for_embedding"] = compact_text_series(out["text_for_embedding"])
    return out


def slim_ranking(df: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "target_cluster",
        "cluster_rank",
        "problem_similarity_to_s0_pre_centroid",
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
        "s0_pre_family_count_for_cluster",
        "c1_pre_family_count_for_cluster",
        "cluster_first_date",
        "cluster_representative_family_id_simple",
        "cluster_representative_title",
    ]
    cols = [col for col in preferred if col in df.columns]
    return df[cols].copy()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build heterogeneous solution candidate rankings by S1 usage cluster.")
    parser.add_argument("--top-k", type=int, default=TOP_K_DEFAULT)
    args = parser.parse_args()

    CLUSTER_DIR.mkdir(parents=True, exist_ok=True)

    cluster_summary = pd.read_csv(CLUSTER_DIR / "S1_cluster_first_dates.csv", dtype=str, keep_default_na=False)
    s0_family = pd.read_csv(DATA_DIR / "S0_family_level.csv", dtype=str, keep_default_na=False)
    s0_publication = pd.read_csv(DATA_DIR / "S0_publication_level.csv", dtype=str, keep_default_na=False)
    c1_pre = pd.read_csv(CLUSTER_DIR / "C1_pre_for_each_cluster.csv", dtype=str, keep_default_na=False)
    c1_overall = pd.read_csv(CLUSTER_DIR / "C1_pre_nonsemi_overall.csv", dtype=str, keep_default_na=False)

    s0_family = add_family_first_date(s0_family, s0_publication)
    s0_family, s0_context_created = add_context_columns(s0_family)
    s0_pre = build_s0_pre_for_each_cluster(s0_family, cluster_summary)

    c1_pre, c1_context_created = add_context_columns(c1_pre)
    c1_overall, _ = add_context_columns(c1_overall)

    if s0_context_created:
        save_context_extraction_input(s0_pre, CLUSTER_DIR / "S0_context_extraction_input.csv")
    if c1_context_created:
        save_context_extraction_input(c1_pre, CLUSTER_DIR / "C1_context_extraction_input.csv")

    dataset_summary = build_dataset_summary(cluster_summary, s0_pre, c1_pre, c1_overall)
    ranking, topk = rank_candidates_by_cluster(s0_pre, c1_pre, args.top_k)

    slim_s0_pre(s0_pre).to_csv(CLUSTER_DIR / "S0_pre_for_each_cluster.csv", index=False, encoding="utf-8")
    dataset_summary.to_csv(CLUSTER_DIR / "heterogeneous_cluster_dataset_summary.csv", index=False, encoding="utf-8")
    slim_ranking(topk).to_csv(CLUSTER_DIR / "C1_problem_topk_by_cluster.csv", index=False, encoding="utf-8")
    slim_ranking(ranking).to_csv(CLUSTER_DIR / "C1_candidate_ranking_by_cluster.csv", index=False, encoding="utf-8")

    print(dataset_summary.to_string(index=False))
    print(f"saved S0_pre rows={len(s0_pre)}")
    print(f"saved C1 ranking rows={len(ranking)} topk_rows={len(topk)} top_k={args.top_k}")
    if s0_context_created or c1_context_created:
        print("context extraction input CSVs were created because context columns were absent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
