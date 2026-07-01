from __future__ import annotations

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
