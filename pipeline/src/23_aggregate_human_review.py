from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


BASE = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "pipeline/outputs/manual_review_evaluation"
INPUT_XLSX = Path("/Users/h-torii4649/Downloads/manual_review_with_human_filled.xlsx")
SHEET_NAME = "manual_review_with_llm"

OUT_NORMALIZED_CSV = OUT_DIR / "human_review_filled_normalized.csv"
OUT_NORMALIZED_XLSX = OUT_DIR / "human_review_filled_normalized.xlsx"
OUT_SUMMARY_CSV = OUT_DIR / "human_review_summary.csv"
OUT_SUMMARY_MD = OUT_DIR / "human_review_summary.md"
OUT_COMPARISON_CSV = OUT_DIR / "human_vs_llm_review_comparison.csv"
OUT_COMPARISON_MD = OUT_DIR / "human_vs_llm_review_comparison.md"
OUT_LOG = OUT_DIR / "human_review_aggregation_log.md"

HUMAN_TO_FINAL = {
    "human_problem_extraction_score": "final_problem_extraction_score",
    "human_solution_extraction_score": "final_solution_extraction_score",
    "human_technical_means_score": "final_technical_means_score",
    "human_target_object_score": "final_target_object_score",
    "human_problem_similarity_score": "final_problem_similarity_score",
    "human_solution_relevance_score": "final_solution_relevance_score",
    "human_candidate_score": "final_candidate_score",
    "human_representative_flag": "final_representative_flag",
    "human_final_label": "final_label",
    "human_reviewer_comment": "final_reviewer_comment",
}

FORBIDDEN_REVIEW_COLUMNS = {
    "rank",
    "score",
    "gap_score",
    "similarity_score",
    "method_source",
    "proposed_or_baseline",
}


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    def cell(value: Any) -> str:
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


def precision_at_order(df: pd.DataFrame, k: int, score_col: str = "human_candidate_score") -> float | None:
    subset = df.head(k)
    scores = num(subset[score_col]).dropna()
    if scores.empty:
        return None
    return float((scores >= 2).mean())


