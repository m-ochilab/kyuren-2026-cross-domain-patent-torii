from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


BASE = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent

EXISTING_CSV = OUT_DIR / "existing_human_review_normalized.csv"
BASELINE_BLIND_CSV = OUT_DIR / "baseline_review_blind.csv"
BASELINE_HUMAN_CSV_CANDIDATES = [
    Path("/Users/h-torii4649/Downloads/baseline_review_with_human_filled_strict.csv"),
    OUT_DIR / "baseline_review_with_human_filled_strict.csv",
    OUT_DIR / "baseline_review_with_human_filled.csv",
    Path("/Users/h-torii4649/Downloads/baseline_review_with_human_filled.csv"),
]
BASELINE_HUMAN_XLSX_CANDIDATES = [
    OUT_DIR / "baseline_review_with_human_filled.xlsx",
    Path("/Users/h-torii4649/Downloads/baseline_review_with_human_filled.xlsx"),
]
MANUAL_KEY_CSV = OUT_DIR / "manual_review_key.csv"
BASELINE_KEY_CSV = OUT_DIR / "baseline_review_key.csv"

OUT_ALL = OUT_DIR / "final_human_review_all.csv"
OUT_CANDIDATE_TYPE = OUT_DIR / "final_candidate_type_summary.csv"
OUT_METHOD = OUT_DIR / "final_method_comparison_summary.csv"
OUT_PRECISION = OUT_DIR / "final_precision_at_k_summary.csv"
OUT_UNET = OUT_DIR / "final_unet_subset_summary.csv"
OUT_MD = OUT_DIR / "final_human_review_summary.md"


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


def label_counts(df: pd.DataFrame) -> dict[str, int]:
    counts = clean_label(df["final_label"]).value_counts()
    return {
        "label_◎": int(counts.get("◎", 0)),
        "label_○": int(counts.get("○", 0)),
        "label_△": int(counts.get("△", 0)),
        "label_×": int(counts.get("×", 0)),
    }


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


def load_key(path: Path, prefix: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["review_id"])
    key_cols = [
        "review_id",
        "candidate_type",
        "proposed_or_baseline",
        "rank",
        "neighbor_rank",
        "method_source",
        "specific_method_flag",
        "general_term_flag",
    ]
    key = pd.read_csv(path, encoding="utf-8-sig", usecols=lambda c: c in key_cols)
    key = key.rename(
        columns={
            "candidate_type": f"{prefix}_candidate_type",
            "specific_method_flag": f"{prefix}_specific_method_flag",
            "general_term_flag": f"{prefix}_general_term_flag",
        }
    )
    return key


def normalize_review(df: pd.DataFrame, source_group: str) -> pd.DataFrame:
    out = df.copy()
    if "candidate_type_original" not in out.columns:
        out["candidate_type_original"] = out.get("candidate_type", "")
    out["candidate_type"] = out.get("candidate_type", "").replace({"random_low_rank": "fulltext_low_rank_baseline"})
    out["candidate_score"] = n(out.get("human_candidate_score", pd.Series(pd.NA, index=out.index)))
    out["final_label"] = clean_label(out.get("human_final_label", pd.Series("", index=out.index)))
    out["representative_flag"] = n(out.get("human_representative_flag", pd.Series(0, index=out.index))).fillna(0)
    out["review_source_group"] = source_group
    out["evaluation_status"] = out["candidate_score"].map(lambda x: "evaluated" if pd.notna(x) else "unevaluated")
    return out


def read_baseline_review() -> tuple[pd.DataFrame, str]:
    for path in BASELINE_HUMAN_CSV_CANDIDATES:
        if path.exists():
            return pd.read_csv(path, encoding="utf-8-sig"), str(path)
    for path in BASELINE_HUMAN_XLSX_CANDIDATES:
        if path.exists():
            xl = pd.ExcelFile(path)
            sheet = "baseline_with_llm" if "baseline_with_llm" in xl.sheet_names else xl.sheet_names[0]
            return pd.read_excel(path, sheet_name=sheet), str(path)
    if BASELINE_BLIND_CSV.exists():
        return pd.read_csv(BASELINE_BLIND_CSV, encoding="utf-8-sig"), str(BASELINE_BLIND_CSV)
    return pd.DataFrame(), "missing"


def load_all() -> tuple[pd.DataFrame, str]:
    existing = pd.read_csv(EXISTING_CSV, encoding="utf-8-sig")
    existing = normalize_review(existing, "existing_review")
    manual_key = load_key(MANUAL_KEY_CSV, "key")
    if not manual_key.empty:
        existing = existing.merge(manual_key, on="review_id", how="left")

    baseline_raw, baseline_source = read_baseline_review()
    if not baseline_raw.empty:
        baseline = normalize_review(baseline_raw, "additional_baseline")
        baseline_key = load_key(BASELINE_KEY_CSV, "key")
        if not baseline_key.empty:
            baseline = baseline.merge(baseline_key, on="review_id", how="left")
        all_df = pd.concat([existing, baseline], ignore_index=True, sort=False)
    else:
        all_df = existing

    if "key_candidate_type" in all_df.columns:
        all_df["candidate_type"] = all_df["candidate_type"].fillna(all_df["key_candidate_type"])
    for src, dst in [("key_specific_method_flag", "specific_method_flag"), ("key_general_term_flag", "general_term_flag")]:
        if src in all_df.columns:
            if dst in all_df.columns:
                all_df[dst] = all_df[dst].fillna(all_df[src])
            else:
                all_df[dst] = all_df[src]
    for col in ["specific_method_flag", "general_term_flag"]:
        if col not in all_df.columns:
            all_df[col] = 0
        all_df[col] = n(all_df[col]).fillna(0).astype(int)
    if "proposed_or_baseline" not in all_df.columns:
        all_df["proposed_or_baseline"] = ""
    if "rank" not in all_df.columns:
        all_df["rank"] = pd.NA
    all_df["rank_num"] = n(all_df["rank"])
    all_df["rank_bucket"] = all_df["rank_num"].map(rank_bucket)
    return all_df, baseline_source


