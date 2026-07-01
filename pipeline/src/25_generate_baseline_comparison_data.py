from __future__ import annotations

import importlib.util
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


BASE = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "pipeline/outputs/manual_review_evaluation"

INPUTS = {
    "human_filled": Path("/Users/h-torii4649/Downloads/manual_review_with_human_filled.xlsx"),
    "manual_review_key": OUT_DIR / "manual_review_key.csv",
    "manual_review_rubric": OUT_DIR / "manual_review_rubric.md",
    "manual_review_generation_log": OUT_DIR / "manual_review_generation_log.md",
    "b0_contexts": BASE / "pipeline/data/processed_full/B0_contexts.csv",
    "a0_contexts": BASE / "pipeline/data/processed_full/A0_contexts.csv",
    "fulltext_topk": BASE / "pipeline/data/processed_full/similarity/A0_to_B0_fulltext_topk_full.csv",
    "problem_topk": BASE / "pipeline/data/processed_full/similarity/A0_to_B0_problem_topk_full.csv",
    "solution_topk": BASE / "pipeline/data/processed_full/similarity/A0_to_B0_solution_topk_full.csv",
    "method_gap_all": BASE / "pipeline/data/processed_full/ranking/method_gap_ranking_all_full.csv",
    "method_gap_specific": BASE / "pipeline/data/processed_full/ranking/method_gap_ranking_specific_methods_full.csv",
    "method_gap_future": BASE / "pipeline/data/processed_full/ranking/method_gap_ranking_with_future_full.csv",
    "method_future_growth": BASE / "pipeline/data/processed_full/ranking/method_future_growth_evaluation_full.csv",
    "unet_check": BASE / "pipeline/data/processed_full/ranking/unet_ranking_check_full.csv",
}

OUT_EXISTING_NORMALIZED = OUT_DIR / "existing_human_review_normalized.csv"
OUT_BLIND_CSV = OUT_DIR / "baseline_review_blind.csv"
OUT_BLIND_XLSX = OUT_DIR / "baseline_review_blind.xlsx"
OUT_KEY_CSV = OUT_DIR / "baseline_review_key.csv"
OUT_LLM_CSV = OUT_DIR / "baseline_review_with_llm_suggestions.csv"
OUT_LLM_XLSX = OUT_DIR / "baseline_review_with_llm_suggestions.xlsx"
OUT_NOTE = OUT_DIR / "baseline_comparison_design_note.md"
OUT_LOG = OUT_DIR / "baseline_generation_log.md"

BLIND_BASE_COLUMNS = [
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
]

HUMAN_COLUMNS = [
    "human_problem_extraction_score",
    "human_solution_extraction_score",
    "human_technical_means_score",
    "human_target_object_score",
    "human_problem_similarity_score",
    "human_solution_relevance_score",
    "human_candidate_score",
    "human_representative_flag",
    "human_final_label",
    "human_reviewer_comment",
    "human_modified_flag",
]

FORBIDDEN_BLIND_COLUMNS = {
    "rank",
    "score",
    "gap_score",
    "similarity",
    "similarity_score",
    "method_source",
    "proposed_or_baseline",
    "source_file",
    "source_row_index",
    "neighbor_rank",
}

SPECIFIC_PATTERNS = [
    r"\bu-?net\b",
    r"\bunet\b",
    r"\bu net\b",
    r"\byolo\b",
    r"\bgan\b",
    r"cyclegan",
    r"transformer",
    r"resnet",
    r"autoencoder",
    r"domain adaptation",
    r"\bcnn\b",
    r"\bsvm\b",
    r"\bpca\b",
    r"k-means",
    r"random forest",
    r"vgg",
    r"\bvit\b",
    r"encoder-decoder",
    r"principal component analysis",
    r"attention",
    r"注意",
]

GENERAL_PATTERNS = [
    "画像セグメンテーション",
    "画像分類",
    "画像前処理",
    "画像生成・再構成",
    "深層学習モデル",
    "機械学習モデル",
    "特徴抽出",
    "欠陥検出",
    "物体検出",
    "撮像装置",
    "検査装置",
    "画像処理",
    "検出方法",
    "image processing",
    "deep learning",
    "machine learning",
    "segmentation",
]


