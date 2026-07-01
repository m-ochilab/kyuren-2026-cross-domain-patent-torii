"""
Script: 12_rank_method_gaps.py
Purpose: technical_meansに基づくA0高出現/B0低出現の手法ギャップランキングを作成する。
Output:
  - data/processed/ranking/method_gap_ranking_all.csv
  - data/processed/ranking/method_gap_ranking_specific_methods.csv
  - data/processed/ranking/method_future_growth_evaluation.csv
  - data/processed/ranking/method_gap_ranking_with_future.csv
  - data/processed/ranking/unet_ranking_check.csv
"""

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


SPLIT_RE = re.compile(r"[;,、/|]+")
UNET_RE = re.compile(r"u[\s-]?net|nnu[\s-]?net", re.IGNORECASE)
SPECIFIC_METHODS = {
    "u-net",
    "cnn",
    "svm",
    "random forest",
    "k-means",
    "autoencoder",
    "gan",
    "transformer",
    "attention",
    "encoder-decoder",
    "yolo",
    "domain adaptation",
}


def resolve_dir(path: str, pipeline_dir: Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = pipeline_dir / p
    if p.exists():
        return p
    if "processed" in p.parts:
        parts = p.parts[p.parts.index("processed") + 1:]
        alt = pipeline_dir / "data" / "processed" / Path(*parts)
        if alt.exists():
            return alt
    return p


def resolve_output_dir(path: str, pipeline_dir: Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    if p.parts and p.parts[0] == "processed":
        return pipeline_dir / "data" / "processed" / Path(*p.parts[1:])
    return pipeline_dir / p


def method_key(value: str) -> str:
    v = re.sub(r"\s+", " ", str(value).strip()).lower()
    v = v.replace("u net", "u-net").replace("unet", "u-net")
    v = v.replace("encoder decoder", "encoder-decoder")
    if UNET_RE.search(v):
        return "u-net"
    if v in {"convolutional neural network", "畳み込みニューラルネットワーク"}:
        return "cnn"
    if v == "support vector machine":
        return "svm"
    if v in {"auto-encoder"}:
        return "autoencoder"
    return v


def display_name(key: str, display_counter: Counter) -> str:
    if UNET_RE.search(key):
        return "U-Net"
    canonical = {
        "cnn": "CNN",
        "svm": "SVM",
        "random forest": "random forest",
        "k-means": "k-means",
        "autoencoder": "Autoencoder",
        "gan": "GAN",
        "transformer": "Transformer",
        "attention": "Attention",
        "encoder-decoder": "encoder-decoder",
        "yolo": "YOLO",
        "domain adaptation": "Domain Adaptation",
    }
    if key in canonical:
        return canonical[key]
    if display_counter:
        return display_counter.most_common(1)[0][0]
    return key


def explode_methods(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for idx, row in df.iterrows():
        text = row.get("technical_means", "")
        if pd.isna(text) or not str(text).strip():
            continue
        for raw in SPLIT_RE.split(str(text)):
            raw = raw.strip()
            if not raw:
                continue
            key = method_key(raw)
            if not key or key in {"method", "system", "apparatus", "device"}:
                continue
            rows.append({
                "row_idx": idx,
                "method": key,
                "method_display_raw": raw,
                "year": row.get("year", row.get("filing_year", "")),
            })
    return pd.DataFrame(rows)


def filter_rows(df: pd.DataFrame, include_noise: bool) -> pd.DataFrame:
    out = df.copy()
    if not include_noise and "analysis_include" in out.columns:
        out = out[pd.to_numeric(out["analysis_include"], errors="coerce").fillna(1).astype(int) == 1]
    return out


def period_df(df: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    year = pd.to_numeric(df["year"], errors="coerce")
    return df[(year >= start) & (year <= end)]


def method_counts(exploded: pd.DataFrame) -> tuple[Counter, dict[str, Counter]]:
    counts = Counter(exploded["method"]) if len(exploded) else Counter()
    displays: dict[str, Counter] = defaultdict(Counter)
    for _, row in exploded.iterrows():
        displays[row["method"]][row["method_display_raw"]] += 1
    return counts, displays


def read_problem_similarity(similarity_dir: Path) -> float:
    path = similarity_dir / "field_level_similarity_summary.csv"
    if not path.exists():
        return 1.0
    df = pd.read_csv(path)
    for col in ["problem_field_similarity", "problem_field_similarity"]:
        if col in df.columns and len(df):
            return float(df[col].iloc[0])
    return 1.0


def suffixed(name: str, suffix: str) -> str:
    if not suffix:
        return name
    stem, ext = name.rsplit(".", 1)
    return f"{stem}_{suffix}.{ext}"


def main() -> None:
    parser = argparse.ArgumentParser(description="technical_meansの手法ギャップランキング")
    parser.add_argument("--input-dir", default="data/processed")
    parser.add_argument("--similarity-dir", default="data/processed/similarity")
    parser.add_argument("--output-dir", default="data/processed/ranking")
    parser.add_argument("--include-noise", action="store_true")
    parser.add_argument("--pre-start", type=int, default=2015)
    parser.add_argument("--pre-end", type=int, default=2018)
    parser.add_argument("--future-start", type=int, default=2019)
    parser.add_argument("--future-end", type=int, default=2024)
    parser.add_argument("--output-suffix", default="")
    args = parser.parse_args()

    pipeline_dir = Path(__file__).parent.parent
    input_dir = resolve_dir(args.input_dir, pipeline_dir)
    similarity_dir = resolve_dir(args.similarity_dir, pipeline_dir)
    output_dir = resolve_output_dir(args.output_dir, pipeline_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    a = filter_rows(pd.read_csv(input_dir / "A0_contexts.csv"), args.include_noise)
    b = filter_rows(pd.read_csv(input_dir / "B0_contexts.csv"), args.include_noise)
    problem_sim = read_problem_similarity(similarity_dir)

    a_pre = period_df(a, args.pre_start, args.pre_end)
    b_pre = period_df(b, args.pre_start, args.pre_end)
    b_future = period_df(b, args.future_start, args.future_end)

    a_pre_methods = explode_methods(a_pre)
    b_pre_methods = explode_methods(b_pre)
    b_future_methods = explode_methods(b_future)

    a_counts, a_displays = method_counts(a_pre_methods)
    b_counts, b_displays = method_counts(b_pre_methods)
    f_counts, f_displays = method_counts(b_future_methods)
    all_methods = sorted(set(a_counts) | set(b_counts) | set(f_counts) | SPECIFIC_METHODS)

    ranking_rows = []
    future_rows = []
    combined_rows = []
    for method in all_methods:
        a_count = a_counts.get(method, 0)
        b_count = b_counts.get(method, 0)
        f_count = f_counts.get(method, 0)
        a_rate = a_count / len(a_pre) if len(a_pre) else 0.0
        b_rate = b_count / len(b_pre) if len(b_pre) else 0.0
        f_rate = f_count / len(b_future) if len(b_future) else 0.0
        gap_rate = a_rate - b_rate
        positive_gap = max(gap_rate, 0.0)
        gap_score_old = a_rate * (1.0 - b_rate) * problem_sim
        gap_score_v2 = a_rate * positive_gap * problem_sim
        disp_counter = a_displays.get(method, Counter()) + b_displays.get(method, Counter()) + f_displays.get(method, Counter())
        disp = display_name(method, disp_counter)
        growth = f_rate - b_rate

        ranking_rows.append({
            "method": method,
            "method_display": disp,
            "A_pre_count": a_count,
            "A_pre_total": len(a_pre),
            "A_pre_rate": a_rate,
            "B_pre_count": b_count,
            "B_pre_total": len(b_pre),
            "B_pre_rate": b_rate,
            "gap_rate": gap_rate,
            "positive_gap": positive_gap,
            "problem_field_similarity": problem_sim,
            "gap_score_old": gap_score_old,
            "gap_score_v2": gap_score_v2,
        })
        future_rows.append({
            "method": method,
            "B_future_count": f_count,
            "B_future_total": len(b_future),
            "B_future_rate": f_rate,
            "B_growth_rate": growth,
        })
        combined_rows.append({
            "method": method,
            "method_display": disp,
            "A_pre_rate": a_rate,
            "B_pre_rate": b_rate,
            "gap_rate": gap_rate,
            "positive_gap": positive_gap,
            "gap_score_old": gap_score_old,
            "gap_score_v2": gap_score_v2,
            "B_future_rate": f_rate,
            "B_growth_rate": growth,
            "future_observed_flag": int(f_count > 0),
        })

    ranking_all_candidates = pd.DataFrame(ranking_rows)
    ranking = (
        ranking_all_candidates[ranking_all_candidates["positive_gap"] > 0]
        .sort_values(["gap_score_v2", "positive_gap", "A_pre_count"], ascending=False)
        .reset_index(drop=True)
    )
    ranking.insert(0, "rank", range(1, len(ranking) + 1))
    specific = (
        ranking_all_candidates[ranking_all_candidates["method"].isin(SPECIFIC_METHODS)]
        .merge(ranking[["method", "rank"]], on="method", how="left")
        .sort_values(["gap_score_v2", "positive_gap", "A_pre_count"], ascending=False)
        .reset_index(drop=True)
    )
    if len(specific):
        specific.insert(0, "specific_rank", range(1, len(specific) + 1))
    future = pd.DataFrame(future_rows)
    combined = pd.DataFrame(combined_rows)
    combined = combined[combined["method"].isin(set(ranking["method"]))].merge(ranking[["method", "rank"]], on="method", how="left")
    combined = combined.sort_values("rank").reset_index(drop=True)

    ranking.to_csv(output_dir / suffixed("method_gap_ranking_all.csv", args.output_suffix), index=False, encoding="utf-8")
    ranking.to_csv(output_dir / suffixed("method_gap_ranking_pre.csv", args.output_suffix), index=False, encoding="utf-8")
    specific.to_csv(output_dir / suffixed("method_gap_ranking_specific_methods.csv", args.output_suffix), index=False, encoding="utf-8")
    future.to_csv(output_dir / suffixed("method_future_growth_evaluation.csv", args.output_suffix), index=False, encoding="utf-8")
    combined.to_csv(output_dir / suffixed("method_gap_ranking_with_future.csv", args.output_suffix), index=False, encoding="utf-8")

    unet = combined[combined["method"].str.contains(UNET_RE, na=False)].copy()
    unet = unet.merge(ranking[["method", "A_pre_count", "B_pre_count", "problem_field_similarity"]], on="method", how="left")
    unet.to_csv(output_dir / suffixed("unet_ranking_check.csv", args.output_suffix), index=False, encoding="utf-8")
    print(f"saved ranking files: {output_dir}")
    if len(unet):
        print("U-Net ranking check:")
        print(unet.to_string(index=False))
    else:
        print("U-Net ranking check: no U-Net related technical_means found")


if __name__ == "__main__":
    main()
