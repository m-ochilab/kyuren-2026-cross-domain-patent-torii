#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLUSTER_DIR = PROJECT_ROOT / "pipeline/outputs/heterogeneous_clusters"

LABEL_ORDER = {"×": 0, "△": 1, "○": 2, "◎": 3}
LABEL_BY_SCORE = {v: k for k, v in LABEL_ORDER.items()}

DAILY_RE = re.compile(
    r"launder|laundry|clothing|cloth|textile|garment|hair|dish|kitchen|food processing|"
    r"detergent granule|powder detergent|fabric|fiber product|shampoo|cosmetic|"
    r"洗濯|衣料|衣類|繊維|毛髪|食器|台所|食品|洗剤粒子|粉末洗剤|シャンプー",
    re.IGNORECASE,
)
PRIORITY_RE = re.compile(
    r"glass substrate|hard disk substrate|plastic coating|screen printing plate|object surface|"
    r"target surface|hard surface|surface of an object|"
    r"ガラス.*基板|ハードディスク.*基板|プラスチック.*塗膜|スクリーン印刷|対象表面|物体表面",
    re.IGNORECASE,
)
GENERAL_CLEANING_RE = re.compile(
    r"cleaning|cleaner|detergent|washing|remov|rinse|residue|surface roughness|corrosion|"
    r"洗浄|清洗|清潔|洗剤|除去|リンス|残渣|残留|腐食|表面粗さ",
    re.IGNORECASE,
)

CLUSTER_PROBLEM_PATTERNS = {
    "silicon_wafer_cleaning": r"silicon wafer|wafer|rinse|particle|semiconductor.*surface|晶片|ウェーハ|ウエハ|粒子",
    "semiconductor_substrate_cleaning": r"semiconductor substrate|semiconductor device substrate|substrate cleaning|semiconductor|基板|半導体",
    "cmp_polishing_post_cleaning": r"\bCMP\b|post[- ]?CMP|chemical mechanical polishing|slurry|polishing residue|ceria|polishing|研磨|スラリー|酸化セリウム|残渣",
    "flux_electronic_component_cleaning": r"flux|solder|electronic part|mounting|printed circuit|フラックス|はんだ|半田|電子部品|実装|プリント回路",
    "photoresist_resin_mask_removal": r"photoresist|resist|resin mask|copper corrosion|mask|copper|剥離|樹脂マスク|レジスト|銅|腐食",
    "adhesive_cleaning": r"adhesive|bonding|temporary fixing|resin residue|接着|仮固定|樹脂残渣|粘着",
    "circuit_board_cleaning": r"circuit board|printed wiring board|\bPCB\b|solder|flux residue|回路基板|プリント配線|はんだ|フラックス残渣",
}

CLUSTER_SOLUTION_PATTERNS = {
    "silicon_wafer_cleaning": r"cleaning composition|cleaning method|rinse|particle removal|surfactant|polymer|洗浄剤|リンス|粒子除去|界面活性剤|高分子",
    "semiconductor_substrate_cleaning": r"substrate cleaning|cleaning composition|detergent composition|polymer|surfactant|基板.*洗浄|洗浄剤|組成物",
    "cmp_polishing_post_cleaning": r"cleaning composition|detergent composition|residue removal|particle removal|polishing|slurry|洗浄剤|残渣除去|粒子除去|研磨",
    "flux_electronic_component_cleaning": r"flux.*remov|solder.*clean|cleaning composition|solvent|amine|フラックス.*除去|はんだ.*洗浄|溶剤|アミン",
    "photoresist_resin_mask_removal": r"resin mask.*remov|resist.*remov|cleaning composition|corrosion suppress|剥離|除去|腐食.*抑制|洗浄剤",
    "adhesive_cleaning": r"adhesive.*remov|cleaning composition|solvent|glycol ether|hydrocarbon|接着剤.*除去|溶剤|洗浄剤",
    "circuit_board_cleaning": r"circuit board.*clean|printed wiring.*clean|flux.*remov|solder|cleaning method|回路基板.*洗浄|プリント配線.*洗浄|フラックス.*除去",
}


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.lower() == "nan":
        return ""
    return re.sub(r"\s+", " ", text).strip()