def clean(v: Any) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def csv_row_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        if path.suffix.lower() == ".xlsx":
            return len(pd.read_excel(path, sheet_name=0, usecols=[0]))
        if path.suffix.lower() == ".md":
            return None
        header = pd.read_csv(path, nrows=0).columns
        if len(header) == 0:
            return 0
        first_col = header[0]
        total = 0
        for chunk in pd.read_csv(path, usecols=[first_col], chunksize=100000):
            total += len(chunk)
        return total
    except Exception:
        return None


def input_info() -> dict[str, dict[str, Any]]:
    info: dict[str, dict[str, Any]] = {}
    for name, path in INPUTS.items():
        item: dict[str, Any] = {"path": path, "exists": path.exists(), "rows": None, "columns": []}
        if path.exists():
            try:
                if path.suffix.lower() == ".xlsx":
                    df = pd.read_excel(path, sheet_name=0, nrows=0)
                elif path.suffix.lower() == ".csv":
                    df = pd.read_csv(path, nrows=0)
                else:
                    df = pd.DataFrame()
                item["columns"] = list(df.columns)
                item["rows"] = csv_row_count(path)
            except Exception as exc:
                item["read_error"] = f"{type(exc).__name__}: {exc}"
        info[name] = item
    return info


def is_specific(text: str) -> int:
    s = text.lower()
    return int(any(re.search(pattern, s, flags=re.IGNORECASE) for pattern in SPECIFIC_PATTERNS))


def is_general(text: str) -> int:
    s = text.lower()
    return int(any(term.lower() in s for term in GENERAL_PATTERNS))


def split_methods(value: Any) -> list[str]:
    raw = clean(value)
    if not raw:
        return []
    parts = re.split(r"[;；,，/、]+", raw)
    return [p.strip() for p in parts if p.strip()]


def normalize_existing_review() -> tuple[pd.DataFrame, set[str], dict[str, int]]:
    existing = pd.read_excel(INPUTS["human_filled"], sheet_name="manual_review_with_llm")
    existing["candidate_type_original"] = existing["candidate_type"]
    replacement_count = int((existing["candidate_type"] == "random_low_rank").sum())
    existing["candidate_type"] = existing["candidate_type"].replace(
        {"random_low_rank": "fulltext_low_rank_baseline"}
    )
    existing["candidate_score"] = pd.to_numeric(existing["human_candidate_score"], errors="coerce")
    existing["final_label"] = existing["human_final_label"].fillna("").astype(str).str.strip()
    existing["representative_flag"] = pd.to_numeric(existing["human_representative_flag"], errors="coerce")
    existing.to_csv(OUT_EXISTING_NORMALIZED, index=False, encoding="utf-8-sig")
    return (
        existing,
        set(existing["publication_number"].dropna().astype(str)),
        {
            "rows": len(existing),
            "random_low_rank_replaced": replacement_count,
        },
    )


