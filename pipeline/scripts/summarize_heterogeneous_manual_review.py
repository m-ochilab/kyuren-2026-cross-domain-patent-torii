from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


BASE = Path(__file__).resolve().parents[2]
REVIEW_DIR = BASE / "pipeline/outputs/heterogeneous_manual_review"
DEFAULT_INPUTS = [
    Path("/Users/h-torii4649/Downloads/heterogeneous_manual_review_final_strict.csv"),
    REVIEW_DIR / "heterogeneous_manual_review_final_strict.csv",
    REVIEW_DIR / "heterogeneous_manual_review_with_human_filled.csv",
    REVIEW_DIR / "heterogeneous_manual_review_with_human_filled.xlsx",
    REVIEW_DIR / "heterogeneous_manual_review_blind.csv",
]

OUT_SUMMARY = REVIEW_DIR / "heterogeneous_manual_review_summary.csv"
OUT_BY_CLUSTER = REVIEW_DIR / "heterogeneous_manual_review_by_cluster.csv"
OUT_FINAL = REVIEW_DIR / "heterogeneous_manual_review_final.csv"

LABEL_ORDER = ["◎", "○", "△", "×"]


def read_review_file() -> tuple[pd.DataFrame, Path]:
    for path in DEFAULT_INPUTS:
        if not path.exists():
            continue
        if path.suffix.lower() == ".xlsx":
            return pd.read_excel(path), path
        return pd.read_csv(path, encoding="utf-8-sig"), path
    raise FileNotFoundError("No heterogeneous manual review input file found.")


def clean_label(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def label_counts(df: pd.DataFrame) -> dict[str, int]:
    counts = df["human_label_clean"].value_counts()
    return {f"label_{label}_count": int(counts.get(label, 0)) for label in LABEL_ORDER}


def summarize_overall(df: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    evaluated = df[df["human_label_clean"] != ""]
    rows: list[dict[str, Any]] = [
        {"metric": "source_file", "value": str(source_path)},
        {"metric": "total_rows", "value": len(df)},
        {"metric": "evaluated_rows", "value": len(evaluated)},
        {"metric": "unevaluated_rows", "value": len(df) - len(evaluated)},
    ]
    counts = label_counts(evaluated)
    for key, value in counts.items():
        rows.append({"metric": key, "value": value})
    denom = len(evaluated)
    strong = counts["label_◎_count"] + counts["label_○_count"]
    broad = strong + counts["label_△_count"]
    rows.extend(
        [
            {"metric": "strong_or_plausible_count_◎○", "value": strong},
            {"metric": "strong_or_plausible_rate_◎○", "value": strong / denom if denom else ""},
            {"metric": "broad_candidate_count_◎○△", "value": broad},
            {"metric": "broad_candidate_rate_◎○△", "value": broad / denom if denom else ""},
        ]
    )
    return pd.DataFrame(rows)


def summarize_by_cluster(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for cluster, group in df.groupby("cluster", dropna=False):
        evaluated = group[group["human_label_clean"] != ""]
        counts = label_counts(evaluated)
        strong = counts["label_◎_count"] + counts["label_○_count"]
        broad = strong + counts["label_△_count"]
        denom = len(evaluated)
        row: dict[str, Any] = {
            "cluster": "missing" if pd.isna(cluster) else str(cluster),
            "total_rows": len(group),
            "evaluated_rows": len(evaluated),
            "unevaluated_rows": len(group) - len(evaluated),
            **counts,
            "strong_or_plausible_count_◎○": strong,
            "strong_or_plausible_rate_◎○": strong / denom if denom else "",
            "broad_candidate_count_◎○△": broad,
            "broad_candidate_rate_◎○△": broad / denom if denom else "",
        }
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["cluster"])


def main() -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    df, source_path = read_review_file()
    if "human_label" not in df.columns:
        raise ValueError("Input file must contain human_label column.")
    if "cluster" not in df.columns:
        raise ValueError("Input file must contain cluster column.")

    df = df.copy()
    df["human_label_clean"] = df["human_label"].map(clean_label)
    df["is_strong_or_plausible_◎○"] = df["human_label_clean"].isin(["◎", "○"]).astype(int)
    df["is_broad_candidate_◎○△"] = df["human_label_clean"].isin(["◎", "○", "△"]).astype(int)
    df["evaluation_status"] = df["human_label_clean"].map(lambda x: "evaluated" if x else "unevaluated")

    summary = summarize_overall(df, source_path)
    by_cluster = summarize_by_cluster(df)

    df.to_csv(OUT_FINAL, index=False, encoding="utf-8-sig")
    summary.to_csv(OUT_SUMMARY, index=False, encoding="utf-8-sig")
    by_cluster.to_csv(OUT_BY_CLUSTER, index=False, encoding="utf-8-sig")

    print(f"source: {source_path}")
    print(f"rows: {len(df)}")
    print(summary.to_string(index=False))
    print(by_cluster.to_string(index=False))


if __name__ == "__main__":
    main()