def label_from_score(score: int) -> str:
    return LABEL_BY_SCORE[max(0, min(3, score))]


def strongest(labels: list[str]) -> str:
    return max(labels, key=lambda label: LABEL_ORDER.get(label, 0)) if labels else "×"


def weaken(label: str, steps: int = 1) -> str:
    return label_from_score(LABEL_ORDER.get(label, 0) - steps)


def score_candidate_for_cluster(cluster: str, text: str) -> tuple[str, str, str, str]:
    problem_re = re.compile(CLUSTER_PROBLEM_PATTERNS[cluster], re.IGNORECASE)
    solution_re = re.compile(CLUSTER_SOLUTION_PATTERNS[cluster], re.IGNORECASE)

    is_daily = bool(DAILY_RE.search(text))
    is_priority = bool(PRIORITY_RE.search(text))
    has_general_cleaning = bool(GENERAL_CLEANING_RE.search(text))
    has_problem = bool(problem_re.search(text))
    has_solution = bool(solution_re.search(text))

    problem_score = 0
    solution_score = 0

    if has_problem:
        problem_score = 3 if not is_daily else 1
    elif is_priority and has_general_cleaning:
        problem_score = 2
    elif has_general_cleaning:
        problem_score = 1

    if has_solution:
        solution_score = 3 if not is_daily else 1
    elif is_priority and has_general_cleaning:
        solution_score = 2
    elif has_general_cleaning:
        solution_score = 1

    if is_daily and not is_priority:
        problem_score = min(problem_score, 1)
        solution_score = min(solution_score, 1)

    if cluster == "silicon_wafer_cleaning" and is_priority and re.search(r"glass substrate|hard disk substrate", text, re.I):
        problem_score = max(problem_score, 2)
        solution_score = max(solution_score, 2)

    if cluster in {"adhesive_cleaning", "circuit_board_cleaning"} and re.search(r"object surface|target surface|plastic coating", text, re.I):
        problem_score = max(problem_score, 2)
        solution_score = max(solution_score, 2)

    problem_label = label_from_score(problem_score)
    solution_label = label_from_score(solution_score)
    overall_score = round((problem_score + solution_score) / 2)
    if problem_score == 0 or solution_score == 0:
        overall_score = min(overall_score, 1)
    overall_label = label_from_score(overall_score)

    reasons = []
    if is_daily and not is_priority:
        reasons.append("日用品・衣料/洗剤寄りで半導体用途への接続が弱い")
    if is_priority:
        reasons.append("優先確認対象の基材/表面洗浄候補を含む")
    if has_problem:
        reasons.append("対象クラスタの用途語・課題語が本文に出る")
    elif has_general_cleaning:
        reasons.append("一般的な洗浄課題はあるがクラスタ固有性は限定的")
    if not reasons:
        reasons.append("クラスタ用途との直接接点が本文から弱い")
    note = "、".join(reasons) + "。"
    return problem_label, solution_label, overall_label, note


