from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


BASE = Path(__file__).resolve().parents[2]
RANKING_DIR = BASE / "pipeline/data/processed_full/ranking"
SIM_DIR = BASE / "pipeline/data/processed_full/similarity"
CONTEXT_DIR = BASE / "pipeline/data/processed_full"
OUT_DIR = BASE / "pipeline/outputs/manual_review_evaluation"

FILES = {
    "specific_methods": RANKING_DIR / "method_gap_ranking_specific_methods_full.csv",
    "with_future": RANKING_DIR / "method_gap_ranking_with_future_full.csv",
    "all_methods": RANKING_DIR / "method_gap_ranking_all_full.csv",
    "future_growth": RANKING_DIR / "method_future_growth_evaluation_full.csv",
    "unet_check": RANKING_DIR / "unet_ranking_check_full.csv",
    "problem_topk": SIM_DIR / "A0_to_B0_problem_topk_full.csv",
    "solution_topk": SIM_DIR / "A0_to_B0_solution_topk_full.csv",
    "fulltext_topk": SIM_DIR / "A0_to_B0_fulltext_topk_full.csv",
    "field_summary": SIM_DIR / "field_level_similarity_summary_full.csv",
    "b_contexts": CONTEXT_DIR / "B0_contexts.csv",
}

BLIND_COLUMNS = [
    "review_id",
    "publication_number",
    "family_id",
    "title",
    "abstract",
    "claims",
    "problem_context",
    "solution_context",
    "technical_means",
    "target_object",
    "effect_context",
    "application_field",
    "method_name",
    "candidate_type",
    "general_term_flag",
    "specific_method_flag",
    "problem_extraction_score",
    "solution_extraction_score",
    "technical_means_score",
    "target_object_score",
    "problem_similarity_score",
    "solution_relevance_score",
    "candidate_score",
    "representative_flag",
    "final_label",
    "reviewer_comment",
]

REVIEW_BLANK_COLUMNS = [
    "problem_extraction_score",
    "solution_extraction_score",
    "technical_means_score",
    "target_object_score",
    "problem_similarity_score",
    "solution_relevance_score",
    "candidate_score",
    "representative_flag",
    "final_label",
    "reviewer_comment",
]

FORBIDDEN_BLIND_COLUMNS = {
    "rank",
    "score",
    "gap_score",
    "similarity_score",
    "method_source",
    "proposed_or_baseline",
    "future_count",
    "future_rate",
}

SPECIFIC_PATTERNS = [
    r"\bu-?net\b",
    r"\bunet\b",
    r"\bu net\b",
    r"\byolo\b",
    r"\bgan\b",
    r"\bcyclegan\b",
    r"\btransformer\b",
    r"\bresnet\b",
    r"\bautoencoder\b",
    r"\bdomain adaptation\b",
    r"\bcnn\b",
    r"\bsvm\b",
    r"\bpca\b",
    r"\bk-means\b",
    r"\brandom forest\b",
    r"\bvgg\b",
    r"\bvit\b",
    r"encoder-decoder",
    r"principal component analysis",
]

GENERAL_PATTERNS = [
    "画像セグメンテーション",
    "深層学習モデル",
    "画像処理",
    "画像処理システム",
    "画像処理方法",
    "機械学習モデル",
    "画像生成・再構成",
    "信号処理",
    "検出方法",
    "分類",
    "特徴抽出",
    "segmentation",
    "deep learning",
    "image processing",
    "machine learning",
]

METHOD_FLAG_COLUMNS = {
    "u-net": "is_unet_final",
    "unet": "is_unet_final",
    "u net": "is_unet_final",
    "yolo": "is_yolo",
    "gan": "is_gan",
    "cyclegan": "is_cyclegan",
    "transformer": "is_transformer",
    "attention": "is_attention",
    "autoencoder": "is_autoencoder",
    "cnn": "is_cnn",
    "domain adaptation": "is_domain_adaptation",
    "resnet": "is_resnet",
    "vgg": "is_vgg",
}


@dataclass
class Candidate:
    publication_number: str
    candidate_type: str
    method_name: str
    source_file: str
    source_row_index: int | None = None
    method_source: str = ""
    proposed_or_baseline: str = "proposed"
    rank: Any = ""
    score: Any = ""
    gap_score: Any = ""
    similarity_score: Any = ""
    future_count: Any = ""
    future_rate: Any = ""
    row_data: dict[str, Any] = field(default_factory=dict)
    pair_data: dict[str, Any] = field(default_factory=dict)


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, **kwargs)