def group_summary(scored: pd.DataFrame, group_col: str, group_type: str | None = None) -> pd.DataFrame:
    rows = []
    for value, g in scored.groupby(group_col, dropna=False):
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
        if group_type:
            row = {"group_type": group_type, **row}
        rows.append(row)
    return pd.DataFrame(rows)


def precision_at_k(scored: pd.DataFrame, k_values: list[int]) -> pd.DataFrame:
    rows = []
    for candidate_type, g in scored.groupby("candidate_type", dropna=False):
        ordered = g.copy()
        ordered["_review_order"] = range(len(ordered))
        ordered = ordered.sort_values(["rank_num", "_review_order"], na_position="last")
        for k in k_values:
            subset = ordered.head(k)
            scores = n(subset["candidate_score"]).dropna()
            valid = int((scores >= 2).sum())
            rows.append(
                {
                    "candidate_type": "missing" if pd.isna(candidate_type) else str(candidate_type),
                    "k": k,
                    "evaluated_count": int(len(subset)),
                    "valid_candidate_count_score_ge_2": valid,
                    "precision_at_k": valid / len(subset) if len(subset) else "",
                }
            )
    return pd.DataFrame(rows)


def unet_summary(scored: pd.DataFrame) -> pd.DataFrame:
    text_cols = [c for c in ["title", "method_name", "technical_means", "problem_context", "solution_context", "candidate_type"] if c in scored.columns]
    mask = scored[text_cols].fillna("").astype(str).agg(" ".join, axis=1).str.contains(
        r"u-?net|unet|u net", case=False, regex=True
    )
    unet = scored[mask]
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


def write_md(
    all_df: pd.DataFrame,
    scored: pd.DataFrame,
    candidate_type: pd.DataFrame,
    method: pd.DataFrame,
    precision: pd.DataFrame,
    unet: pd.DataFrame,
    baseline_source: str,
) -> None:
    lines = [
        "# Final Human Review Summary",
        "",
        f"- total rows: {len(all_df)}",
        f"- evaluated rows: {len(scored)}",
        f"- unevaluated rows: {int((all_df['evaluation_status'] == 'unevaluated').sum())}",
        f"- baseline review source: `{baseline_source}`",
        "",
    ]
    if (all_df["evaluation_status"] == "unevaluated").any():
        lines.extend(
            [
                "追加ベースラインの `human_candidate_score` が空欄の行は、未評価としてスコア集計から除外しています。",
                "",
            ]
        )
    lines.extend(["## Candidate Type", "", md_table(candidate_type, list(candidate_type.columns)), ""])
    lines.extend(["## Method Comparison", "", md_table(method, list(method.columns)), ""])
    lines.extend(["## Precision@k", "", md_table(precision, list(precision.columns)), ""])
    lines.extend(["## U-Net Subset", "", md_table(unet, list(unet.columns)), ""])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    all_df, baseline_source = load_all()
    all_df.to_csv(OUT_ALL, index=False, encoding="utf-8-sig")

    scored = all_df[all_df["candidate_score"].notna()].copy()
    candidate_type = group_summary(scored, "candidate_type")
    method = pd.concat(
        [
            group_summary(scored, "proposed_or_baseline", "proposed_or_baseline"),
            group_summary(scored, "specific_method_flag", "specific_method_flag"),
            group_summary(scored, "general_term_flag", "general_term_flag"),
            group_summary(scored, "rank_bucket", "rank_bucket"),
        ],
        ignore_index=True,
    )
    precision = precision_at_k(scored, [5, 10, 20])
    unet = unet_summary(scored)

    candidate_type.to_csv(OUT_CANDIDATE_TYPE, index=False, encoding="utf-8-sig")
    method.to_csv(OUT_METHOD, index=False, encoding="utf-8-sig")
    precision.to_csv(OUT_PRECISION, index=False, encoding="utf-8-sig")
    unet.to_csv(OUT_UNET, index=False, encoding="utf-8-sig")
    write_md(all_df, scored, candidate_type, method, precision, unet, baseline_source)

    print(f"Total rows: {len(all_df)}")
    print(f"Evaluated rows: {len(scored)}")
    print(f"Unevaluated rows: {int((all_df['evaluation_status'] == 'unevaluated').sum())}")
    print(candidate_type.to_string(index=False))


if __name__ == "__main__":
    main()
