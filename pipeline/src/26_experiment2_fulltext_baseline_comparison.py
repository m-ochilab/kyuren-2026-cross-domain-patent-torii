#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLUSTER_DIR = PROJECT_ROOT / "pipeline/outputs/heterogeneous_clusters"
MANUAL_DIR = PROJECT_ROOT / "pipeline/outputs/heterogeneous_manual_review"
BUNDLE_DIR = PROJECT_ROOT / "pipeline/data/bundles/experiment2_heterogeneous_bundle"

C1_PRE_PATH = CLUSTER_DIR / "C1_pre_for_each_cluster.csv"
S0_FILTERED_PATH = CLUSTER_DIR / "S0_pre_for_each_cluster_filtered.csv"
S1_CLUSTER_PATH = CLUSTER_DIR / "S1_cluster_first_dates.csv"
PROPOSED_RANKING_PATH = CLUSTER_DIR / "C1_candidate_manual_review_filled_draft.csv"
ENRICHED_C1_RANKING_PATH = CLUSTER_DIR / "C1_candidate_ranking_by_cluster_filtered.csv"
STRICT_REVIEW_PATH = Path("/Users/h-torii4649/Downloads/heterogeneous_manual_review_final_strict.csv")
LOCAL_REVIEW_PATH = MANUAL_DIR / "heterogeneous_manual_review_final.csv"

TOP_K = 20
MAX_TOKENS_PER_DOC = 5000

LABEL_ORDER = ["◎", "○", "△", "×", "未評価"]
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_\-]{1,}", re.IGNORECASE)
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]+")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def combine_text(row: pd.Series, columns: Iterable[str]) -> str:
    return clean_text(" ".join(clean_text(row.get(col, "")) for col in columns))


def tokenize(text: str) -> list[str]:
    text = clean_text(text).lower()
    tokens: list[str] = []
    tokens.extend(match.group(0) for match in TOKEN_RE.finditer(text))
    for match in CJK_RE.finditer(text):
        block = match.group(0)
        for n in (2, 3):
            if len(block) >= n:
                tokens.extend(block[i : i + n] for i in range(len(block) - n + 1))
    return tokens[:MAX_TOKENS_PER_DOC]


def hashed_idf_vectors(texts: list[str]) -> tuple[list[Counter[str]], dict[str, float]]:
    counters: list[Counter[str]] = []
    document_frequency: Counter[str] = Counter()
    for text in texts:
        counter = Counter(tokenize(text))
        counters.append(counter)
        document_frequency.update(counter.keys())

    n_docs = max(len(counters), 1)
    idf = {
        token: math.log((1 + n_docs) / (1 + df)) + 1.0
        for token, df in document_frequency.items()
    }
    return counters, idf


def vectorize_counter(counter: Counter[str], idf: dict[str, float]) -> dict[str, float]:
    weighted: dict[str, float] = {}
    norm_sq = 0.0
    for token, tf in counter.items():
        weight = (1.0 + math.log(tf)) * idf.get(token, 1.0)
        weighted[token] = weight
        norm_sq += weight * weight
    if norm_sq == 0:
        return {}
    norm = math.sqrt(norm_sq)
    return {token: weight / norm for token, weight in weighted.items()}


def aggregate_counters(counters: Iterable[Counter[str]]) -> Counter[str]:
    total: Counter[str] = Counter()
    for counter in counters:
        total.update(counter)
    return total


