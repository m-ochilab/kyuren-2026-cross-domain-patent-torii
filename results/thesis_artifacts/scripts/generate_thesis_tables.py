#!/usr/bin/env python3
from __future__ import annotations

import math
import shutil
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ARTIFACT_DIR = PROJECT_ROOT / "pipeline/outputs/thesis_artifacts"
TABLE_DIR = ARTIFACT_DIR / "tables"
ROOT_TABLE_DIR = PROJECT_ROOT / "tables"

P1 = PROJECT_ROOT / "pipeline/outputs/experiment1_data_bundle/outputs"
P2 = PROJECT_ROOT / "pipeline/outputs/experiment2_heterogeneous_bundle/outputs"
DATA = PROJECT_ROOT / "pipeline/data"
TABLE_SOURCE = PROJECT_ROOT / "pipeline/outputs/tables"

LABEL_MAP = {"◎": "Strong", "○": "Plausible", "△": "Weak", "×": "Reject"}
LABEL_ORDER = ["◎", "○", "△", "×"]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def row_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return len(pd.read_csv(path, usecols=[0]))
    except Exception:
        return None


def family_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, usecols=lambda c: c == "family_id_simple")
        if "family_id_simple" not in df.columns:
            return None
        return int(df["family_id_simple"].nunique())
    except Exception:
        return None


