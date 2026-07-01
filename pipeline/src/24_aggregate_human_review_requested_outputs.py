from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


BASE = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "pipeline/outputs/manual_review_evaluation"
INPUT_XLSX = Path("/Users/h-torii4649/Downloads/manual_review_with_human_filled.xlsx")
INPUT_SHEET = "manual_review_with_llm"
KEY_CSV = OUT_DIR / "manual_review_key.csv"

OUT_SUMMARY_CSV = OUT_DIR / "human_review_summary.csv"
OUT_SUMMARY_MD = OUT_DIR / "human_review_summary.md"
OUT_CANDIDATE_TYPE_CSV = OUT_DIR / "human_candidate_type_summary.csv"
OUT_METHOD_COMPARISON_CSV = OUT_DIR / "human_method_comparison_summary.csv"
OUT_PRECISION_CSV = OUT_DIR / "human_precision_at_k_summary.csv"
OUT_UNET_CSV = OUT_DIR / "human_unet_subset_summary.csv"


def n(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def clean_label(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def md_table(df: pd.DataFrame, columns: list[str]) -> str:
    def cell(v: Any) -> str:
        if pd.isna(v):
            return ""
        return str(v).replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in df[columns].iterrows():
        lines.append("| " + " | ".join(cell(row[col]) for col in columns) + " |")
    return "\n".join(lines)


def label_counts(df: pd.DataFrame, prefix: str = "label") -> dict[str, int]:
    counts = clean_label(df["final_label"]).value_counts()
    return {
        f"{prefix}_◎": int(counts.get("◎", 0)),
        f"{prefix}_○": int(counts.get("○", 0)),
        f"{prefix}_△": int(counts.get("△", 0)),
        f"{prefix}_×": int(counts.get("×", 0)),
    }


def group_stats(df: pd.DataFrame, group_col: str, group_type: str | None = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for value, g in df.groupby(group_col, dropna=False):
        scores = n(g["candidate_score"]).dropna()
        row: dict[str, Any] = {
            "group_value": "missing" if pd.isna(value) or str(value) == "" else str(value),
            "count": int(len(g)),
            "candidate_score_mean": scores.mean() if not scores.empty else "",
            "candidate_score_median": scores.median() if not scores.empty else "",
            "valid_candidate_count_score_ge_2": int((scores >= 2).sum()),
            "valid_candidate_rate_score_ge_2": (scores >= 2).mean() if not scores.empty else "",
            "representative_flag_count": int(n(g["representative_flag"]).fillna(0).sum()),
        }
        row.update(label_counts(g))
        if group_type is not None:
            row = {"group_type": group_type, **row}
        rows.append(row)
    return pd.DataFrame(rows)


def precision_at_k(df: pd.DataFrame, group_col: str, k_values: list[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rank_col = "rank_num"
    for value, g in df.groupby(group_col, dropna=False):
        ordered = g.copy()
        ordered["_review_order"] = range(len(ordered))
        if rank_col in ordered.columns:
            ordered = ordered.sort_values([rank_col, "_review_order"], na_position="last")
            sort_basis = "rank ascending, then review order"
        else:
            sort_basis = "review order"
        for k in k_values:
            subset = ordered.head(k)
            scores = n(subset["candidate_score"]).dropna()
            valid_count = int((scores >= 2).sum())
            rows.append(
                {
                    "proposed_or_baseline": "missing" if pd.isna(value) or str(value) == "" else str(value),
                    "k": k,
                    "evaluated_count": int(len(subset)),
                    "valid_candidate_count_score_ge_2": valid_count,
                    "precision_at_k": valid_count / len(subset) if len(subset) else "",
                    "sort_basis": sort_basis,
                }
            )
    return pd.DataFrame(rows)


def rank_bucket(rank: Any) -> str:
    r = pd.to_numeric(pd.Series([rank]), errors="coerce").iloc[0]
    if pd.isna(r):
        return "rank_missing"
    if r <= 5:
        return "rank_001_005"
    if r <= 10:
        return "rank_006_010"
    if r <= 20:
        return "rank_011_020"
    return "rank_021_plus"


def load_and_normalize() -> pd.DataFrame:
    human = pd.read_excel(INPUT_XLSX, sheet_name=INPUT_SHEET)
    required = ["review_id", "human_candidate_score", "human_final_label", "human_representative_flag"]
    missing = [col for col in required if col not in human.columns]
    if missing:
        raise ValueError(f"Missing required human review columns: {missing}")

    df = human.copy()
    df["candidate_score"] = n(df["human_candidate_score"])
    df["final_label"] = clean_label(df["human_final_label"])
    df["representative_flag"] = n(df["human_representative_flag"]).fillna(0).astype(int)

    if KEY_CSV.exists():
        key_cols = [
            "review_id",
            "candidate_type",
            "proposed_or_baseline",
            "rank",
            "method_source",
            "specific_method_flag",
            "general_term_flag",
        ]
        key = pd.read_csv(KEY_CSV, encoding="utf-8-sig", usecols=lambda c: c in key_cols)
        key = key.rename(
            columns={
                "candidate_type": "key_candidate_type",
                "specific_method_flag": "key_specific_method_flag",
                "general_term_flag": "key_general_term_flag",
            }
        )
        df = df.merge(key, on="review_id", how="left")
        if "candidate_type" not in df.columns:
            df["candidate_type"] = df["key_candidate_type"]
        else:
            df["candidate_type"] = df["candidate_type"].fillna(df.get("key_candidate_type"))
        for source, target in [
            ("key_specific_method_flag", "specific_method_flag"),
            ("key_general_term_flag", "general_term_flag"),
        ]:
            if source in df.columns:
                if target in df.columns:
                    df[target] = df[target].fillna(df[source])
                else:
                    df[target] = df[source]
    else:
        df["proposed_or_baseline"] = "missing_key"
        df["rank"] = pd.NA

    df["rank_num"] = pd.to_numeric(df.get("rank", pd.NA), errors="coerce")
    df["rank_bucket"] = df["rank_num"].map(rank_bucket)
    for col in ["specific_method_flag", "general_term_flag"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = n(df[col]).fillna(0).astype(int)
    return df


def make_overall_summary(df: pd.DataFrame) -> pd.DataFrame:
    scores = n(df["candidate_score"]).dropna()
    rows: list[dict[str, Any]] = [
        {"section": "overall", "metric": "count", "value": int(len(df)), "count": int(len(df))},
        {"section": "overall", "metric": "candidate_score_mean", "value": scores.mean(), "count": int(len(scores))},
        {"section": "overall", "metric": "candidate_score_median", "value": scores.median(), "count": int(len(scores))},
        {
            "section": "overall",
            "metric": "valid_candidate_rate_score_ge_2",
            "value": (scores >= 2).mean(),
            "count": int(len(scores)),
        },
        {
            "section": "overall",
            "metric": "representative_flag_1_count",
            "value": int(n(df["representative_flag"]).fillna(0).sum()),
            "count": int(len(df)),
        },
    ]
    for label, count in clean_label(df["final_label"]).value_counts().items():
        rows.append({"section": "final_label_count", "metric": label, "value": int(count), "count": int(count)})
    for score, count in n(df["candidate_score"]).value_counts().sort_index().items():
        rows.append({"section": "candidate_score_count", "metric": int(score), "value": int(count), "count": int(count)})

    for flag_col in ["specific_method_flag", "general_term_flag"]:
        subset = df[df[flag_col] == 1]
        flag_scores = n(subset["candidate_score"]).dropna()
        rows.extend(
            [
                {
                    "section": "method_flag_comparison",
                    "metric": f"{flag_col}_count",
                    "value": int(len(subset)),
                    "count": int(len(subset)),
                },
                {
                    "section": "method_flag_comparison",
                    "metric": f"{flag_col}_candidate_score_mean",
                    "value": flag_scores.mean() if not flag_scores.empty else "",
                    "count": int(len(flag_scores)),
                },
                {
                    "section": "method_flag_comparison",
                    "metric": f"{flag_col}_valid_rate_score_ge_2",
                    "value": (flag_scores >= 2).mean() if not flag_scores.empty else "",
                    "count": int(len(flag_scores)),
                },
            ]
        )
    return pd.DataFrame(rows)


def make_method_comparison(df: pd.DataFrame) -> pd.DataFrame:
    frames = []
    if "proposed_or_baseline" in df.columns:
        frames.append(group_stats(df, "proposed_or_baseline", "proposed_or_baseline"))
    frames.append(group_stats(df, "specific_method_flag", "specific_method_flag"))
    frames.append(group_stats(df, "general_term_flag", "general_term_flag"))
    frames.append(group_stats(df, "rank_bucket", "rank_bucket"))
    return pd.concat(frames, ignore_index=True)


def make_unet_summary(df: pd.DataFrame) -> pd.DataFrame:
    text_cols = ["title", "method_name", "technical_means", "problem_context", "solution_context", "candidate_type"]
    mask = df[text_cols].fillna("").astype(str).agg(" ".join, axis=1).str.contains(
        r"u-?net|unet|u net", case=False, regex=True
    )
    unet = df[mask].copy()
    scores = n(unet["candidate_score"]).dropna()
    row = {
        "subset": "u_net_related",
        "count": int(len(unet)),
        "candidate_score_mean": scores.mean() if not scores.empty else "",
        "candidate_score_median": scores.median() if not scores.empty else "",
        "valid_candidate_count_score_ge_2": int((scores >= 2).sum()),
        "valid_candidate_rate_score_ge_2": (scores >= 2).mean() if not scores.empty else "",
        "representative_flag_count": int(n(unet["representative_flag"]).fillna(0).sum()),
    }
    row.update(label_counts(unet))
    return pd.DataFrame([row])


def write_summary_md(
    overall: pd.DataFrame,
    candidate_type: pd.DataFrame,
    method: pd.DataFrame,
    precision: pd.DataFrame,
    unet: pd.DataFrame,
) -> None:
    lines = [
        "# Human Review Summary",
        "",
        "人手評価済みの `human_` 列を最終評価として集計した結果です。`human_candidate_score` を `candidate_score`、`human_final_label` を `final_label` として扱っています。",
        "",
        "## Overall",
        "",
        md_table(overall, ["section", "metric", "value", "count"]),
        "",
        "## Candidate Type",
        "",
        md_table(candidate_type, list(candidate_type.columns)),
        "",
        "## Method / Rank Comparison",
        "",
        md_table(method, list(method.columns)),
        "",
        "## Precision@k",
        "",
        md_table(precision, list(precision.columns)),
        "",
        "## U-Net Subset",
        "",
        md_table(unet, list(unet.columns)),
        "",
        "## Notes",
        "",
        "- `manual_review_key.csv` を `review_id` で結合し、`proposed_or_baseline` と `rank` を集計に使用しました。",
        "- 元の `manual_review_with_human_filled.xlsx` は上書きしていません。",
        "- Precision@k は `candidate_score >= 2` を妥当候補として計算しています。",
    ]
    OUT_SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = load_and_normalize()
    overall = make_overall_summary(df)
    candidate_type = group_stats(df, "candidate_type").rename(columns={"group_value": "candidate_type"})
    method = make_method_comparison(df)
    precision = precision_at_k(df, "proposed_or_baseline", [5, 10, 20])
    unet = make_unet_summary(df)

    overall.to_csv(OUT_SUMMARY_CSV, index=False, encoding="utf-8-sig")
    candidate_type.to_csv(OUT_CANDIDATE_TYPE_CSV, index=False, encoding="utf-8-sig")
    method.to_csv(OUT_METHOD_COMPARISON_CSV, index=False, encoding="utf-8-sig")
    precision.to_csv(OUT_PRECISION_CSV, index=False, encoding="utf-8-sig")
    unet.to_csv(OUT_UNET_CSV, index=False, encoding="utf-8-sig")
    write_summary_md(overall, candidate_type, method, precision, unet)

    print(f"Aggregated rows: {len(df)}")
    print("Overall:")
    print(overall.to_string(index=False))
    print("\nCandidate type:")
    print(candidate_type.to_string(index=False))
    print("\nPrecision@k:")
    print(precision.to_string(index=False))
    print("\nU-Net:")
    print(unet.to_string(index=False))


if __name__ == "__main__":
    main()