def cosine_sparse(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return float(sum(value * right.get(token, 0.0) for token, value in left.items()))


def hash_text_id(text: str) -> str:
    return hashlib.blake2b(text.encode("utf-8", errors="ignore"), digest_size=8).hexdigest()


def split_clusters(value: str) -> set[str]:
    return {
        part.strip()
        for part in re.split(r"[;,]", clean_text(value))
        if part.strip()
    }


def label_counts(series: pd.Series) -> dict[str, int]:
    counts = series.fillna("未評価").replace("", "未評価").value_counts().to_dict()
    return {label: int(counts.get(label, 0)) for label in LABEL_ORDER}


def first_existing(path_candidates: Iterable[Path]) -> Path:
    for path in path_candidates:
        if path.exists():
            return path
    raise FileNotFoundError("No candidate input file exists")


def build_fulltext_baseline() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    c1_pre = read_csv(C1_PRE_PATH)
    s0_filtered = read_csv(S0_FILTERED_PATH)
    s1_clusters = read_csv(S1_CLUSTER_PATH)
    proposed_draft = read_csv(PROPOSED_RANKING_PATH)
    enriched_c1 = read_csv(ENRICHED_C1_RANKING_PATH)
    review_path = first_existing([STRICT_REVIEW_PATH, LOCAL_REVIEW_PATH])
    proposed_review = read_csv(review_path)

    context_cols = ["problem_context", "solution_context", "technical_means"]
    enrich_cols = ["target_cluster", "family_id_simple"] + [
        col for col in context_cols if col in enriched_c1.columns
    ]
    c1_pre = c1_pre.merge(
        enriched_c1[enrich_cols].drop_duplicates(["target_cluster", "family_id_simple"]),
        on=["target_cluster", "family_id_simple"],
        how="left",
    )

    cluster_col = "target_cluster"
    c1_pre["fulltext"] = c1_pre.apply(lambda row: combine_text(row, ["title", "abstract", "claims"]), axis=1)
    c1_pre["fulltext_length"] = c1_pre["fulltext"].str.len().astype(int)

    s0_text_cols = [
        "title",
        "abstract",
        "claims",
        "text_for_embedding",
        "problem_context",
        "solution_context",
        "technical_means",
    ]
    s0_filtered["query_text"] = s0_filtered.apply(lambda row: combine_text(row, s0_text_cols), axis=1)

    c1_texts = c1_pre["fulltext"].fillna("").astype(str).tolist()
    s0_texts = s0_filtered["query_text"].fillna("").astype(str).tolist()
    counters, idf = hashed_idf_vectors(c1_texts + s0_texts)
    c1_counters = counters[: len(c1_pre)]
    s0_counters = counters[len(c1_pre) :]
    c1_vectors = [vectorize_counter(counter, idf) for counter in c1_counters]

    s0_counter_by_cluster: dict[str, Counter[str]] = {}
    s0_tmp = s0_filtered.reset_index(drop=True)
    for cluster, idxs in s0_tmp.groupby("target_cluster").groups.items():
        s0_counter_by_cluster[cluster] = aggregate_counters(s0_counters[i] for i in idxs)

    cluster_meta = (
        s1_clusters.rename(
            columns={
                "usage_cluster": "target_cluster",
                "cluster_first_date": "s1_cluster_first_date",
                "representative_family_id_simple": "matched_s1_representative_family",
                "representative_title": "matched_s1_title",
            }
        )
        .set_index("target_cluster")
        .to_dict(orient="index")
    )

    rows: list[pd.DataFrame] = []
    c1_reset = c1_pre.reset_index(drop=True)
    for cluster in sorted(cluster_meta.keys()):
        subset_idx = c1_reset.index[c1_reset[cluster_col] == cluster].to_list()
        query_counter = s0_counter_by_cluster.get(cluster, Counter())
        query_vector = vectorize_counter(query_counter, idf)
        ranked_records = []
        for idx in subset_idx:
            record = c1_reset.loc[idx].to_dict()
            record["fulltext_similarity"] = cosine_sparse(query_vector, c1_vectors[idx])
            record["fulltext_hash"] = hash_text_id(record.get("fulltext", ""))
            record["s0_filtered_family_count_for_cluster"] = int(
                (s0_tmp["target_cluster"] == cluster).sum()
            )
            ranked_records.append(record)
        ranked = pd.DataFrame(ranked_records)
        if ranked.empty:
            continue
        ranked = ranked.sort_values(
            ["fulltext_similarity", "family_first_date", "family_id_simple", "title"],
            ascending=[False, True, True, True],
        ).reset_index(drop=True)
        ranked.insert(0, "fulltext_rank", np.arange(1, len(ranked) + 1))
        rows.append(ranked.head(TOP_K))

    top20 = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    for cluster, meta in cluster_meta.items():
        mask = top20["target_cluster"] == cluster
        for key, value in meta.items():
            if key not in top20.columns:
                top20[key] = ""
            top20.loc[mask, key] = value

    top20_cols = [
        "target_cluster",
        "fulltext_rank",
        "fulltext_similarity",
        "family_id",
        "family_id_simple",
        "family_first_date",
        "date_basis",
        "filing_date",
        "priority_date",
        "publication_date",
        "patent_count",
        "title",
        "abstract",
        "claims",
        "problem_context",
        "solution_context",
        "technical_means",
        "fulltext_length",
        "fulltext_hash",
        "s0_filtered_family_count_for_cluster",
        "cluster_first_date",
        "matched_s1_representative_family",
        "matched_s1_title",
    ]
    top20 = top20[[col for col in top20_cols if col in top20.columns]].copy()

    unique_family = make_unique_family(top20)
    overlap = make_overlap_tables(proposed_review, unique_family, top20)
    fulltext_only = make_fulltext_only_for_review(proposed_review, unique_family)
    report = make_report(
        c1_pre=c1_pre,
        s0_filtered=s0_filtered,
        proposed_review=proposed_review,
        top20=top20,
        unique_family=unique_family,
        overlap=overlap,
        fulltext_only=fulltext_only,
        review_path=review_path,
        proposed_draft=proposed_draft,
    )
    return top20, unique_family, overlap, fulltext_only, report


def make_unique_family(top20: pd.DataFrame) -> pd.DataFrame:
    if top20.empty:
        return pd.DataFrame()

    records = []
    for family_id, group in top20.groupby("family_id_simple", dropna=False):
        best = group.sort_values(
            ["fulltext_similarity", "fulltext_rank", "target_cluster"],
            ascending=[False, True, True],
        ).iloc[0]
        appeared = sorted(group["target_cluster"].dropna().astype(str).unique())
        cluster_ranks = "; ".join(
            f"{row.target_cluster}:{int(row.fulltext_rank)}"
            for row in group.sort_values(["target_cluster", "fulltext_rank"]).itertuples()
        )
        record = best.to_dict()
        record["primary_cluster"] = best.get("target_cluster", "")
        record["appeared_clusters"] = "; ".join(appeared)
        record["cluster_ranks"] = cluster_ranks
        record["best_fulltext_rank"] = int(best.get("fulltext_rank", 0))
        record["best_fulltext_similarity"] = float(best.get("fulltext_similarity", 0.0))
        records.append(record)

    out = pd.DataFrame(records)
    return out.sort_values(
        ["best_fulltext_rank", "best_fulltext_similarity", "family_id_simple"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def make_overlap_tables(
    proposed_review: pd.DataFrame,
    unique_family: pd.DataFrame,
    top20: pd.DataFrame,
) -> pd.DataFrame:
    proposed = proposed_review.copy()
    proposed["family_id_simple"] = proposed["family_id_simple"].astype(str)
    unique_family = unique_family.copy()
    unique_family["family_id_simple"] = unique_family["family_id_simple"].astype(str)

    proposed_families = set(proposed["family_id_simple"])
    fulltext_families = set(unique_family["family_id_simple"])
    overlap_families = proposed_families & fulltext_families
    proposed_only = proposed_families - fulltext_families
    fulltext_only = fulltext_families - proposed_families

    rows = [
        {"level": "overall", "cluster": "ALL", "metric": "proposed_count", "value": len(proposed_families)},
        {"level": "overall", "cluster": "ALL", "metric": "fulltext_baseline_count", "value": len(fulltext_families)},
        {"level": "overall", "cluster": "ALL", "metric": "overlap_family_count", "value": len(overlap_families)},
        {"level": "overall", "cluster": "ALL", "metric": "proposed_only_count", "value": len(proposed_only)},
        {"level": "overall", "cluster": "ALL", "metric": "fulltext_only_count", "value": len(fulltext_only)},
    ]

    clusters = sorted(set(top20["target_cluster"].astype(str)) | set(proposed["cluster"].astype(str)))
    for cluster in clusters:
        proposed_cluster = set()
        for row in proposed.itertuples():
            appeared = split_clusters(getattr(row, "appeared_clusters", "")) or {getattr(row, "cluster", "")}
            if cluster in appeared:
                proposed_cluster.add(str(row.family_id_simple))
        fulltext_cluster = set(top20.loc[top20["target_cluster"] == cluster, "family_id_simple"].astype(str))
        rows.extend(
            [
                {"level": "cluster", "cluster": cluster, "metric": "proposed_count", "value": len(proposed_cluster)},
                {
                    "level": "cluster",
                    "cluster": cluster,
                    "metric": "fulltext_baseline_count",
                    "value": len(fulltext_cluster),
                },
                {
                    "level": "cluster",
                    "cluster": cluster,
                    "metric": "overlap_family_count",
                    "value": len(proposed_cluster & fulltext_cluster),
                },
                {
                    "level": "cluster",
                    "cluster": cluster,
                    "metric": "proposed_only_count",
                    "value": len(proposed_cluster - fulltext_cluster),
                },
                {
                    "level": "cluster",
                    "cluster": cluster,
                    "metric": "fulltext_only_count",
                    "value": len(fulltext_cluster - proposed_cluster),
                },
            ]
        )

    proposed_labels = proposed["human_label"].replace("", "未評価") if "human_label" in proposed.columns else pd.Series()
    for label, count in label_counts(proposed_labels).items():
        rows.append({"level": "label_distribution", "cluster": "proposed_all", "metric": label, "value": count})
    overlap_labels = proposed.loc[proposed["family_id_simple"].isin(overlap_families), "human_label"]
    for label, count in label_counts(overlap_labels).items():
        rows.append({"level": "label_distribution", "cluster": "overlap_reused_human_label", "metric": label, "value": count})
    rows.append(
        {
            "level": "label_distribution",
            "cluster": "fulltext_only",
            "metric": "未評価",
            "value": len(fulltext_only),
        }
    )
    return pd.DataFrame(rows)


def make_fulltext_only_for_review(proposed_review: pd.DataFrame, unique_family: pd.DataFrame) -> pd.DataFrame:
    proposed_families = set(proposed_review["family_id_simple"].astype(str))
    fulltext_only = unique_family.loc[
        ~unique_family["family_id_simple"].astype(str).isin(proposed_families)
    ].copy()
    if fulltext_only.empty:
        return fulltext_only
    fulltext_only = fulltext_only.sort_values(
        ["primary_cluster", "best_fulltext_rank", "best_fulltext_similarity"],
        ascending=[True, True, False],
    ).reset_index(drop=True)
    fulltext_only.insert(0, "review_id", [f"FTONLY{i:04d}" for i in range(1, len(fulltext_only) + 1)])
    fulltext_only["evaluation_status"] = "unreviewed_fulltext_only"
    review_cols = [
        "review_id",
        "primary_cluster",
        "appeared_clusters",
        "cluster_ranks",
        "best_fulltext_rank",
        "best_fulltext_similarity",
        "family_id",
        "family_id_simple",
        "family_first_date",
        "title",
        "abstract",
        "claims",
        "problem_context",
        "solution_context",
        "technical_means",
        "matched_s1_representative_family",
        "matched_s1_title",
        "evaluation_status",
    ]
    return fulltext_only[[col for col in review_cols if col in fulltext_only.columns]].copy()


def metric_value(overlap: pd.DataFrame, metric: str, cluster: str = "ALL") -> int:
    mask = (overlap["metric"] == metric) & (overlap["cluster"] == cluster)
    if not mask.any():
        return 0
    return int(overlap.loc[mask, "value"].iloc[0])


def markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_No rows._"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines = [header, sep]
    for _, row in df.iterrows():
        values = [clean_text(row.get(col, "")) for col in columns]
        values = [value.replace("|", "/") for value in values]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def make_report(
    c1_pre: pd.DataFrame,
    s0_filtered: pd.DataFrame,
    proposed_review: pd.DataFrame,
    top20: pd.DataFrame,
    unique_family: pd.DataFrame,
    overlap: pd.DataFrame,
    fulltext_only: pd.DataFrame,
    review_path: Path,
    proposed_draft: pd.DataFrame,
) -> str:
    cluster_rows = overlap[overlap["level"] == "cluster"].pivot(
        index="cluster", columns="metric", values="value"
    ).reset_index()
    for col in [
        "proposed_count",
        "fulltext_baseline_count",
        "overlap_family_count",
        "proposed_only_count",
        "fulltext_only_count",
    ]:
        if col not in cluster_rows.columns:
            cluster_rows[col] = 0
        cluster_rows[col] = cluster_rows[col].astype(int)

    proposed_labels = pd.DataFrame(
        [{"label": label, "count": count} for label, count in label_counts(proposed_review.get("human_label", pd.Series())).items()]
    )
    overlap_family_set = set(unique_family["family_id_simple"].astype(str)) & set(
        proposed_review["family_id_simple"].astype(str)
    )
    overlap_labels = pd.DataFrame(
        [
            {"label": label, "count": count}
            for label, count in label_counts(
                proposed_review.loc[
                    proposed_review["family_id_simple"].astype(str).isin(overlap_family_set),
                    "human_label",
                ]
            ).items()
        ]
    )

    examples = (
        fulltext_only.sort_values(["primary_cluster", "best_fulltext_rank"])
        .groupby("primary_cluster", as_index=False)
        .head(3)
        if not fulltext_only.empty
        else pd.DataFrame()
    )
    if not examples.empty:
        examples = examples.assign(
            best_fulltext_similarity=lambda d: d["best_fulltext_similarity"].map(lambda x: f"{float(x):.4f}")
        )

    return f"""# Experiment 2 Fulltext Baseline Comparison

## 目的

実験2「異質解決策型」について、課題文脈に基づく提案ランキングと、Title + Abstract + Claims の全文テキストに基づく baseline ranking の候補重複・差分・クラスタ傾向を比較した補助分析である。

## 入力

- C1 candidate population: `{C1_PRE_PATH.relative_to(PROJECT_ROOT)}` ({len(c1_pre)} rows)
- S0 filtered query set: `{S0_FILTERED_PATH.relative_to(PROJECT_ROOT)}` ({len(s0_filtered)} rows)
- S1 cluster metadata: `{S1_CLUSTER_PATH.relative_to(PROJECT_ROOT)}`
- Proposed draft ranking: `{PROPOSED_RANKING_PATH.relative_to(PROJECT_ROOT)}` ({len(proposed_draft)} rows)
- Enriched C1 context ranking: `{ENRICHED_C1_RANKING_PATH.relative_to(PROJECT_ROOT)}` ({len(pd.read_csv(ENRICHED_C1_RANKING_PATH, usecols=["family_id_simple"]))} rows)
- Human reviewed proposed families: `{review_path}` ({len(proposed_review)} rows)

## baseline の作り方

- C1候補ごとに `fulltext = title + abstract + claims` を作成した。
- 同じ7クラスタ、同じpre条件、同じC1候補母集団を使った。
- クラスタごとのqueryは `S0_pre_for_each_cluster_filtered.csv` の `text_for_embedding/problem_context/solution_context/technical_means` を結合して作成した。
- 現在のローカル環境では `sentence-transformers` / `sklearn` が利用できないため、BERTそのものではなく、再現可能な軽量ハッシュTF-IDF全文ベクトルを用いた。したがって本結果は「全文BERT baseline の軽量代替」として扱う。
- 各clusterでTop{TOP_K}を抽出し、family単位で重複統合した。

## 全体集計

| metric | value |
| --- | ---: |
| proposed_count | {metric_value(overlap, "proposed_count")} |
| fulltext_baseline_count | {metric_value(overlap, "fulltext_baseline_count")} |
| overlap_family_count | {metric_value(overlap, "overlap_family_count")} |
| proposed_only_count | {metric_value(overlap, "proposed_only_count")} |
| fulltext_only_count | {metric_value(overlap, "fulltext_only_count")} |

## cluster別 overlap

{markdown_table(cluster_rows, ["cluster", "proposed_count", "fulltext_baseline_count", "overlap_family_count", "proposed_only_count", "fulltext_only_count"])}

## human_label 分布

### 提案手法側 46 family

{markdown_table(proposed_labels, ["label", "count"])}

### baseline と重複した評価済み family

{markdown_table(overlap_labels, ["label", "count"])}

### fulltext_only

fulltext_only候補は既存評価に含まれないため、全件を未評価として分けた。

## fulltext_only 代表例

{markdown_table(examples, ["primary_cluster", "best_fulltext_rank", "best_fulltext_similarity", "family_id_simple", "title"], max_rows=21)}

## 注意

- この比較は実験2の主結果ではなく、候補ランキングの性質差を見るための補助分析である。
- 評価済みの `human_label` は提案手法で作成した46 familyに対してのみ再利用した。
- fulltext_only候補は未評価であり、妥当性を示すものではない。
- 本分析は技術導入可能性を証明するものではなく、専門家確認候補としての解釈可能性やランキング傾向の比較に限定される。
"""


def save_outputs() -> None:
    top20, unique_family, overlap, fulltext_only, report = build_fulltext_baseline()

    outputs = {
        "fulltext_baseline_top20_by_cluster.csv": top20,
        "fulltext_baseline_unique_family.csv": unique_family,
        "proposed_vs_fulltext_overlap.csv": overlap,
        "fulltext_only_candidates_for_review.csv": fulltext_only,
    }
    CLUSTER_DIR.mkdir(parents=True, exist_ok=True)
    for filename, df in outputs.items():
        df.to_csv(CLUSTER_DIR / filename, index=False, encoding="utf-8-sig")
    (CLUSTER_DIR / "experiment2_fulltext_baseline_report.md").write_text(report, encoding="utf-8")

    bundle_out = BUNDLE_DIR / "outputs"
    bundle_out.mkdir(parents=True, exist_ok=True)
    for filename, df in outputs.items():
        df.to_csv(bundle_out / filename, index=False, encoding="utf-8-sig")
    (bundle_out / "experiment2_fulltext_baseline_report.md").write_text(report, encoding="utf-8")

    print("created:")
    for filename in [*outputs.keys(), "experiment2_fulltext_baseline_report.md"]:
        print(f"- {CLUSTER_DIR / filename}")
    print(f"bundle copies: {bundle_out}")


if __name__ == "__main__":
    save_outputs()