def aggregate_manual_rows(manual: pd.DataFrame, c1_pre: pd.DataFrame) -> pd.DataFrame:
    c1_unique = c1_pre.drop_duplicates("family_id_simple").copy()
    c1_cols = [
        "family_id_simple",
        "abstract",
        "claims",
        "full_text",
        "title_abstract_text",
    ]
    c1_cols = [col for col in c1_cols if col in c1_unique.columns]
    enriched = manual.merge(c1_unique[c1_cols], on="family_id_simple", how="left")

    rows = []
    for family_id, group in enriched.groupby("family_id_simple", sort=False):
        group = group.copy()
        group["rank_int"] = pd.to_numeric(group["rank"], errors="coerce").fillna(9999).astype(int)
        best = group.sort_values(["rank_int", "cluster"]).iloc[0]
        cluster_labels = []
        solution_labels = []
        overall_labels = []
        notes = []

        text = " ".join(
            clean(best.get(col, ""))
            for col in [
                "title",
                "abstract",
                "claims",
                "problem_context",
                "solution_context",
                "full_text",
            ]
        )
        for _, row in group.sort_values(["cluster", "rank_int"]).iterrows():
            p, s, o, note = score_candidate_for_cluster(clean(row["cluster"]), text)
            cluster_labels.append(p)
            solution_labels.append(s)
            overall_labels.append(o)
            notes.append(f"{row['cluster']}: {note}")

        appeared = group.sort_values(["cluster", "rank_int"])
        rows.append(
            {
                "primary_cluster": clean(best["cluster"]),
                "appeared_clusters": "; ".join(appeared["cluster"].tolist()),
                "cluster_ranks": "; ".join(f"{r.cluster}:{r.rank}" for r in appeared.itertuples(index=False)),
                "best_rank": str(int(best["rank_int"])),
                "family_id_simple": family_id,
                "family_first_date": clean(best["family_first_date"]),
                "title": clean(best["title"]),
                "problem_context": clean(best["problem_context"]),
                "solution_context": clean(best["solution_context"]),
                "technical_means": clean(best["technical_means"]),
                "matched_s1_representative_family": "; ".join(dict.fromkeys(appeared["matched_s1_representative_family"].tolist())),
                "matched_s1_title": "; ".join(dict.fromkeys(appeared["matched_s1_title"].tolist())),
                "review_problem_match": strongest(cluster_labels),
                "review_solution_match": strongest(solution_labels),
                "review_overall_label": strongest(overall_labels),
                "review_note": " ".join(dict.fromkeys(notes)),
            }
        )

    out = pd.DataFrame(rows)
    out = out.sort_values(
        ["review_overall_label", "best_rank", "family_first_date", "family_id_simple"],
        key=lambda s: s.map(LABEL_ORDER) if s.name == "review_overall_label" else s,
        ascending=[False, True, True, True],
    ).reset_index(drop=True)
    return out


def build_summary(filled: pd.DataFrame, original_rows: int) -> pd.DataFrame:
    rows = [
        {"metric": "manual_review_top20_rows_before_dedup", "value": original_rows},
        {"metric": "manual_review_unique_family_rows", "value": len(filled)},
    ]
    for label in ["◎", "○", "△", "×"]:
        rows.append(
            {
                "metric": f"overall_label_{label}_count",
                "value": int((filled["review_overall_label"] == label).sum()),
            }
        )
    cluster_rows = []
    for cluster, group in filled.assign(primary_cluster=filled["primary_cluster"]).groupby("primary_cluster"):
        cluster_rows.append(
            {
                "metric": f"primary_cluster_{cluster}_unique_family_count",
                "value": len(group),
            }
        )
    return pd.DataFrame(rows + cluster_rows)


def main() -> int:
    manual_path = CLUSTER_DIR / "C1_candidate_manual_review_by_cluster.csv"
    c1_path = CLUSTER_DIR / "C1_pre_for_each_cluster.csv"
    manual = pd.read_csv(manual_path, dtype=str, keep_default_na=False)
    c1_pre = pd.read_csv(c1_path, dtype=str, keep_default_na=False)

    filled = aggregate_manual_rows(manual, c1_pre)
    summary = build_summary(filled, len(manual))

    filled.to_csv(CLUSTER_DIR / "C1_candidate_manual_review_filled_draft.csv", index=False, encoding="utf-8")
    summary.to_csv(CLUSTER_DIR / "heterogeneous_manual_review_summary.csv", index=False, encoding="utf-8")

    print(filled.head(20).to_string(max_colwidth=100, index=False))
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
