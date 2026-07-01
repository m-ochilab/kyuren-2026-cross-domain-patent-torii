"""
Script: 13_make_vector_ranking_report.py
Purpose: ベクトル化・類似度・technical_meansランキングの品質確認レポートを作成する。
Output:
  - data/processed/reports/vector_ranking_quality_report.md
  - data/processed/reports/vector_ranking_quality_report.xlsx
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


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


def nonempty(df: pd.DataFrame, col: str) -> tuple[int, float]:
    if col not in df.columns:
        return 0, 0.0
    n = int((df[col].fillna("").astype(str).str.strip() != "").sum())
    return n, n / len(df) if len(df) else 0.0


def split_methods(series: pd.Series) -> Counter:
    import re

    c = Counter()
    for value in series.fillna(""):
        for item in re.split(r"[;,、/|]+", str(value)):
            item = item.strip()
            if item:
                c[item] += 1
    return c


def method_top(df: pd.DataFrame, include_noise: bool) -> pd.DataFrame:
    if not include_noise and "analysis_include" in df.columns:
        df = df[pd.to_numeric(df["analysis_include"], errors="coerce").fillna(1).astype(int) == 1]
    c = split_methods(df.get("technical_means", pd.Series(dtype=str)))
    return pd.DataFrame([{"technical_means": k, "count": v} for k, v in c.most_common(20)])


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def first_existing(paths: list[Path]) -> pd.DataFrame:
    for path in paths:
        if path.exists():
            return pd.read_csv(path)
    return pd.DataFrame()


def suffixed(name: str, suffix: str) -> str:
    if not suffix:
        return name
    stem, ext = name.rsplit(".", 1)
    return f"{stem}_{suffix}.{ext}"


def md_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if df is None or len(df) == 0:
        return ""
    out = df.head(max_rows).copy() if max_rows else df.copy()
    out = out.fillna("")
    cols = list(out.columns)
    lines = [
        "| " + " | ".join(str(c) for c in cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in out.iterrows():
        values = [str(row[c]).replace("|", "/").replace("\n", " ") for c in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="vector/ranking品質レポート作成")
    parser.add_argument("--input-dir", default="data/processed")
    parser.add_argument("--embedding-dir", default=None)
    parser.add_argument("--similarity-dir", default=None)
    parser.add_argument("--ranking-dir", default=None)
    parser.add_argument("--output-dir", default="data/processed/reports")
    parser.add_argument("--output-suffix", default="")
    args = parser.parse_args()

    pipeline_dir = Path(__file__).parent.parent
    input_dir = resolve_dir(args.input_dir, pipeline_dir)
    embedding_dir = resolve_dir(args.embedding_dir or str(input_dir / "embeddings"), pipeline_dir)
    similarity_dir = resolve_dir(args.similarity_dir or str(input_dir / "similarity"), pipeline_dir)
    ranking_dir = resolve_dir(args.ranking_dir or str(input_dir / "ranking"), pipeline_dir)
    output_dir = resolve_output_dir(args.output_dir, pipeline_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    contexts = {d: pd.read_csv(input_dir / f"{d}_contexts.csv") for d in ["A0", "B0"]}

    input_rows = []
    for d, df in contexts.items():
        include_count = int(pd.to_numeric(df.get("analysis_include", pd.Series([1] * len(df))), errors="coerce").fillna(1).sum())
        row = {"domain": d, "records": len(df), "analysis_include": include_count}
        for col in ["problem_context", "solution_context", "technical_means"]:
            n, rate = nonempty(df, col)
            row[f"{col}_nonempty"] = n
            row[f"{col}_rate"] = rate
        input_rows.append(row)
    input_summary = pd.DataFrame(input_rows)

    vector_rows = []
    for d in ["A0", "B0"]:
        meta_path = embedding_dir / f"{d}_embedding_metadata.csv"
        meta_n = len(pd.read_csv(meta_path)) if meta_path.exists() else 0
        row = {"domain": d, "metadata_rows": meta_n}
        for emb_type in ["problem", "solution", "fulltext"]:
            path = embedding_dir / f"{d}_{emb_type}_embeddings.npy"
            if path.exists():
                emb = np.load(path, mmap_mode="r")
                row[f"{emb_type}_shape"] = "x".join(map(str, emb.shape))
            else:
                row[f"{emb_type}_shape"] = ""
        vector_rows.append(row)
    vector_summary = pd.DataFrame(vector_rows)

    field_similarity = first_existing([
        similarity_dir / suffixed("field_level_similarity_summary.csv", args.output_suffix),
        similarity_dir / "field_level_similarity_summary.csv",
    ])
    ranking = first_existing([
        ranking_dir / suffixed("method_gap_ranking_all.csv", args.output_suffix),
        ranking_dir / "method_gap_ranking_all.csv",
        ranking_dir / "method_gap_ranking_pre.csv",
    ])
    ranking_future = first_existing([
        ranking_dir / suffixed("method_gap_ranking_with_future.csv", args.output_suffix),
        ranking_dir / "method_gap_ranking_with_future.csv",
    ])
    unet = first_existing([
        ranking_dir / suffixed("unet_ranking_check.csv", args.output_suffix),
        ranking_dir / "unet_ranking_check.csv",
    ])
    specific = first_existing([
        ranking_dir / suffixed("method_gap_ranking_specific_methods.csv", args.output_suffix),
        ranking_dir / "method_gap_ranking_specific_methods.csv",
    ])

    top_methods_include = pd.concat(
        [method_top(df.assign(domain=d), include_noise=False).assign(domain=d) for d, df in contexts.items()],
        ignore_index=True,
    )
    top_methods_all = pd.concat(
        [method_top(df.assign(domain=d), include_noise=True).assign(domain=d) for d, df in contexts.items()],
        ignore_index=True,
    )
    noise_diff = pd.concat([
        top_methods_include.assign(scope="exclude_noise"),
        top_methods_all.assign(scope="include_noise"),
    ], ignore_index=True)

    md_lines = [
        "# Vector Ranking Quality Report",
        "",
        "このレポートは、技術導入可能性を証明するものではなく、専門家が確認すべきクロスドメイン技術候補をランキング化するための品質確認である。",
        "",
        "## 1. Input And Context Coverage",
        "",
        md_table(input_summary),
        "",
        "## 2. Vectorization",
        "",
        md_table(vector_summary),
        "",
        "## 3. Field-Level Similarity",
        "",
        md_table(field_similarity) if len(field_similarity) else "field-level similarity file not found.",
        "",
        "## 4. technical_means Top 20",
        "",
        md_table(top_methods_include) if len(top_methods_include) else "No technical_means.",
        "",
        "## 5. GapScore Ranking Top 20",
        "",
        md_table(ranking, max_rows=20) if len(ranking) else "Ranking file not found.",
        "",
        "## 6. U-Net Ranking Check",
        "",
        md_table(unet) if len(unet) else "No U-Net related row found in ranking.",
        "",
        "## 7. Specific Method Ranking",
        "",
        md_table(specific, max_rows=20) if len(specific) else "Specific method ranking file not found.",
        "",
        "## 8. Noise Included vs Excluded",
        "",
        md_table(noise_diff) if len(noise_diff) else "No comparison.",
        "",
    ]

    md_out = output_dir / suffixed("vector_ranking_quality_report.md", args.output_suffix)
    md_out.write_text("\n".join(md_lines), encoding="utf-8")

    xlsx_out = output_dir / suffixed("vector_ranking_quality_report.xlsx", args.output_suffix)
    with pd.ExcelWriter(xlsx_out, engine="openpyxl") as writer:
        input_summary.to_excel(writer, sheet_name="input_context", index=False)
        vector_summary.to_excel(writer, sheet_name="vectorization", index=False)
        field_similarity.to_excel(writer, sheet_name="field_similarity", index=False)
        top_methods_include.to_excel(writer, sheet_name="means_top20_excl_noise", index=False)
        top_methods_all.to_excel(writer, sheet_name="means_top20_incl_noise", index=False)
        ranking.head(20).to_excel(writer, sheet_name="gapscore_top20", index=False)
        specific.head(50).to_excel(writer, sheet_name="specific_methods", index=False)
        ranking_future.head(50).to_excel(writer, sheet_name="ranking_with_future", index=False)
        unet.to_excel(writer, sheet_name="unet_check", index=False)
        noise_diff.to_excel(writer, sheet_name="noise_diff", index=False)

    print(f"saved: {md_out}")
    print(f"saved: {xlsx_out}")


if __name__ == "__main__":
    main()