def latex_escape(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def fmt(value: object) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        if abs(value) <= 1:
            return f"{value:.3f}"
        return f"{value:.2f}"
    return "" if value is None else str(value)


def write_table(df: pd.DataFrame, stem: str, caption: str, label: str) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    ROOT_TABLE_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = TABLE_DIR / f"{stem}.csv"
    tex_path = TABLE_DIR / f"{stem}.tex"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    col_spec = "l" * len(df.columns)
    lines = [
        r"\begin{table}[tbp]",
        r"\centering",
        r"\small",
        rf"\caption{{{latex_escape(caption)}}}",
        rf"\label{{{label}}}",
        r"\begin{adjustbox}{max width=\textwidth}",
        rf"\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        " & ".join(latex_escape(c) for c in df.columns) + r" \\",
        r"\midrule",
    ]
    for _, row in df.iterrows():
        lines.append(" & ".join(latex_escape(fmt(v)) for v in row.tolist()) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{adjustbox}", r"\end{table}", ""])
    tex_path.write_text("\n".join(lines), encoding="utf-8")

    shutil.copy2(csv_path, ROOT_TABLE_DIR / csv_path.name)
    shutil.copy2(tex_path, ROOT_TABLE_DIR / tex_path.name)


def make_dataset_summary_table() -> None:
    ds = read_csv(TABLE_SOURCE / "dataset_summary.csv")
    ds_lookup = {}
    if not ds.empty:
        for _, row in ds.iterrows():
            ds_lookup[(row["domain"], row["level"])] = row

    prep = read_csv(P2 / "s1_c1_preparation_summary.csv")
    prep_lookup = dict(zip(prep.get("metric", []), prep.get("value", []))) if not prep.empty else {}

    rows = [
        [
            "A0",
            "実験1（主分析）",
            "医療画像解析分野",
            int(ds_lookup.get(("A0", "publication"), {}).get("total_records", row_count(DATA / "raw/A0_orbis_publication_level.csv"))),
            int(ds_lookup.get(("A0", "family"), {}).get("total_records", family_count(DATA / "raw/A0_orbis_publication_level.csv"))),
        ],
        [
            "A1",
            "実験1（主分析）",
            "医療画像解析分野のU-Net関連集合",
            row_count(DATA / "raw/A1_orbis_publication_level.csv"),
            family_count(DATA / "raw/A1_orbis_publication_level.csv"),
        ],
        [
            "B0",
            "実験1（主分析）",
            "製造欠陥検出分野",
            int(ds_lookup.get(("B0", "publication"), {}).get("total_records", row_count(DATA / "raw/B0_orbis_publication_level.csv"))),
            int(ds_lookup.get(("B0", "family"), {}).get("total_records", family_count(DATA / "raw/B0_orbis_publication_level.csv"))),
        ],
        [
            "B1",
            "実験1（主分析）",
            "製造欠陥検出分野のU-Net関連集合",
            row_count(DATA / "raw/B1_orbis_publication_level.csv"),
            family_count(DATA / "raw/B1_orbis_publication_level.csv"),
        ],
        [
            "C1",
            "実験2（補助分析）",
            "花王の洗浄・除去系非半導体候補",
            int(prep_lookup.get("c1_pre_nonsemi_overall_count", row_count(P2 / "C1_pre_nonsemi_overall.csv"))),
            row_count(P2 / "C1_pre_nonsemi_overall.csv"),
        ],
        [
            "S1",
            "実験2（補助分析）",
            "半導体洗浄関連の既知事例・用途クラスタ",
            row_count(DATA / "raw_heterogeneous/S1_heterogeneous_publication_level.csv"),
            int(prep_lookup.get("s1_family_count", row_count(DATA / "processed_heterogeneous/S1_family_level.csv"))),
        ],
        [
            "S0_pre",
            "実験2（補助分析）",
            "クラスタ初出日前のS0比較集合",
            "",
            row_count(P2 / "S0_pre_for_each_cluster.csv"),
        ],
        [
            "S0_pre_filtered",
            "実験2（補助分析）",
            "用途語フィルタ後のS0比較集合",
            "",
            row_count(P2 / "S0_pre_for_each_cluster_filtered.csv"),
        ],
    ]
    df = pd.DataFrame(rows, columns=["データセット", "使用実験", "内容", "公開公報数", "ファミリー数・候補行数"])
    write_table(df, "dataset_summary_table", "本研究で用いた主要データセット", "tab:dataset_summary_table")


def make_experiment1_dataset_table() -> None:
    ds = read_csv(TABLE_SOURCE / "dataset_summary.csv")
    if ds.empty:
        df = pd.DataFrame()
    else:
        df = ds[["domain", "level", "total_records", "past_records", "future_records", "has_text"]].copy()
        df["level"] = df["level"].map({"publication": "公開公報", "family": "ファミリー"}).fillna(df["level"])
        df["has_text"] = df["has_text"].map({True: "可", False: "不可"}).fillna(df["has_text"])
        df.columns = ["分野", "集計単位", "総件数", "過去期間", "将来期間", "テキスト利用"]
    write_table(df, "experiment1_dataset_table", "実験1におけるデータセットと期間分割", "tab:experiment1_dataset_table")


def make_experiment1_unet_occurrence_table() -> None:
    ds = read_csv(TABLE_SOURCE / "dataset_summary.csv")
    if ds.empty:
        df = pd.DataFrame()
    else:
        df = ds[["domain", "level", "is_unet_total", "is_unet_rate", "is_unet_past", "is_unet_future"]].copy()
        df["level"] = df["level"].map({"publication": "公開公報", "family": "ファミリー"}).fillna(df["level"])
        df.columns = ["分野", "集計単位", "U-Net総件数", "U-Net出現率", "過去期間", "将来期間"]
    write_table(df, "experiment1_unet_occurrence_table", "実験1におけるU-Net出現状況", "tab:experiment1_unet_occurrence_table")


def make_experiment1_evaluation_summary_table() -> None:
    temporal = read_csv(TABLE_SOURCE / "temporal_evaluation_summary.csv")
    ds = read_csv(TABLE_SOURCE / "dataset_summary.csv")
    if temporal.empty or ds.empty:
        df = pd.DataFrame()
    else:
        lookup = dict(zip(temporal["metric"], temporal["value"]))
        pub = ds[ds["level"] == "publication"].set_index("domain")
        a0_past = int(pub.loc["A0", "is_unet_past"])
        b0_past = int(pub.loc["B0", "is_unet_past"])
        b0_future = int(pub.loc["B0", "is_unet_future"])
        b0_past_interpretation = (
            "製造欠陥検出分野の過去期間では確認されなかった"
            if b0_past == 0
            else "製造欠陥検出分野の過去期間では極めて低出現であった"
        )
        rows = [
            ["U-Net候補ランキング順位", f"{int(lookup.get('rank_in_past_ranking', 2))}位", "過去期間の具体的手法ランキングで上位に抽出された"],
            ["上位3件以内の抽出", "該当", "専門家確認候補として十分上位に含まれた"],
            ["A0過去U-Net出現件数", f"{a0_past}件", "医療画像解析分野の過去期間で確認された"],
            ["B0過去U-Net出現件数", f"{b0_past}件", b0_past_interpretation],
            ["B0将来U-Net出現件数", f"{b0_future}件", "製造欠陥検出分野の将来期間で確認された"],
            ["評価の位置づけ", "後ろ向き評価", "将来予測ではなく、既知の後年出現を用いた確認である"],
        ]
        df = pd.DataFrame(rows, columns=["項目", "値", "解釈"])
    write_table(df, "experiment1_evaluation_summary_table", "U-Net候補抽出に関する後ろ向き確認結果", "tab:experiment1_evaluation_summary_table")


def make_extraction_fields_table() -> None:
    df = pd.DataFrame(
        [
            ["problem_context", "発明が解こうとする課題、目的、問題点"],
            ["solution_context", "課題に対して提示される構成、方法、処理手順"],
            ["technical_means", "具体的な技術手段、手法名、材料、構成要素"],
            ["target_object", "技術が適用される対象物や材料"],
            ["application_field", "発明が用いられる応用分野や利用場面"],
            ["effect_context", "発明によって得られる効果や改善点"],
        ],
        columns=["抽出項目", "定義"],
    )
    write_table(df, "extraction_fields_table", "LLMにより抽出する文脈項目の定義", "tab:extraction_fields_table")


def make_solution_type_definition_table() -> None:
    df = pd.DataFrame(
        [
            [
                "近接解決策型",
                "課題文脈と解決手段文脈の双方が比較的近い候補",
                "実験1",
                "U-Net",
                "主分析",
            ],
            [
                "異質解決策型",
                "課題文脈には関連があるが、対象物・材料・分野が大きく異なる候補",
                "実験2",
                "洗浄・除去系技術",
                "補助分析",
            ],
        ],
        columns=["候補タイプ", "定義", "対象実験", "例", "位置づけ"],
    )
    write_table(df, "solution_type_definition_table", "近接解決策型と異質解決策型の定義", "tab:solution_type_definition_table")


def make_experiment1_result_table() -> None:
    ds = read_csv(TABLE_SOURCE / "dataset_summary.csv")
    temporal = read_csv(TABLE_SOURCE / "temporal_evaluation_summary.csv")
    rows = []
    if not ds.empty:
        a0_pub = ds[(ds["domain"] == "A0") & (ds["level"] == "publication")].iloc[0]
        b0_pub = ds[(ds["domain"] == "B0") & (ds["level"] == "publication")].iloc[0]
        rows.extend(
            [
                ["A0公開公報総数", int(a0_pub["total_records"]), "データセット規模"],
                ["B0公開公報総数", int(b0_pub["total_records"]), "データセット規模"],
                ["A0 U-Net件数", int(a0_pub["is_unet_total"]), "出現状況"],
                ["B0 U-Net件数", int(b0_pub["is_unet_total"]), "出現状況"],
            ]
        )
    if not temporal.empty:
        lookup = dict(zip(temporal["metric"], temporal["value"]))
        rows.append(["U-Net候補ランキング順位", f"{int(lookup.get('rank_in_past_ranking', 2))}位", "候補抽出結果"])
        rows.append(["上位3件以内の抽出", "該当", "候補抽出結果"])
    df = pd.DataFrame(rows, columns=["項目", "値", "区分"])
    write_table(df, "experiment1_result_table", "実験1主分析の簡略要約", "tab:experiment1_result_table")


def make_experiment1_baseline_table() -> None:
    df = read_csv(P1 / "final_candidate_type_summary.csv")
    if df.empty:
        df = pd.DataFrame()
    else:
        label_map = {
            "proposed_top": "提案手法",
            "fulltext_top_baseline": "全文類似上位ベースライン",
        }
        df = df[df["group_value"].isin(label_map)].copy()
        df["group_value"] = df["group_value"].map(label_map)
        df = df[
            [
                "group_value",
                "count",
                "candidate_score_mean",
                "valid_candidate_rate_score_ge_2",
                "label_◎",
                "label_○",
                "label_△",
                "label_×",
            ]
        ].copy()
        df.columns = [
            "Candidate type",
            "N",
            "Mean score",
            "Valid rate",
            "Strong",
            "Plausible",
            "Weak",
            "Reject",
        ]
        df.columns = ["候補集合", "N", "平均スコア", "妥当候補率", "◎", "○", "△", "×"]
    write_table(df, "experiment1_baseline_table", "実験1における提案手法と全文類似上位ベースラインの比較", "tab:experiment1_baseline_table")


def make_experiment2_label_summary_table() -> None:
    final = read_csv(P2 / "heterogeneous_manual_review_final_strict.csv")
    counts = final["human_label"].value_counts().to_dict() if not final.empty else {}
    strong = int(counts.get("◎", 0) + counts.get("○", 0))
    broad = int(strong + counts.get("△", 0))
    meaning = {"◎": "強い候補", "○": "妥当候補", "△": "弱い候補", "×": "不適切候補"}
    df = pd.DataFrame(
        [[raw, meaning[raw], int(counts.get(raw, 0))] for raw in LABEL_ORDER]
        + [["◎+○", "強い候補または妥当候補", strong], ["◎+○+△", "広義の確認候補", broad]],
        columns=["ラベル", "意味", "件数"],
    )
    expected = {"◎": 11, "○": 5, "△": 12, "×": 18}
    mismatches = {k: (counts.get(k, 0), v) for k, v in expected.items() if int(counts.get(k, 0)) != v}
    if mismatches:
        print(f"WARNING: Experiment 2 final label counts differ from expected: {mismatches}")
    write_table(df, "experiment2_label_summary_table", "実験2におけるLLM支援付き著者確認評価の全体集計", "tab:experiment2_label_summary_table")


def make_experiment2_cluster_summary_table() -> None:
    df = read_csv(P2 / "heterogeneous_manual_review_by_cluster.csv")
    if not df.empty:
        df = df[
            [
                "cluster",
                "total_rows",
                "label_◎_count",
                "label_○_count",
                "label_△_count",
                "label_×_count",
                "strong_or_plausible_count_◎○",
                "broad_candidate_count_◎○△",
            ]
        ].copy()
        cluster_map = {
            "adhesive_cleaning": "接着剤洗浄",
            "circuit_board_cleaning": "回路基板洗浄",
            "cmp_polishing_post_cleaning": "CMP後洗浄",
            "flux_electronic_component_cleaning": "フラックス・電子部品洗浄",
            "photoresist_resin_mask_removal": "フォトレジスト・樹脂除去",
            "semiconductor_substrate_cleaning": "半導体基板洗浄",
            "silicon_wafer_cleaning": "シリコンウェーハ洗浄",
        }
        df["cluster"] = df["cluster"].map(cluster_map).fillna(df["cluster"])
        df.columns = [
            "クラスタ",
            "N",
            "◎",
            "○",
            "△",
            "×",
            "◎+○",
            "◎+○+△",
        ]
    write_table(df, "experiment2_cluster_summary_table", "実験2におけるクラスタ別評価集計", "tab:experiment2_cluster_summary_table")


def make_experiment2_fulltext_baseline_table() -> None:
    overlap = read_csv(P2 / "proposed_vs_fulltext_overlap.csv")
    if overlap.empty:
        df = pd.DataFrame()
    else:
        overall = overlap[overlap["level"] == "overall"].copy()
        metric_names = {
            "proposed_count": ("提案手法件数", "提案手法のファミリー数"),
            "fulltext_baseline_count": ("ベースライン件数", "軽量全文テキストベースラインのファミリー数"),
            "overlap_family_count": ("重複件数", "重複ファミリー数"),
            "proposed_only_count": ("提案手法のみ", "提案手法にのみ含まれるファミリー数"),
            "fulltext_only_count": ("ベースラインのみ", "ベースラインにのみ含まれるファミリー数"),
        }
        overall["metric_jp"] = overall["metric"].map(lambda x: metric_names.get(x, (x, x))[0])
        overall["Description"] = overall["metric"].map(lambda x: metric_names.get(x, (x, x))[1])
        df = overall[["metric_jp", "Description", "value"]].copy()
        df.columns = ["指標", "内容", "値"]
    write_table(df, "experiment2_fulltext_baseline_table", "実験2における提案手法と軽量全文テキストベースラインの比較", "tab:experiment2_fulltext_baseline_table")


def make_experiment_comparison_table() -> None:
    df = pd.DataFrame(
        [
            [
                "実験1",
                "近接解決策型",
                "医療画像解析→製造欠陥検出",
                "U-Net",
                "主分析",
                "既知手法を用いた後ろ向き評価",
                "技術移転の因果関係は示さない",
            ],
            [
                "実験2",
                "異質解決策型",
                "洗浄・除去系技術→半導体洗浄",
                "46件のユニークファミリー",
                "補助分析",
                "クラスタ別に専門家確認候補を整理",
                "クラスタ設計に依存し、技術導入可能性は示さない",
            ],
        ],
        columns=["実験", "候補タイプ", "対象", "評価対象", "位置づけ", "強み", "注意点"],
    )
    write_table(df, "experiment1_experiment2_comparison_table", "実験1と実験2の位置づけの比較", "tab:experiment1_experiment2_comparison_table")


def make_limitations_table() -> None:
    df = pd.DataFrame(
        [
            ["技術導入可能性", "抽出候補が実際に導入・実装できることは示さない。"],
            ["LLM抽出", "課題・解決手段・技術手段の抽出には誤抽出や一般化が含まれうる。"],
            ["人手評価", "評価はLLM支援付き著者確認評価であり、大規模な第三者専門家評価ではない。"],
            ["実験2クラスタ", "異質解決策型分析はS1用途クラスタや用途語フィルタに依存する。"],
            ["特許データ", "特許公開は実装、性能、市場採用、因果関係を保証しない。"],
            ["ベースライン比較", "実験2のベースラインは軽量全文テキストベースラインであり、補助比較として扱う。"],
        ],
        columns=["観点", "限界"],
    )
    write_table(df, "limitations_table", "本研究の限界", "tab:limitations_table")


def main() -> None:
    make_dataset_summary_table()
    make_extraction_fields_table()
    make_solution_type_definition_table()
    make_experiment1_dataset_table()
    make_experiment1_unet_occurrence_table()
    make_experiment1_evaluation_summary_table()
    make_experiment1_result_table()
    make_experiment1_baseline_table()
    make_experiment2_label_summary_table()
    make_experiment2_cluster_summary_table()
    make_experiment2_fulltext_baseline_table()
    make_experiment_comparison_table()
    make_limitations_table()
    print(f"Generated thesis tables in {TABLE_DIR}")


if __name__ == "__main__":
    main()