def load_b0_thin() -> pd.DataFrame:
    desired = [
        "publication_number",
        "family_id",
        "year",
        "title",
        "abstract",
        "technical_means",
        "has_text",
        "application_field",
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
    header = pd.read_csv(INPUTS["b0_contexts"], nrows=0).columns
    usecols = [c for c in desired if c in header]
    df = pd.read_csv(INPUTS["b0_contexts"], usecols=usecols)
    df["publication_number"] = df["publication_number"].astype(str)
    return df


def load_b0_full(publications: set[str]) -> pd.DataFrame:
    desired = [
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
    header = pd.read_csv(INPUTS["b0_contexts"], nrows=0).columns
    usecols = [c for c in desired if c in header]
    chunks = []
    for chunk in pd.read_csv(INPUTS["b0_contexts"], usecols=usecols, chunksize=5000):
        chunk["publication_number"] = chunk["publication_number"].astype(str)
        hit = chunk[chunk["publication_number"].isin(publications)].copy()
        if not hit.empty:
            chunks.append(hit)
    if not chunks:
        return pd.DataFrame(columns=desired)
    return pd.concat(chunks, ignore_index=True).drop_duplicates("publication_number")


def text_present(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.len() > 0


def has_text_mask(df: pd.DataFrame) -> pd.Series:
    mask = text_present(df.get("title", pd.Series("", index=df.index))) | text_present(
        df.get("abstract", pd.Series("", index=df.index))
    )
    if "has_text" in df.columns:
        has_text = df["has_text"].astype(str).str.lower().isin(["true", "1", "yes"])
        preferred = mask & has_text
        return preferred if preferred.sum() >= 30 else mask
    return mask


def pick_true_random(b0: pd.DataFrame, existing_pubs: set[str], selected: set[str]) -> tuple[list[dict[str, Any]], int]:
    pool = b0[~b0["publication_number"].isin(existing_pubs | selected)].copy()
    pool = pool[has_text_mask(pool)]
    before = len(pool)
    pool = pool.sample(frac=1.0, random_state=42)
    picks = pool.drop_duplicates("publication_number").head(30)
    rows = []
    for idx, row in picks.iterrows():
        rows.append(
            {
                "publication_number": clean(row["publication_number"]),
                "candidate_type": "true_random_baseline",
                "method_name": clean(row.get("technical_means", "")) or "true_random_baseline",
                "source_file": rel(INPUTS["b0_contexts"]),
                "source_row_index": int(idx),
                "rank": "",
                "neighbor_rank": "",
                "similarity_score": "",
                "method_source": "B0_contexts_random_seed_42",
            }
        )
    return rows, before - len(picks)


def pick_fulltext_top(b0: pd.DataFrame, existing_pubs: set[str], selected: set[str]) -> tuple[list[dict[str, Any]], int]:
    cols = [
        "neighbor_rank",
        "b_publication_number",
        "similarity",
        "b_family_id",
        "b_technical_means",
        "b_application_field",
    ]
    topk = pd.read_csv(INPUTS["fulltext_topk"], usecols=lambda c: c in cols)
    topk["b_publication_number"] = topk["b_publication_number"].astype(str)
    valid_b0 = set(b0.loc[has_text_mask(b0), "publication_number"].astype(str))
    before = len(topk)
    topk = topk[
        topk["b_publication_number"].isin(valid_b0)
        & ~topk["b_publication_number"].isin(existing_pubs | selected)
    ].copy()
    topk["_source_row_index"] = topk.index
    topk = topk.sort_values(["neighbor_rank", "similarity"], ascending=[True, False])
    topk = topk.drop_duplicates("b_publication_number").head(30)
    rows = []
    for _, row in topk.iterrows():
        rows.append(
            {
                "publication_number": clean(row["b_publication_number"]),
                "candidate_type": "fulltext_top_baseline",
                "method_name": clean(row.get("b_technical_means", "")) or "fulltext_top_baseline",
                "source_file": rel(INPUTS["fulltext_topk"]),
                "source_row_index": int(row["_source_row_index"]),
                "rank": row.get("neighbor_rank", ""),
                "neighbor_rank": row.get("neighbor_rank", ""),
                "similarity_score": row.get("similarity", ""),
                "method_source": "A0_to_B0_fulltext_topk_full",
            }
        )
    return rows, before - len(topk)


def pick_frequency_top(b0: pd.DataFrame, existing_pubs: set[str], selected: set[str]) -> tuple[list[dict[str, Any]], int]:
    pool = b0[
        ~b0["publication_number"].isin(existing_pubs | selected)
        & has_text_mask(b0)
        & text_present(b0.get("technical_means", pd.Series("", index=b0.index)))
    ].copy()
    counts: dict[str, int] = {}
    for value in pool["technical_means"]:
        for method in split_methods(value):
            counts[method] = counts.get(method, 0) + 1
    ranked_methods = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    rows = []
    used = set()
    for rank, (method, freq) in enumerate(ranked_methods, start=1):
        if len(rows) >= 30:
            break
        mask = pool["technical_means"].fillna("").astype(str).map(lambda x: method in split_methods(x))
        candidates = pool[mask & ~pool["publication_number"].isin(used)].copy()
        if candidates.empty:
            continue
        candidates["_title_len"] = candidates["title"].fillna("").astype(str).str.len()
        chosen = candidates.sort_values(["_title_len", "publication_number"], ascending=[False, True]).iloc[0]
        pub = clean(chosen["publication_number"])
        used.add(pub)
        rows.append(
            {
                "publication_number": pub,
                "candidate_type": "frequency_top_baseline",
                "method_name": method,
                "source_file": rel(INPUTS["b0_contexts"]),
                "source_row_index": int(chosen.name),
                "rank": rank,
                "neighbor_rank": "",
                "similarity_score": "",
                "method_source": f"B0_technical_means_frequency_count={freq}",
            }
        )
    return rows, max(0, len(ranked_methods) - len(rows))


def build_baseline_rows(existing_pubs: set[str]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    b0 = load_b0_thin()
    selected: set[str] = set()
    raw_rows: list[dict[str, Any]] = []
    stats: dict[str, Any] = {"b0_thin_rows": len(b0), "overlap_excluded": {}}

    true_random, excluded_random = pick_true_random(b0, existing_pubs, selected)
    raw_rows.extend(true_random)
    selected.update(r["publication_number"] for r in true_random)
    stats["true_random_baseline_count"] = len(true_random)
    stats["overlap_excluded"]["true_random_baseline"] = excluded_random

    fulltext_top, excluded_fulltext = pick_fulltext_top(b0, existing_pubs, selected)
    raw_rows.extend(fulltext_top)
    selected.update(r["publication_number"] for r in fulltext_top)
    stats["fulltext_top_baseline_count"] = len(fulltext_top)
    stats["overlap_excluded"]["fulltext_top_baseline"] = excluded_fulltext

    frequency_top, excluded_frequency = pick_frequency_top(b0, existing_pubs, selected)
    raw_rows.extend(frequency_top)
    selected.update(r["publication_number"] for r in frequency_top)
    stats["frequency_top_baseline_count"] = len(frequency_top)
    stats["overlap_excluded"]["frequency_top_baseline"] = excluded_frequency

    full = load_b0_full(selected)
    full_by_pub = {clean(row["publication_number"]): row.to_dict() for _, row in full.iterrows()}
    blind_rows = []
    key_rows = []
    for i, raw in enumerate(raw_rows, start=1):
        review_id = f"BL{i:04d}"
        pub = raw["publication_number"]
        context = full_by_pub.get(pub, {})
        method_name = raw["method_name"]
        method_text = " ".join(
            [
                method_name,
                clean(context.get("technical_means", "")),
                clean(context.get("title", "")),
            ]
        )
        blind = {
            "review_id": review_id,
            "publication_number": pub,
            "family_id": context.get("family_id", ""),
            "title": context.get("title", ""),
            "abstract": context.get("abstract", ""),
            "claims": context.get("claims", ""),
            "problem_context": context.get("problem_context", ""),
            "solution_context": context.get("solution_context", ""),
            "technical_means": context.get("technical_means", ""),
            "target_object": context.get("target_object", ""),
            "effect_context": context.get("effect_context", ""),
            "application_field": context.get("application_field", ""),
            "method_name": method_name,
            "candidate_type": raw["candidate_type"],
            "general_term_flag": is_general(method_text),
            "specific_method_flag": is_specific(method_text),
        }
        for col in HUMAN_COLUMNS:
            blind[col] = ""
        blind_rows.append(blind)
        key_rows.append(
            {
                "review_id": review_id,
                "publication_number": pub,
                "candidate_type": raw["candidate_type"],
                "source_file": raw["source_file"],
                "source_row_index": raw["source_row_index"],
                "rank": raw["rank"],
                "score": raw["similarity_score"],
                "neighbor_rank": raw["neighbor_rank"],
                "similarity_score": raw["similarity_score"],
                "method_source": raw["method_source"],
                "method_name": method_name,
                "proposed_or_baseline": "baseline",
            }
        )

    blind_df = pd.DataFrame(blind_rows)
    for col in BLIND_BASE_COLUMNS + HUMAN_COLUMNS:
        if col not in blind_df.columns:
            blind_df[col] = ""
    blind_df = blind_df[BLIND_BASE_COLUMNS + HUMAN_COLUMNS]
    leaked = sorted(FORBIDDEN_BLIND_COLUMNS & set(blind_df.columns))
    if leaked:
        raise ValueError(f"Bias columns leaked into baseline blind file: {leaked}")
    return blind_df, pd.DataFrame(key_rows), stats


def load_llm_evaluator():
    script = BASE / "pipeline/src/22_create_llm_initial_review.py"
    spec = importlib.util.spec_from_file_location("llm_initial_review", script)
    if spec is None or spec.loader is None:
        return None, []
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate_row, module.LLM_COLUMNS


def add_llm_suggestions(blind: pd.DataFrame) -> pd.DataFrame | None:
    evaluator, llm_columns = load_llm_evaluator()
    if evaluator is None:
        return None
    base_cols = [c for c in BLIND_BASE_COLUMNS if c in blind.columns]
    llm_rows = [evaluator(row) for _, row in blind[base_cols].iterrows()]
    llm_df = pd.DataFrame(llm_rows)
    # Put LLM suggestions before human blanks for easier review.
    no_human = blind[[c for c in blind.columns if c not in HUMAN_COLUMNS]].copy()
    human = blind[HUMAN_COLUMNS].copy()
    for col in llm_columns:
        if col not in llm_df.columns:
            llm_df[col] = ""
    return pd.concat([no_human, llm_df[llm_columns], human], axis=1)


def write_xlsx(df: pd.DataFrame, path: Path, sheet_name: str) -> None:
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)


def write_design_note() -> None:
    text = """# Baseline Comparison Design Note

既存評価で `random_low_rank` として扱っていた候補は、完全なランダム抽出ではなく、全文BERT top-k表の低順位側から抽出された比較候補である。そのため、本比較では名称を `fulltext_low_rank_baseline` に変更し、真のランダムベースラインとは区別する。

新たに `true_random_baseline` として、B0文脈データ全体から本文情報を持つ特許を固定乱数seed=42で抽出した。また、全文BERTによる正式な比較対象として `fulltext_top_baseline` を作成し、`A0_to_B0_fulltext_topk_full.csv` の上位候補からB0側特許を抽出した。さらに、B0内で頻度の高い `technical_means` に対応する代表特許を `frequency_top_baseline` として作成した。

本比較では、提案手法が高スコア候補を出せるかだけでなく、候補理由の説明可能性、すなわち課題文脈・解決手段・技術手段・対象物の対応が人間にとって確認しやすいかも評価対象とする。LLM支援による仮評価を用いる場合でも、最終的な `human_candidate_score` と `human_final_label` は著者が確認・修正した人手評価を用いる。
"""
    OUT_NOTE.write_text(text, encoding="utf-8")


def write_log(info: dict[str, dict[str, Any]], existing_stats: dict[str, int], baseline_stats: dict[str, Any], blind: pd.DataFrame) -> None:
    lines = ["# Baseline Generation Log", ""]
    lines.extend(["## 使用した入力ファイル", ""])
    for name, item in info.items():
        status = "exists" if item.get("exists") else "missing"
        cols = ", ".join(item.get("columns", [])[:20])
        extra = "..." if len(item.get("columns", [])) > 20 else ""
        lines.append(f"- {name}: `{rel(item['path'])}` / {status} / rows={item.get('rows')} / columns={cols}{extra}")
    lines.extend(
        [
            "",
            "## 既存評価ファイル",
            "",
            f"- 行数: {existing_stats['rows']}",
            f"- `random_low_rank` から `fulltext_low_rank_baseline` への置換件数: {existing_stats['random_low_rank_replaced']}",
            "- 元の candidate_type は `candidate_type_original` として `existing_human_review_normalized.csv` に保持。",
            "",
            "## 追加ベースライン抽出条件と件数",
            "",
            f"- true_random_baseline: B0_contextsから本文情報あり、既存候補と非重複、seed=42で抽出 / 件数={baseline_stats['true_random_baseline_count']}",
            f"- fulltext_top_baseline: A0_to_B0_fulltext_topk_fullのneighbor_rank昇順・similarity降順、既存候補と非重複 / 件数={baseline_stats['fulltext_top_baseline_count']}",
            f"- frequency_top_baseline: B0 technical_means頻度上位から代表特許を抽出、既存候補と非重複 / 件数={baseline_stats['frequency_top_baseline_count']}",
            "",
            "## 重複除外・候補除外",
            "",
        ]
    )
    for key, value in baseline_stats.get("overlap_excluded", {}).items():
        lines.append(f"- {key}: 除外または未採用候補の概数={value}")
    lines.extend(
        [
            "",
            "## 欠損列への対応",
            "",
            "- B0_contexts側で欠損している文脈列は空欄として保持。",
            "- has_text列がある場合は has_text=True を優先し、titleまたはabstractが空でない候補に限定。",
            "- human_評価列は追加評価前の空欄として作成。",
            "",
            "## 作成した出力ファイル",
            "",
            f"- `{rel(OUT_EXISTING_NORMALIZED)}`",
            f"- `{rel(OUT_BLIND_CSV)}`",
            f"- `{rel(OUT_BLIND_XLSX)}`",
            f"- `{rel(OUT_KEY_CSV)}`",
            f"- `{rel(OUT_LLM_CSV)}`",
            f"- `{rel(OUT_LLM_XLSX)}`",
            f"- `{rel(OUT_NOTE)}`",
            f"- `{rel(OUT_LOG)}`",
            "- `pipeline/outputs/manual_review_evaluation/aggregate_final_human_review.py`",
            "",
            "## 確認",
            "",
            f"- 追加評価対象件数: {len(blind)}",
            f"- candidate_type別件数: {blind['candidate_type'].value_counts().to_dict()}",
            f"- 追加評価用blindファイルへのrank/score/similarity/source列混入: {sorted(FORBIDDEN_BLIND_COLUMNS & set(blind.columns))}",
            "",
            "## 次に人間がやるべきこと",
            "",
            "1. `baseline_review_blind.xlsx` または `baseline_review_with_llm_suggestions.xlsx` を開き、human_列に評価を記入する。",
            "2. 評価済みファイルを `baseline_review_with_human_filled.xlsx` として保存する。",
            "3. `aggregate_final_human_review.py` を実行し、既存評価と追加ベースライン評価を結合集計する。",
        ]
    )
    OUT_LOG.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    info = input_info()
    _, existing_pubs, existing_stats = normalize_existing_review()
    blind, key, baseline_stats = build_baseline_rows(existing_pubs)

    blind.to_csv(OUT_BLIND_CSV, index=False, encoding="utf-8-sig")
    write_xlsx(blind, OUT_BLIND_XLSX, "baseline_review_blind")
    key.to_csv(OUT_KEY_CSV, index=False, encoding="utf-8-sig")

    llm = add_llm_suggestions(blind)
    if llm is not None:
        llm.to_csv(OUT_LLM_CSV, index=False, encoding="utf-8-sig")
        write_xlsx(llm, OUT_LLM_XLSX, "baseline_with_llm")

    write_design_note()
    write_log(info, existing_stats, baseline_stats, blind)

    print(f"Wrote existing normalized rows: {existing_stats['rows']}")
    print(f"Wrote baseline blind rows: {len(blind)}")
    print(blind["candidate_type"].value_counts().to_string())
    print(f"Baseline key rows: {len(key)}")


if __name__ == "__main__":
    main()