def clean_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def norm(value: Any) -> str:
    return clean_text(value).lower().replace("_", " ").replace("－", "-")


def first_existing(row: pd.Series | dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in row and clean_text(row[name]) != "":
            return row[name]
    return ""


def is_specific_method(text: Any) -> int:
    hay = norm(text)
    return int(any(re.search(pattern, hay, flags=re.IGNORECASE) for pattern in SPECIFIC_PATTERNS))


def is_general_term(text: Any) -> int:
    hay = norm(text)
    return int(any(term.lower() in hay for term in GENERAL_PATTERNS))


def method_to_display(row: pd.Series | dict[str, Any]) -> str:
    return clean_text(first_existing(row, ["method_display", "method", "technical_means", "b_technical_means"]))


def method_matches_text(method: str, text: Any) -> bool:
    method_n = norm(method)
    text_n = norm(text)
    if not method_n or not text_n:
        return False
    aliases = {method_n}
    if method_n == "u-net":
        aliases |= {"unet", "u net"}
    if method_n == "principal component analysis":
        aliases.add("pca")
    if method_n == "pca":
        aliases.add("principal component analysis")
    return any(alias in text_n for alias in aliases)


def context_method_mask(df: pd.DataFrame, method: str) -> pd.Series:
    method_n = norm(method)
    mask = pd.Series(False, index=df.index)
    flag_col = METHOD_FLAG_COLUMNS.get(method_n)
    if flag_col and flag_col in df.columns:
        mask = mask | (pd.to_numeric(df[flag_col], errors="coerce").fillna(0).astype(int) == 1)
    text_cols = [c for c in ["technical_means", "title", "application_field"] if c in df.columns]
    for col in text_cols:
        mask = mask | df[col].map(lambda x: method_matches_text(method, x))
    return mask


def topk_method_mask(df: pd.DataFrame, method: str) -> pd.Series:
    mask = df["b_technical_means"].map(lambda x: method_matches_text(method, x))
    method_n = norm(method)
    if method_n in {"u-net", "unet", "u net"} and "b_is_unet_final" in df.columns:
        mask = mask | (pd.to_numeric(df["b_is_unet_final"], errors="coerce").fillna(0).astype(int) == 1)
    return mask


def load_b0_thin() -> pd.DataFrame:
    desired_cols = [
        "publication_number",
        "family_id",
        "year",
        "title",
        "technical_means",
        "application_field",
        "has_text",
        "analysis_include",
        "is_unet_final",
        "is_yolo",
        "is_gan",
        "is_cyclegan",
        "is_transformer",
        "is_attention",
        "is_autoencoder",
        "is_cnn",
        "is_domain_adaptation",
        "is_resnet",
        "is_vgg",
        "is_efficientnet",
    ]
    header = pd.read_csv(FILES["b_contexts"], nrows=0).columns
    usecols = [c for c in desired_cols if c in header]
    return pd.read_csv(FILES["b_contexts"], usecols=usecols)


def load_b0_full(selected_publications: set[str]) -> pd.DataFrame:
    desired_cols = [
        "publication_number",
        "family_id",
        "title",
        "abstract",
        "claims",
        "problem_context",
        "solution_context",
        "technical_means",
        "target_object",
        "effect_context",
        "application_field",
    ]
    header = pd.read_csv(FILES["b_contexts"], nrows=0).columns
    usecols = [c for c in desired_cols if c in header]
    chunks = []
    for chunk in pd.read_csv(FILES["b_contexts"], usecols=usecols, chunksize=5000):
        chunk["publication_number"] = chunk["publication_number"].astype(str)
        hit = chunk[chunk["publication_number"].isin(selected_publications)].copy()
        if not hit.empty:
            chunks.append(hit)
    if not chunks:
        return pd.DataFrame(columns=desired_cols)
    return pd.concat(chunks, ignore_index=True).drop_duplicates("publication_number")


def pick_from_topk(
    topk: pd.DataFrame,
    b0_thin: pd.DataFrame,
    method: str,
    already_selected: set[str],
    n: int,
    year_min: int | None = None,
) -> list[dict[str, Any]]:
    mask = topk_method_mask(topk, method)
    if year_min is not None and "b_year" in topk.columns:
        mask = mask & (pd.to_numeric(topk["b_year"], errors="coerce") >= year_min)
    df = topk[mask].copy()
    if df.empty:
        return []
    df["b_publication_number"] = df["b_publication_number"].astype(str)
    df = df[~df["b_publication_number"].isin(already_selected)]
    if df.empty:
        return []
    df = df.sort_values(["similarity", "neighbor_rank"], ascending=[False, True])
    picks = []
    seen = set()
    has_text_map = {}
    if "has_text" in b0_thin.columns:
        has_text_map = dict(zip(b0_thin["publication_number"].astype(str), b0_thin["has_text"]))
    for _, row in df.iterrows():
        pub = clean_text(row["b_publication_number"])
        if pub in seen:
            continue
        if str(has_text_map.get(pub, "True")).lower() in {"false", "0"}:
            continue
        seen.add(pub)
        picks.append(row.to_dict())
        if len(picks) >= n:
            break
    return picks


def pick_from_context(
    b0_thin: pd.DataFrame,
    method: str,
    already_selected: set[str],
    n: int,
    year_min: int | None = None,
) -> list[dict[str, Any]]:
    mask = context_method_mask(b0_thin, method)
    if year_min is not None and "year" in b0_thin.columns:
        mask = mask & (pd.to_numeric(b0_thin["year"], errors="coerce") >= year_min)
    if "has_text" in b0_thin.columns:
        mask = mask & b0_thin["has_text"].astype(str).str.lower().isin(["true", "1", "yes"])
    df = b0_thin[mask].copy()
    if df.empty:
        return []
    df["publication_number"] = df["publication_number"].astype(str)
    df = df[~df["publication_number"].isin(already_selected)]
    if "year" in df.columns:
        df = df.sort_values(["year", "publication_number"], ascending=[False, True])
    picks = []
    for _, row in df.drop_duplicates("publication_number").head(n).iterrows():
        picks.append(
            {
                "b_publication_number": row.get("publication_number", ""),
                "b_family_id": row.get("family_id", ""),
                "b_year": row.get("year", ""),
                "b_technical_means": row.get("technical_means", ""),
                "b_application_field": row.get("application_field", ""),
            }
        )
    return picks


def candidate_from_method_row(
    row: pd.Series,
    source_name: str,
    source_file: Path,
    pair: dict[str, Any],
    candidate_type: str,
    source_row_index: int,
) -> Candidate:
    method = method_to_display(row)
    return Candidate(
        publication_number=clean_text(pair.get("b_publication_number", "")),
        candidate_type=candidate_type,
        method_name=method,
        source_file=str(source_file.relative_to(BASE)),
        source_row_index=source_row_index,
        method_source=source_name,
        proposed_or_baseline="proposed",
        rank=first_existing(row, ["rank", "specific_rank"]),
        score=first_existing(row, ["gap_score_v2", "gap_score_old", "positive_gap"]),
        gap_score=first_existing(row, ["gap_score_v2", "gap_score_old", "positive_gap", "gap_rate"]),
        similarity_score=pair.get("similarity", ""),
        future_count=first_existing(row, ["B_future_count", "future_count"]),
        future_rate=first_existing(row, ["B_future_rate", "future_rate"]),
        row_data=row.to_dict(),
        pair_data=pair,
    )


def make_candidates() -> tuple[list[Candidate], dict[str, Any]]:
    input_info = {}
    for name, path in FILES.items():
        if path.exists():
            cols = list(pd.read_csv(path, nrows=0).columns)
            try:
                with path.open("rb") as fh:
                    row_count = sum(1 for _ in fh) - 1
            except OSError:
                row_count = None
            input_info[name] = {"path": path, "rows": row_count, "columns": cols}
        else:
            input_info[name] = {"path": path, "missing": True}

    all_methods = read_csv(FILES["all_methods"])
    with_future = read_csv(FILES["with_future"])
    specific = read_csv(FILES["specific_methods"])
    future_growth = read_csv(FILES["future_growth"])
    unet_check = read_csv(FILES["unet_check"])
    b0_thin = load_b0_thin()
    input_info["b_contexts"]["rows"] = len(b0_thin)
    problem_topk = read_csv(FILES["problem_topk"])
    solution_topk = read_csv(FILES["solution_topk"])
    fulltext_topk = read_csv(FILES["fulltext_topk"])

    future_by_method = future_growth.set_index("method").to_dict(orient="index")
    with_future_enriched = with_future.copy()
    for col in ["B_future_count", "B_future_total"]:
        if col not in with_future_enriched.columns:
            with_future_enriched[col] = with_future_enriched["method"].map(
                lambda m: future_by_method.get(m, {}).get(col, "")
            )

    candidates: list[Candidate] = []
    selected_pubs: set[str] = set()

    # A. Proposed method-ranking candidates: method ranking first, B0 publication as review object.
    proposed_methods = with_future_enriched.sort_values("rank").head(23)
    for idx, row in proposed_methods.iterrows():
        method = method_to_display(row)
        picks = pick_from_topk(problem_topk, b0_thin, method, selected_pubs, n=1)
        if not picks:
            picks = pick_from_topk(solution_topk, b0_thin, method, selected_pubs, n=1)
        if not picks:
            picks = pick_from_context(b0_thin, method, selected_pubs, n=1)
        if not picks:
            continue
        cand = candidate_from_method_row(
            row,
            "method_gap_ranking_with_future_full",
            FILES["with_future"],
            picks[0],
            "proposed_top",
            int(idx),
        )
        if cand.publication_number:
            candidates.append(cand)
            selected_pubs.add(cand.publication_number)

    # B. U-Net candidates: pick multiple publication-level examples related to U-Net.
    unet_rows = pd.concat([unet_check, specific[specific["method"].map(norm).eq("u-net")]], ignore_index=True)
    unet_base = unet_rows.iloc[0] if not unet_rows.empty else pd.Series({"method": "u-net", "method_display": "U-Net"})
    unet_picks = pick_from_topk(problem_topk, b0_thin, "U-Net", selected_pubs, n=10)
    if len(unet_picks) < 10:
        selected_for_unet = selected_pubs | {clean_text(p.get("b_publication_number", "")) for p in unet_picks}
        unet_picks.extend(pick_from_topk(solution_topk, b0_thin, "U-Net", selected_for_unet, n=10 - len(unet_picks)))
    if len(unet_picks) < 5:
        unet_picks.extend(pick_from_context(b0_thin, "U-Net", selected_pubs, n=10 - len(unet_picks)))
    for i, pair in enumerate(unet_picks[:10]):
        pub = clean_text(pair.get("b_publication_number", ""))
        if not pub or pub in selected_pubs:
            continue
        cand = candidate_from_method_row(
            unet_base,
            "unet_ranking_check_full",
            FILES["unet_check"],
            pair,
            "unet_related",
            i,
        )
        candidates.append(cand)
        selected_pubs.add(pub)

    # C. Low-rank/random baseline candidates from fulltext top-k.
    rng = random.Random(42)
    low = fulltext_topk.copy()
    if "neighbor_rank" in low.columns:
        low = low[pd.to_numeric(low["neighbor_rank"], errors="coerce") >= 8]
    low = low[~low["b_publication_number"].astype(str).isin(selected_pubs)]
    if "b_technical_means" in low.columns:
        low = low[low["b_technical_means"].fillna("").astype(str).str.len() > 0]
    low_records = low.drop_duplicates("b_publication_number").to_dict(orient="records")
    rng.shuffle(low_records)
    for i, pair in enumerate(low_records[:10]):
        method_name = clean_text(pair.get("b_technical_means", "")) or "random_baseline"
        cand = Candidate(
            publication_number=clean_text(pair.get("b_publication_number", "")),
            candidate_type="random_low_rank",
            method_name=method_name,
            source_file=str(FILES["fulltext_topk"].relative_to(BASE)),
            source_row_index=i,
            method_source="A0_to_B0_fulltext_topk_full",
            proposed_or_baseline="baseline_random",
            rank=pair.get("neighbor_rank", ""),
            score=pair.get("similarity", ""),
            similarity_score=pair.get("similarity", ""),
            pair_data=pair,
        )
        if cand.publication_number:
            candidates.append(cand)
            selected_pubs.add(cand.publication_number)

    # D. Future-growth candidates: include methods with later B-side growth.
    fg = future_growth.copy()
    fg["B_growth_rate_num"] = pd.to_numeric(fg.get("B_growth_rate", 0), errors="coerce").fillna(0)
    fg["B_future_count_num"] = pd.to_numeric(fg.get("B_future_count", 0), errors="coerce").fillna(0)
    fg = fg.sort_values(["B_growth_rate_num", "B_future_count_num"], ascending=[False, False])
    for idx, row in fg.iterrows():
        if sum(c.candidate_type == "future_growth" for c in candidates) >= 10:
            break
        method = method_to_display(row)
        picks = pick_from_topk(problem_topk, b0_thin, method, selected_pubs, n=1, year_min=2019)
        if not picks:
            picks = pick_from_topk(solution_topk, b0_thin, method, selected_pubs, n=1, year_min=2019)
        if not picks:
            picks = pick_from_context(b0_thin, method, selected_pubs, n=1, year_min=2019)
        if not picks:
            continue
        cand = Candidate(
            publication_number=clean_text(picks[0].get("b_publication_number", "")),
            candidate_type="future_growth",
            method_name=method,
            source_file=str(FILES["future_growth"].relative_to(BASE)),
            source_row_index=int(idx),
            method_source="method_future_growth_evaluation_full",
            proposed_or_baseline="proposed",
            rank="",
            score=first_existing(row, ["B_growth_rate", "B_future_rate"]),
            similarity_score=picks[0].get("similarity", ""),
            future_count=first_existing(row, ["B_future_count", "future_count"]),
            future_rate=first_existing(row, ["B_future_rate", "future_rate"]),
            row_data=row.to_dict(),
            pair_data=picks[0],
        )
        if cand.publication_number:
            candidates.append(cand)
            selected_pubs.add(cand.publication_number)

    input_info["B0_contexts_thin_loaded_rows"] = len(b0_thin)
    input_info["selected_publications"] = len(selected_pubs)
    return candidates, input_info


def build_outputs(candidates: list[Candidate], input_info: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_pubs = {c.publication_number for c in candidates if c.publication_number}
    full = load_b0_full(selected_pubs)
    full_by_pub = {clean_text(row["publication_number"]): row.to_dict() for _, row in full.iterrows()}

    blind_rows = []
    key_rows = []
    for i, cand in enumerate(candidates, start=1):
        review_id = f"MR{i:04d}"
        context = full_by_pub.get(cand.publication_number, {})
        pair = cand.pair_data
        family_id = first_existing(context, ["family_id"]) or pair.get("b_family_id", "")
        method_text = " ".join(
            [
                cand.method_name,
                clean_text(context.get("technical_means", "")),
                clean_text(context.get("title", "")),
            ]
        )
        blind_row = {
            "review_id": review_id,
            "publication_number": cand.publication_number,
            "family_id": family_id,
            "title": context.get("title", ""),
            "abstract": context.get("abstract", ""),
            "claims": context.get("claims", ""),
            "problem_context": context.get("problem_context", ""),
            "solution_context": context.get("solution_context", ""),
            "technical_means": context.get("technical_means", cand.method_name),
            "target_object": context.get("target_object", ""),
            "effect_context": context.get("effect_context", ""),
            "application_field": context.get("application_field", pair.get("b_application_field", "")),
            "method_name": cand.method_name,
            "candidate_type": cand.candidate_type,
            "general_term_flag": is_general_term(method_text),
            "specific_method_flag": is_specific_method(method_text),
        }
        for col in REVIEW_BLANK_COLUMNS:
            blind_row[col] = ""
        blind_rows.append(blind_row)

        row_data = cand.row_data
        key_row = {
            "review_id": review_id,
            "publication_number": cand.publication_number,
            "family_id": family_id,
            "candidate_type": cand.candidate_type,
            "method_name": cand.method_name,
            "source_file": cand.source_file,
            "source_row_index": cand.source_row_index,
            "method_source": cand.method_source,
            "proposed_or_baseline": cand.proposed_or_baseline,
            "rank": cand.rank,
            "score": cand.score,
            "gap_score": cand.gap_score,
            "similarity_score": cand.similarity_score,
            "future_count": cand.future_count,
            "future_rate": cand.future_rate,
            "general_term_flag": blind_row["general_term_flag"],
            "specific_method_flag": blind_row["specific_method_flag"],
            "a_publication_number": pair.get("a_publication_number", ""),
            "a_family_id": pair.get("a_family_id", ""),
            "a_year": pair.get("a_year", ""),
            "b_year": pair.get("b_year", ""),
            "neighbor_rank": pair.get("neighbor_rank", ""),
            "a_application_field": pair.get("a_application_field", ""),
            "b_application_field": pair.get("b_application_field", ""),
            "a_technical_means": pair.get("a_technical_means", ""),
            "b_technical_means": pair.get("b_technical_means", ""),
        }
        for col in [
            "method",
            "method_display",
            "A_pre_count",
            "B_pre_count",
            "A_pre_rate",
            "B_pre_rate",
            "gap_rate",
            "positive_gap",
            "gap_score_old",
            "gap_score_v2",
            "B_future_count",
            "B_future_rate",
            "B_growth_rate",
            "future_observed_flag",
        ]:
            key_row[col] = row_data.get(col, "")
        key_rows.append(key_row)

    blind = pd.DataFrame(blind_rows)
    for col in BLIND_COLUMNS:
        if col not in blind.columns:
            blind[col] = ""
    blind = blind[BLIND_COLUMNS]
    leaked = sorted(FORBIDDEN_BLIND_COLUMNS & set(blind.columns))
    if leaked:
        raise ValueError(f"Forbidden columns leaked into blind file: {leaked}")

    key = pd.DataFrame(key_rows)
    return blind, key


def write_rubric(path: Path) -> None:
    text = """# Manual Review Rubric

## 文脈抽出評価

### problem_extraction_score

- 2 = 課題・目的・問題点が正しく抽出されている
- 1 = 一部曖昧だが評価に使える
- 0 = 誤抽出、または不十分

### solution_extraction_score

- 2 = 解決手段・構成・方法が正しく抽出されている
- 1 = 一部曖昧だが評価に使える
- 0 = 誤抽出、または不十分

### technical_means_score

- 2 = 技術手段名として適切で、具体性がある
- 1 = 関係はあるが一般語・抽象語である
- 0 = 技術手段として不適切

### target_object_score

- 2 = 対象物が明確で正しい
- 1 = 一部曖昧だが使える
- 0 = 不明または不適切

## 候補評価

### problem_similarity_score

- 2 = 参照分野と対象分野で課題が明確に近い
- 1 = 一部近いが、対象・用途がずれる
- 0 = 課題が近いとは言いにくい

### solution_relevance_score

- 2 = 解決手段が対象分野の候補として参考になりそう
- 1 = 関係はあるが、候補としては弱い
- 0 = 解決手段として参考にしにくい

### candidate_score

- 3 = ◎ 卒論の代表例として使える
- 2 = ○ 専門家確認候補として妥当
- 1 = △ 関係はあるが弱い・曖昧
- 0 = × 候補として不適切

### representative_flag

- 1 = 代表特許として本文で説明できる
- 0 = 代表特許としては弱い

### final_label

- ◎ / ○ / △ / × のいずれかを記入する
"""
    path.write_text(text, encoding="utf-8")


def write_aggregate_script(path: Path) -> None:
    text = r'''from __future__ import annotations

from pathlib import Path
import argparse

import pandas as pd


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def precision_at_k(df: pd.DataFrame, k: int) -> float | None:
    if "candidate_score" not in df.columns:
        return None
    subset = df.head(k)
    scored = numeric(subset["candidate_score"]).dropna()
    if scored.empty:
        return None
    return float((scored >= 2).mean())


def add_metric(rows: list[dict], section: str, metric: str, value, count: int | None = None) -> None:
    rows.append({"section": section, "metric": metric, "value": value, "count": count if count is not None else ""})


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    def cell(value) -> str:
        if pd.isna(value):
            return ""
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in df[columns].iterrows():
        lines.append("| " + " | ".join(cell(row[col]) for col in columns) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate manual review scores.")
    parser.add_argument("--blind", default="manual_review_blind.csv")
    parser.add_argument("--key", default="manual_review_key.csv")
    parser.add_argument("--out_csv", default="manual_review_summary.csv")
    parser.add_argument("--out_md", default="manual_review_summary.md")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    blind = pd.read_csv(base / args.blind, encoding="utf-8-sig")
    key = pd.read_csv(base / args.key, encoding="utf-8-sig")
    merged = blind.merge(key, on="review_id", how="left", suffixes=("", "_key"))

    rows: list[dict] = []
    if "candidate_score" in merged.columns:
        scores = numeric(merged["candidate_score"]).dropna()
        add_metric(rows, "overall", "candidate_score_mean", scores.mean() if not scores.empty else "", len(scores))
        add_metric(rows, "overall", "candidate_score_median", scores.median() if not scores.empty else "", len(scores))
        add_metric(rows, "overall", "candidate_score_count", len(scores), len(scores))

    if "final_label" in merged.columns:
        label_counts = merged["final_label"].fillna("").astype(str).str.strip()
        label_counts = label_counts[label_counts != ""].value_counts()
        for label, count in label_counts.items():
            add_metric(rows, "final_label_count", str(label), int(count), int(count))

    if {"candidate_type", "candidate_score"}.issubset(merged.columns):
        grouped = merged.assign(candidate_score_num=numeric(merged["candidate_score"]))
        for candidate_type, group in grouped.groupby("candidate_type", dropna=False):
            scored = group["candidate_score_num"].dropna()
            add_metric(
                rows,
                "candidate_type_mean",
                str(candidate_type),
                scored.mean() if not scored.empty else "",
                len(scored),
            )

    if {"proposed_or_baseline", "candidate_score"}.issubset(merged.columns):
        grouped = merged.assign(candidate_score_num=numeric(merged["candidate_score"]))
        for method, group in grouped.groupby("proposed_or_baseline", dropna=False):
            scored = group["candidate_score_num"].dropna()
            add_metric(
                rows,
                "method_mean",
                str(method),
                scored.mean() if not scored.empty else "",
                len(scored),
            )
            ordered = group.copy()
            if "rank" in ordered.columns:
                ordered["_rank_num"] = pd.to_numeric(ordered["rank"], errors="coerce")
                ordered = ordered.sort_values(["_rank_num", "review_id"], na_position="last")
            for k in [5, 10, 20]:
                add_metric(rows, f"precision_at_{k}", str(method), precision_at_k(ordered, k), min(k, len(ordered)))

    for flag_col, label in [
        ("specific_method_flag", "specific_method_flag_1"),
        ("general_term_flag", "general_term_flag_1"),
    ]:
        if {flag_col, "candidate_score"}.issubset(merged.columns):
            subset = merged[pd.to_numeric(merged[flag_col], errors="coerce").fillna(0).astype(int) == 1]
            scored = numeric(subset["candidate_score"]).dropna()
            add_metric(rows, "flag_comparison", label, scored.mean() if not scored.empty else "", len(scored))

    text_cols = [c for c in ["method_name", "technical_means", "title", "problem_context", "solution_context"] if c in merged.columns]
    if text_cols and "candidate_score" in merged.columns:
        hay = merged[text_cols].fillna("").astype(str).agg(" ".join, axis=1)
        unet = merged[hay.str.contains(r"u-?net|unet|u net", case=False, regex=True, na=False)]
        scored = numeric(unet["candidate_score"]).dropna()
        add_metric(rows, "u_net_subset", "candidate_score_mean", scored.mean() if not scored.empty else "", len(scored))
        add_metric(rows, "u_net_subset", "review_count", len(unet), len(unet))

    summary = pd.DataFrame(rows)
    summary.to_csv(base / args.out_csv, index=False, encoding="utf-8-sig")

    md_lines = ["# Manual Review Summary", ""]
    if summary.empty:
        md_lines.append("No scored rows were available yet.")
    else:
        for section, group in summary.groupby("section", sort=False):
            md_lines.extend([f"## {section}", ""])
            md_lines.append(markdown_table(group, ["metric", "value", "count"]))
            md_lines.append("")
    (base / args.out_md).write_text("\n".join(md_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
'''
    path.write_text(text, encoding="utf-8")


def write_log(
    path: Path,
    blind: pd.DataFrame,
    key: pd.DataFrame,
    input_info: dict[str, Any],
    missing_notes: list[str],
) -> None:
    lines = [
        "# Manual Review Generation Log",
        "",
        "## 使用した入力ファイル",
        "",
    ]
    for name, info in input_info.items():
        if not isinstance(info, dict) or "path" not in info:
            continue
        rel = info["path"].relative_to(BASE) if Path(info["path"]).is_absolute() else info["path"]
        if info.get("missing"):
            lines.append(f"- {name}: `{rel}` (missing)")
        else:
            cols = ", ".join(info.get("columns", [])[:20])
            extra = "..." if len(info.get("columns", [])) > 20 else ""
            lines.append(f"- {name}: `{rel}` / rows={info.get('rows')} / columns={cols}{extra}")
    lines.extend(
        [
            "",
            "## 列名対応",
            "",
            "- `publication_number`, `family_id`, `title`, `abstract`, `claims` は `B0_contexts.csv` の同名列を使用。",
            "- `problem_context`, `solution_context`, `technical_means`, `target_object`, `effect_context`, `application_field` は `B0_contexts.csv` の抽出済み列を使用。",
            "- `method_name` はランキング表の `method_display` を優先し、欠損時は `method` または `b_technical_means` を使用。",
            "- `rank`, `score`, `gap_score`, `similarity_score`, `method_source`, `proposed_or_baseline`, `future_count`, `future_rate` は `manual_review_key.csv` にのみ保存。",
            "",
            "## 候補抽出条件",
            "",
            "- A. 提案手法ランキング上位候補: `method_gap_ranking_with_future_full.csv` の `rank` 上位23手法から、B0側の代表特許を `A0_to_B0_problem_topk_full.csv`、`A0_to_B0_solution_topk_full.csv`、`B0_contexts.csv` で探索。",
            "- B. U-Net関連候補: `unet_ranking_check_full.csv` と `specific_methods` の U-Net 行を根拠に、B0側で U-Net フラグまたは技術手段に該当する特許を抽出。",
            "- C. 低順位・ランダム候補: `A0_to_B0_fulltext_topk_full.csv` の `neighbor_rank >= 8` から、本文情報があるB0候補を固定乱数seed=42で抽出。",
            "- D. 将来比較用候補: `method_future_growth_evaluation_full.csv` の `B_growth_rate`, `B_future_count` が大きい手法から、2019年以降のB0代表特許をproblem/solution top-kとcontextで抽出。",
            "- 重複する `publication_number` は評価対象内で1件に統合。",
            "- 評価用blindファイルにはランキング・スコア・手法ソースを入れず、keyファイルに分離。",
            "",
            "## 作成件数",
            "",
            f"- `manual_review_blind.csv`: {len(blind)} rows",
            f"- `manual_review_key.csv`: {len(key)} rows",
        ]
    )
    type_counts = blind["candidate_type"].value_counts().to_dict() if "candidate_type" in blind else {}
    for candidate_type, count in type_counts.items():
        lines.append(f"- {candidate_type}: {count} rows")
    lines.extend(
        [
            "",
            "## 欠損列・欠損値への対応",
            "",
        ]
    )
    if missing_notes:
        lines.extend([f"- {note}" for note in missing_notes])
    else:
        lines.append("- 必須出力列は全て作成。元データ側の欠損値は空欄として保持。")
    lines.extend(
        [
            "",
            "## 注意点",
            "",
            "- このファイル群は人手評価の材料整理であり、候補の良否をCodexが最終判定したものではありません。",
            "- `general_term_flag` と `specific_method_flag` は候補整理用の機械的フラグです。最終評価では本文・請求項・抽出文脈を読んで判断してください。",
            "- `manual_review_blind.csv` には評価バイアスになりやすいrank/score/source系の列を含めていません。",
            "- 集計時は評価記入後に `aggregate_manual_review.py` を同じディレクトリで実行してください。",
            "",
            "## 次に人間がやるべきこと",
            "",
            "1. `manual_review_blind.csv` またはExcel版を開き、rubricに沿って空欄の評価列を記入する。",
            "2. 記入後、`python3 aggregate_manual_review.py` を実行して `manual_review_summary.csv` と `manual_review_summary.md` を作成する。",
            "3. 必要に応じて `manual_review_key.csv` と結合し、rank/score/source別の追加分析を行う。",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def try_write_xlsx(blind: pd.DataFrame, path: Path) -> str:
    try:
        with pd.ExcelWriter(path) as writer:
            blind.to_excel(writer, index=False, sheet_name="manual_review_blind")
        return "created"
    except Exception as exc:  # xlsx is optional; CSV remains authoritative.
        return f"failed: {type(exc).__name__}: {exc}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates, input_info = make_candidates()
    blind, key = build_outputs(candidates, input_info)

    missing_notes: list[str] = []
    for col in BLIND_COLUMNS:
        if col not in blind.columns:
            missing_notes.append(f"出力必須列 `{col}` が欠損したため空欄列として補完。")
    empty_context_rows = int(
        (
            blind[["title", "abstract", "claims", "problem_context", "solution_context"]]
            .fillna("")
            .astype(str)
            .agg("".join, axis=1)
            .str.len()
            == 0
        ).sum()
    )
    if empty_context_rows:
        missing_notes.append(f"本文・文脈情報が全て空の行が {empty_context_rows} 件あります。")

    blind.to_csv(OUT_DIR / "manual_review_blind.csv", index=False, encoding="utf-8-sig")
    key.to_csv(OUT_DIR / "manual_review_key.csv", index=False, encoding="utf-8-sig")
    write_rubric(OUT_DIR / "manual_review_rubric.md")
    write_aggregate_script(OUT_DIR / "aggregate_manual_review.py")
    xlsx_status = try_write_xlsx(blind, OUT_DIR / "manual_review_blind.xlsx")
    input_info["manual_review_blind_xlsx"] = {"path": OUT_DIR / "manual_review_blind.xlsx", "rows": len(blind), "columns": list(blind.columns), "status": xlsx_status}
    if xlsx_status != "created":
        missing_notes.append(f"Excel版の作成に失敗: {xlsx_status}")
    write_log(OUT_DIR / "manual_review_generation_log.md", blind, key, input_info, missing_notes)

    print(f"Wrote {len(blind)} review rows to {OUT_DIR}")
    print(blind["candidate_type"].value_counts().to_string())


if __name__ == "__main__":
    main()