def build_normalized(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for src, dst in HUMAN_TO_FINAL.items():
        normalized[dst] = normalized[src] if src in normalized.columns else ""
    return normalized


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    scores = num(df["human_candidate_score"]).dropna()
    rows.extend(
        [
            {"section": "overall", "metric": "reviewed_count", "value": len(df), "count": len(df)},
            {"section": "overall", "metric": "candidate_score_mean", "value": scores.mean(), "count": len(scores)},
            {"section": "overall", "metric": "candidate_score_median", "value": scores.median(), "count": len(scores)},
            {"section": "overall", "metric": "valid_candidate_rate_score_ge_2", "value": (scores >= 2).mean(), "count": len(scores)},
            {
                "section": "overall",
                "metric": "representative_flag_count",
                "value": int(num(df["human_representative_flag"]).fillna(0).sum()),
                "count": len(df),
            },
        ]
    )

    for label, count in df["human_final_label"].fillna("").astype(str).value_counts().items():
        rows.append({"section": "final_label_count", "metric": label, "value": int(count), "count": int(count)})

    for score, count in num(df["human_candidate_score"]).value_counts().sort_index().items():
        rows.append({"section": "candidate_score_count", "metric": int(score), "value": int(count), "count": int(count)})

    grouped = df.assign(human_candidate_score_num=num(df["human_candidate_score"]))
    for candidate_type, group in grouped.groupby("candidate_type", dropna=False):
        g = group["human_candidate_score_num"].dropna()
        rows.append(
            {
                "section": "candidate_type",
                "metric": str(candidate_type),
                "value": g.mean() if not g.empty else "",
                "count": len(g),
            }
        )
        rows.append(
            {
                "section": "candidate_type_valid_rate",
                "metric": str(candidate_type),
                "value": (g >= 2).mean() if not g.empty else "",
                "count": len(g),
            }
        )

    for k in [5, 10, 20, 50]:
        rows.append(
            {
                "section": "precision_at_review_order",
                "metric": f"precision_at_{k}",
                "value": precision_at_order(df, k),
                "count": min(k, len(df)),
            }
        )

    unet_mask = (
        df[["title", "method_name", "technical_means", "candidate_type", "problem_context", "solution_context"]]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .str.contains(r"u-?net|unet|u net", case=False, regex=True)
    )
    unet_scores = num(df.loc[unet_mask, "human_candidate_score"]).dropna()
    rows.extend(
        [
            {"section": "u_net_subset", "metric": "count", "value": int(unet_mask.sum()), "count": int(unet_mask.sum())},
            {
                "section": "u_net_subset",
                "metric": "candidate_score_mean",
                "value": unet_scores.mean() if not unet_scores.empty else "",
                "count": len(unet_scores),
            },
            {
                "section": "u_net_subset",
                "metric": "valid_candidate_rate_score_ge_2",
                "value": (unet_scores >= 2).mean() if not unet_scores.empty else "",
                "count": len(unet_scores),
            },
        ]
    )
    return pd.DataFrame(rows)


def build_comparison(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    comp = df[
        [
            "review_id",
            "publication_number",
            "title",
            "candidate_type",
            "method_name",
            "llm_candidate_score",
            "human_candidate_score",
            "llm_final_label",
            "human_final_label",
            "llm_confidence",
            "human_modified_flag",
            "llm_reviewer_comment_short",
            "human_reviewer_comment",
        ]
    ].copy()
    comp["score_delta_human_minus_llm"] = num(comp["human_candidate_score"]) - num(comp["llm_candidate_score"])
    comp["label_agreement"] = comp["llm_final_label"].astype(str).str.strip() == comp["human_final_label"].astype(str).str.strip()
    comp["score_agreement"] = num(comp["human_candidate_score"]) == num(comp["llm_candidate_score"])

    rows: list[dict[str, Any]] = []
    rows.append({"section": "agreement", "metric": "score_agreement_rate", "value": comp["score_agreement"].mean(), "count": len(comp)})
    rows.append({"section": "agreement", "metric": "label_agreement_rate", "value": comp["label_agreement"].mean(), "count": len(comp)})
    rows.append(
        {
            "section": "agreement",
            "metric": "human_modified_flag_count",
            "value": int(num(comp["human_modified_flag"]).fillna(0).sum()),
            "count": len(comp),
        }
    )
    rows.append(
        {
            "section": "agreement",
            "metric": "mean_score_delta_human_minus_llm",
            "value": comp["score_delta_human_minus_llm"].mean(),
            "count": len(comp),
        }
    )
    for candidate_type, group in comp.groupby("candidate_type", dropna=False):
        rows.append(
            {
                "section": "agreement_by_candidate_type",
                "metric": str(candidate_type),
                "value": group["score_agreement"].mean(),
                "count": len(group),
            }
        )
    return comp, pd.DataFrame(rows)


def write_summary_md(summary: pd.DataFrame, comparison_summary: pd.DataFrame) -> None:
    lines = ["# Human Review Summary", ""]
    for section, group in summary.groupby("section", sort=False):
        lines.extend([f"## {section}", "", markdown_table(group, ["metric", "value", "count"]), ""])
    lines.extend(["# Human vs LLM Comparison", ""])
    for section, group in comparison_summary.groupby("section", sort=False):
        lines.extend([f"## {section}", "", markdown_table(group, ["metric", "value", "count"]), ""])
    OUT_SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def write_comparison_md(comparison: pd.DataFrame, comparison_summary: pd.DataFrame) -> None:
    changed = comparison[~comparison["score_agreement"]].copy()
    changed["abs_delta"] = changed["score_delta_human_minus_llm"].abs()
    changed = changed.sort_values(["abs_delta", "review_id"], ascending=[False, True]).head(20)
    lines = ["# Human vs LLM Review Comparison", ""]
    for section, group in comparison_summary.groupby("section", sort=False):
        lines.extend([f"## {section}", "", markdown_table(group, ["metric", "value", "count"]), ""])
    lines.extend(["## Largest Score Differences", ""])
    if changed.empty:
        lines.append("All human candidate scores matched the LLM suggestions.")
    else:
        lines.append(
            markdown_table(
                changed,
                [
                    "review_id",
                    "candidate_type",
                    "method_name",
                    "llm_candidate_score",
                    "human_candidate_score",
                    "score_delta_human_minus_llm",
                    "llm_final_label",
                    "human_final_label",
                ],
            )
        )
    OUT_COMPARISON_MD.write_text("\n".join(lines), encoding="utf-8")


def write_log(df: pd.DataFrame, summary: pd.DataFrame, comparison_summary: pd.DataFrame) -> None:
    lines = [
        "# Human Review Aggregation Log",
        "",
        "## 入力",
        "",
        f"- `{INPUT_XLSX}`",
        f"- sheet: `{SHEET_NAME}`",
        "",
        "## 出力",
        "",
        f"- `{OUT_NORMALIZED_CSV.relative_to(BASE)}`",
        f"- `{OUT_NORMALIZED_XLSX.relative_to(BASE)}`",
        f"- `{OUT_SUMMARY_CSV.relative_to(BASE)}`",
        f"- `{OUT_SUMMARY_MD.relative_to(BASE)}`",
        f"- `{OUT_COMPARISON_CSV.relative_to(BASE)}`",
        f"- `{OUT_COMPARISON_MD.relative_to(BASE)}`",
        "",
        "## 集計条件",
        "",
        "- `human_` 列を人間による最終評価として集計しました。",
        "- 元Excelファイルは変更していません。",
        "- `rank`, `score`, `gap_score`, `similarity_score`, `method_source`, `proposed_or_baseline` は人間評価ファイルには含まれていません。",
        "- Precision@k相当は、評価ファイルの行順に対して `human_candidate_score >= 2` を妥当候補として算出しました。",
        "",
        "## 確認",
        "",
        f"- 集計日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 行数: {len(df)}",
        f"- human_candidate_score 記入件数: {num(df['human_candidate_score']).notna().sum()}",
        f"- human_final_label 記入件数: {df['human_final_label'].notna().sum()}",
    ]
    OUT_LOG.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = pd.read_excel(INPUT_XLSX, sheet_name=SHEET_NAME)
    leaked = sorted(FORBIDDEN_REVIEW_COLUMNS & set(df.columns))
    if leaked:
        raise ValueError(f"Bias-prone columns unexpectedly found in human review sheet: {leaked}")

    normalized = build_normalized(df)
    summary = build_summary(df)
    comparison, comparison_summary = build_comparison(df)

    normalized.to_csv(OUT_NORMALIZED_CSV, index=False, encoding="utf-8-sig")
    summary.to_csv(OUT_SUMMARY_CSV, index=False, encoding="utf-8-sig")
    comparison.to_csv(OUT_COMPARISON_CSV, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(OUT_NORMALIZED_XLSX) as writer:
        normalized.to_excel(writer, index=False, sheet_name="human_review_normalized")
        summary.to_excel(writer, index=False, sheet_name="summary")
        comparison_summary.to_excel(writer, index=False, sheet_name="llm_comparison_summary")
    write_summary_md(summary, comparison_summary)
    write_comparison_md(comparison, comparison_summary)
    write_log(df, summary, comparison_summary)

    print(f"Aggregated human review rows: {len(df)}")
    print(df["human_final_label"].value_counts().to_string())
    print(df["human_candidate_score"].value_counts().sort_index().to_string())
    print(comparison_summary.to_string(index=False))


if __name__ == "__main__":
    main()
