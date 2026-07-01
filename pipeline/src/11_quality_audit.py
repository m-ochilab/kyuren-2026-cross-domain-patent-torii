"""
Script: 11_quality_audit.py
Purpose: 本番分析前の品質確認表と人手確認サンプルを作成する。
Input:
  - data/processed/{domain}_publication_level.csv
  - data/processed/{domain}_contexts.csv
Output:
  - outputs/tables/quality_audit_summary.csv
  - outputs/tables/quality_audit_report.md
  - outputs/review_samples/{domain}_manual_review_sample.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml


DOMAINS = ["A0", "B0"]
TEXT_COLUMNS = ["title", "abstract", "claims"]
CONTEXT_COLUMNS = ["problem_context", "solution_context", "technical_means"]
UNET_COLUMNS = [
    "is_unet_title_abstract",
    "is_unet_claims",
    "is_unet_full_text",
    "is_unet_final",
]
REVIEW_COLUMNS = [
    "publication_number",
    "family_id",
    "year",
    "title",
    "abstract",
    "problem_context",
    "solution_context",
    "technical_means",
    "target_object",
    "application_field",
    "domain_noise_flag",
    "domain_noise_reason",
    "analysis_include",
    "is_unet_title_abstract",
    "is_unet_claims",
    "is_unet_full_text",
    "is_unet_final",
]


def nonempty_rate(df: pd.DataFrame, col: str) -> tuple[int, float]:
    if col not in df.columns:
        return 0, 0.0
    n = int((df[col].fillna("").astype(str).str.strip() != "").sum())
    return n, n / len(df) if len(df) else 0.0


def safe_sum(df: pd.DataFrame, col: str) -> int:
    if col not in df.columns:
        return 0
    return int(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def sample_review_rows(df: pd.DataFrame, sample_size: int, seed: int) -> pd.DataFrame:
    parts = []

    if "domain_noise_flag" in df.columns:
        noise = df[df["domain_noise_flag"] == 1]
        if len(noise):
            parts.append(noise.sample(min(max(sample_size // 3, 5), len(noise)), random_state=seed))

    if "technical_means" in df.columns:
        empty_means = df[df["technical_means"].fillna("").astype(str).str.strip() == ""]
        if len(empty_means):
            parts.append(empty_means.sample(min(max(sample_size // 5, 3), len(empty_means)), random_state=seed + 1))

    if "is_unet_full_text" in df.columns:
        unet = df[pd.to_numeric(df["is_unet_full_text"], errors="coerce").fillna(0) == 1]
        if len(unet):
            parts.append(unet.sample(min(max(sample_size // 5, 3), len(unet)), random_state=seed + 2))

    current = pd.concat(parts, ignore_index=False).drop_duplicates() if parts else pd.DataFrame()
    remaining_n = max(sample_size - len(current), 0)
    pool = df.drop(index=current.index, errors="ignore")
    if remaining_n and len(pool):
        current = pd.concat(
            [current, pool.sample(min(remaining_n, len(pool)), random_state=seed + 3)],
            ignore_index=False,
        )

    out = current.head(sample_size).copy()
    for col in REVIEW_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    out = out[REVIEW_COLUMNS]
    out.insert(0, "review_id", range(1, len(out) + 1))
    out["review_technical_means_valid"] = ""
    out["review_domain_noise_valid"] = ""
    out["review_problem_solution_split_valid"] = ""
    out["review_notes"] = ""
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="品質確認表と人手確認サンプルを作成")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--review-sample-size", type=int, default=50)
    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = script_dir / config_path
    with config_path.open(encoding="utf-8") as fp:
        cfg = yaml.safe_load(fp)

    processed_dir = script_dir / cfg["data"]["processed_dir"]
    tables_dir = script_dir / cfg["data"]["output_dir"] / "tables"
    review_dir = script_dir / cfg["data"]["output_dir"] / "review_samples"
    tables_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    report_lines = [
        "# Quality Audit Summary",
        "",
        "## Adoption Rules",
        "",
        "- `is_unet_final = is_unet_title_abstract` in the main analysis.",
        "- `is_unet_claims` and `is_unet_full_text` are kept for supplementary analysis.",
        "- Rows with `domain_noise_flag = 1` are review targets before final exclusion.",
        "- Family-level U-Net flags are aggregated by max: if any publication in a family is U-Net, the family flag is 1.",
        "",
    ]

    seed = int(cfg.get("sample", {}).get("seed", 42))

    for domain in DOMAINS:
        pub_path = processed_dir / f"{domain}_publication_level.csv"
        ctx_path = processed_dir / f"{domain}_contexts.csv"
        if not pub_path.exists() or not ctx_path.exists():
            continue

        pub = pd.read_csv(pub_path)
        ctx = pd.read_csv(ctx_path)

        rows.append({"domain": domain, "section": "input", "metric": "records", "count": len(pub), "rate": 1.0})

        for col in TEXT_COLUMNS:
            count, rate = nonempty_rate(pub, col)
            rows.append({"domain": domain, "section": "text", "metric": f"{col}_nonempty", "count": count, "rate": rate})

        for col in CONTEXT_COLUMNS:
            count, rate = nonempty_rate(ctx, col)
            rows.append({"domain": domain, "section": "context", "metric": f"{col}_nonempty", "count": count, "rate": rate})

        for col in UNET_COLUMNS:
            rows.append({"domain": domain, "section": "unet", "metric": col, "count": safe_sum(pub, col), "rate": safe_sum(pub, col) / len(pub)})

        for col in ["domain_noise_flag", "analysis_include"]:
            rows.append({"domain": domain, "section": "domain_qc", "metric": col, "count": safe_sum(ctx, col), "rate": safe_sum(ctx, col) / len(ctx)})

        review = sample_review_rows(ctx, args.review_sample_size, seed)
        review_out = review_dir / f"{domain}_manual_review_sample.csv"
        review.to_csv(review_out, index=False, encoding="utf-8")

        report_lines.extend([
            f"## {domain}",
            "",
            f"- input records: {len(pub)}",
            f"- review sample: `{review_out.relative_to(script_dir)}` ({len(review)} rows)",
            "",
        ])

    summary = pd.DataFrame(rows)
    summary["rate"] = summary["rate"].round(6)
    summary_out = tables_dir / "quality_audit_summary.csv"
    summary.to_csv(summary_out, index=False, encoding="utf-8")

    report_lines.extend([
        "## Output Files",
        "",
        f"- `{summary_out.relative_to(script_dir)}`",
        "- `outputs/review_samples/A0_manual_review_sample.csv`",
        "- `outputs/review_samples/B0_manual_review_sample.csv`",
        "",
    ])
    report_out = tables_dir / "quality_audit_report.md"
    report_out.write_text("\n".join(report_lines), encoding="utf-8")

    print(summary.to_string(index=False))
    print(f"\nSaved: {summary_out}")
    print(f"Saved: {report_out}")


if __name__ == "__main__":
    main()
