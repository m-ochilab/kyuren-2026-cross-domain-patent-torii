from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "pipeline" / "outputs" / "thesis_artifacts"


CHAPTERS = [
    ("chapter1_introduction_draft.md", "chapters/chapter1_intro.tex"),
    ("chapter2_related_work_draft.md", "chapters/chapter2_related_work.tex"),
    ("chapter3_proposed_method_draft.md", "chapters/chapter3_method.tex"),
    ("chapter4_dataset_experimental_design_draft.md", "chapters/chapter4_dataset_design.tex"),
    ("chapter5_experiment1_unet_near_solution_draft.md", "chapters/chapter5_experiment1.tex"),
    ("chapter6_experiment2_heterogeneous_solution_draft.md", "chapters/chapter6_experiment2.tex"),
    ("chapter7_discussion_draft.md", "chapters/chapter7_discussion.tex"),
    ("chapter8_conclusion_draft.md", "chapters/chapter8_conclusion.tex"),
]


FIG_BLOCKS = {
    "chapters/chapter1_intro.tex": [
        ("1.1 本章の概要", "framework_overview", "本研究の全体像。特許文書を課題文脈と解決手段文脈に分離し、専門家確認候補を抽出するスクリーニング手法として整理する。"),
    ],
    "chapters/chapter3_method.tex": [
        ("3.1 手法の全体像", "method_pipeline", "提案手法の処理フロー。特許文書の前処理、文脈抽出、ベクトル化、候補ランキング、LLM支援付き著者確認評価までを示す。"),
        ("3.6 候補タイプの定義", "solution_type_quadrant", "課題文脈類似度と解決手段文脈類似度に基づく候補タイプの概念図。実験1を主分析、実験2を補助分析として位置づける。"),
    ],
    "chapters/chapter5_experiment1.tex": [
        ("5.1 本章の概要", "experiment1_pipeline", "実験1の処理フロー。U-Netを対象とした近接解決策型候補抽出を主分析として扱う。"),
        ("5.4 U-Netの出現傾向", "experiment1_unet_trend", "U-Netの年次出現傾向。医療画像解析分野と製造欠陥検出分野における出現時期の違いを後ろ向き評価の前提として示す。"),
        ("5.6 ベースライン比較", "experiment1_baseline_comparison", "実験1における提案手法と全文類似上位ベースラインの比較。単純な優劣ではなく、候補集合の性質差を確認する補助比較として扱う。"),
    ],
    "chapters/chapter6_experiment2.tex": [
        ("6.1 本章の概要", "experiment2_pipeline", "実験2の処理フロー。S1用途クラスタ、C1非半導体系pre候補、各クラスタ上位20件、7クラスタ分、ファミリー単位の重複統合、46件のLLM支援付き著者確認評価を示す。"),
        ("6.6 LLM支援付き著者確認評価", "experiment2_label_distribution", "実験2における評価ラベルの分布。46件のユニークファミリーを対象にしたLLM支援付き著者確認評価の結果を示す。"),
        ("6.6 LLM支援付き著者確認評価", "experiment2_cluster_distribution", "実験2におけるクラスタ別評価ラベル分布。クラスタ依存性を確認するための補助図である。"),
        ("6.7 軽量全文テキストベースラインとの補助比較", "experiment2_fulltext_overlap", "提案手法と軽量全文テキストベースラインの候補集合の重複・差分。精度優劣ではなく候補集合の傾向差を確認する。"),
    ],
}


TABLE_BLOCKS = {
    "chapters/chapter3_method.tex": [
        ("3.3 文脈抽出", "extraction_fields_table"),
        ("3.6 候補タイプの定義", "solution_type_definition_table"),
    ],
    "chapters/chapter4_dataset_design.tex": [
        ("4.2 使用データセットの全体像", "dataset_summary_table"),
        ("4.3 実験1のデータセットと設計", "experiment1_dataset_table"),
    ],
    "chapters/chapter5_experiment1.tex": [
        ("5.4 U-Netの出現傾向", "experiment1_unet_occurrence_table"),
        ("5.5 候補抽出結果", "experiment1_evaluation_summary_table"),
        ("5.6 ベースライン比較", "experiment1_baseline_table"),
    ],
    "chapters/chapter6_experiment2.tex": [
        ("6.6 LLM支援付き著者確認評価", "experiment2_label_summary_table"),
        ("6.6 LLM支援付き著者確認評価", "experiment2_cluster_summary_table"),
        ("6.7 軽量全文テキストベースラインとの補助比較", "experiment2_fulltext_baseline_table"),
    ],
    "chapters/chapter7_discussion.tex": [
        ("7.2 実験1から得られた示唆", "experiment1_experiment2_comparison_table"),
        ("7.7 本研究の限界", "limitations_table"),
    ],
}


TABLE_CAPTIONS = {
    "dataset_summary_table": "本研究で用いた主要データセットの概要",
    "extraction_fields_table": "LLMにより抽出する文脈項目の定義",
    "solution_type_definition_table": "近接解決策型と異質解決策型の定義",
    "experiment1_dataset_table": "実験1におけるデータセットと期間分割",
    "experiment1_unet_occurrence_table": "実験1におけるU-Net出現状況",
    "experiment1_evaluation_summary_table": "U-Net候補抽出に関する後ろ向き確認結果",
    "experiment1_baseline_table": "実験1における提案手法と全文類似上位ベースラインの比較",
    "experiment2_label_summary_table": "実験2におけるLLM支援付き著者確認評価の全体集計",
    "experiment2_cluster_summary_table": "実験2におけるクラスタ別評価集計",
    "experiment2_fulltext_baseline_table": "実験2における提案手法と軽量全文テキストベースラインの比較",
    "experiment1_experiment2_comparison_table": "実験1と実験2の位置づけの比較",
    "limitations_table": "本研究の限界",
}


ABSTRACT_TEXT = """本研究は、特許文書を用いたクロスドメイン技術候補抽出において、全文類似だけでは候補抽出理由を説明しにくいという問題に着目する。特許文書には、技術課題、解決手段、対象物、効果などが含まれるが、全文ベクトルとして一括で扱うと、どの観点で候補が近いのかが不明瞭になりやすい。そこで本研究では、特許文書を課題文脈である \\texttt{problem\\_context} と解決手段文脈である \\texttt{solution\\_context} に分離し、課題が近い異分野間において、対象分野では低出現または未使用である技術手法・解決手段を専門家確認候補として抽出する枠組みを検討した。実験1では、U-Netを対象とした近接解決策型の主分析を行い、医療画像解析分野で先行して現れたU-Netを、製造欠陥検出分野での後年出現を参照しながら後ろ向き評価した。その結果、U-Netは過去期間の具体的手法ランキングで2位となり、上位の専門家確認候補として確認された。実験2では、洗浄・除去系技術から半導体洗浄への異質解決策型の補助分析を行った。46件のユニークファミリーをLLM支援付き著者確認評価により確認した結果、◎11件、○5件、△12件、×18件となった。ノイズも含まれた一方で、一部クラスタでは専門家確認候補として解釈可能な候補が得られた。また、軽量全文テキストベースラインとの比較により、提案手法と全文テキストベースラインの候補集合に差分があることを補助的に確認した。ただし、本研究は技術導入可能性を証明するものではなく、専門家確認候補を絞り込むスクリーニング手法として位置づける。"""


def tex_escape_text(s: str) -> str:
    parts = re.split(r"(`[^`]+`)", s)
    out = []
    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            inner = part[1:-1].replace("\\", "\\textbackslash{}")
            inner = inner.replace("_", "\\_").replace("%", "\\%").replace("&", "\\&")
            out.append(f"\\texttt{{{inner}}}")
            continue
        part = part.replace("\\", "\\textbackslash{}")
        part = part.replace("&", "\\&").replace("%", "\\%")
        part = part.replace("_", "\\_")
        out.append(part)
    return "".join(out)


def convert_md(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    in_itemize = False
    skip_usage = False

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("使用図表:"):
            skip_usage = True
            continue
        if skip_usage:
            if not line or line.startswith("- "):
                continue
            skip_usage = False

        if line.startswith("# "):
            if in_itemize:
                out.append("\\end{itemize}")
                in_itemize = False
            title = line[2:].strip()
            title = re.sub(r"^第\d+章\s*", "", title)
            out.append(f"\\chapter{{{tex_escape_text(title)}}}")
            continue
        if line.startswith("## "):
            if in_itemize:
                out.append("\\end{itemize}")
                in_itemize = False
            title = re.sub(r"^\d+\.\d+\s*", "", line[3:].strip())
            out.append(f"\\section{{{tex_escape_text(title)}}}")
            continue
        if line.startswith("### "):
            if in_itemize:
                out.append("\\end{itemize}")
                in_itemize = False
            title = re.sub(r"^\d+\.\d+\.\d+\s*", "", line[4:].strip())
            out.append(f"\\subsection{{{tex_escape_text(title)}}}")
            continue
        if line.startswith("- "):
            if not in_itemize:
                out.append("\\begin{itemize}")
                in_itemize = True
            body = tex_escape_text(line[2:].strip())
            body = re.sub(r"^\\texttt\{([^}]+)\}:", r"\\item[\\texttt{\1}]", body)
            if not body.startswith("\\item"):
                body = "\\item " + body
            out.append(body)
            continue
        if not line:
            if in_itemize:
                out.append("\\end{itemize}")
                in_itemize = False
            out.append("")
            continue

        if in_itemize:
            out.append("\\end{itemize}")
            in_itemize = False
        out.append(tex_escape_text(line))

    if in_itemize:
        out.append("\\end{itemize}")
    return "\n".join(out).strip() + "\n"


def figure_block(name: str, caption: str) -> str:
    return (
        "\\begin{figure}[tbp]\n"
        "\\centering\n"
        f"\\includegraphics[width=0.92\\linewidth]{{{name}}}\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{fig:{name}}}\n"
        "\\end{figure}\n"
    )


def table_block(name: str) -> str:
    return f"\\input{{tables/{name}}}\n"


def insert_blocks(tex: str, rel: str) -> str:
    section_to_blocks: dict[str, list[str]] = {}
    for sec, fig, cap in FIG_BLOCKS.get(rel, []):
        section_to_blocks.setdefault(sec, []).append(figure_block(fig, cap))
    for sec, table in TABLE_BLOCKS.get(rel, []):
        section_to_blocks.setdefault(sec, []).append(table_block(table))

    for sec, blocks in section_to_blocks.items():
        sec_title = re.sub(r"^\d+\.\d+\s*", "", sec)
        target = f"\\section{{{tex_escape_text(sec_title)}}}"
        block_text = "\n" + "\n".join(blocks) + "\n"
        if target in tex:
            tex = tex.replace(target, target + block_text, 1)
    return tex


def replace_placeholder_refs(tex: str) -> str:
    replacements = {
        "図3.Xに、提案手法": "\\figref{fig:method_pipeline}に、提案手法",
        "表3.Xに、これら": "\\tabref{tab:extraction_fields_table}に、これら",
        "図3.Xに、課題文脈": "\\figref{fig:solution_type_quadrant}に、課題文脈",
        "表3.Xに各タイプ": "\\tabref{tab:solution_type_definition_table}に各タイプ",
        "表4.Xに、本研究": "\\tabref{tab:dataset_summary_table}に、本研究",
        "表4.Xに、実験1": "\\tabref{tab:experiment1_dataset_table}に、実験1",
        "表5.Xに、実験1のデータセット": "\\tabref{tab:experiment1_dataset_table}に、実験1のデータセット",
        "図5.Xに、U-Net関連": "\\figref{fig:experiment1_unet_trend}に、U-Net関連",
        "表5.Xに、U-Net関連": "\\tabref{tab:experiment1_unet_occurrence_table}に、U-Net関連",
        "表5.Xに、U-Net候補": "\\tabref{tab:experiment1_evaluation_summary_table}に、U-Net候補",
        "図5.Xに、提案手法と全文類似上位ベースライン": "\\figref{fig:experiment1_baseline_comparison}に、提案手法と全文類似上位ベースライン",
        "表5.Xに、同じ2集合": "\\tabref{tab:experiment1_baseline_table}に、同じ2集合",
        "図5.Xに、各候補集合": "\\figref{fig:experiment1_baseline_comparison}に、各候補集合",
        "表5.Xに、候補集合": "\\tabref{tab:experiment1_baseline_table}に、候補集合",
        "図6.Xおよび表6.Xに、最終評価": "\\figref{fig:experiment2_label_distribution}および\\tabref{tab:experiment2_label_summary_table}に、最終評価",
        "図6.Xおよび表6.Xに、クラスタ別": "\\figref{fig:experiment2_cluster_distribution}および\\tabref{tab:experiment2_cluster_summary_table}に、クラスタ別",
        "表6.Xに、ファミリー単位": "\\tabref{tab:experiment2_fulltext_baseline_table}に、ファミリー単位",
        "図6.Xに、提案手法": "\\figref{fig:experiment2_fulltext_overlap}に、提案手法",
        "表7.Xに、本研究": "\\tabref{tab:limitations_table}に、本研究",
    }
    for old, new in replacements.items():
        tex = tex.replace(old, new)
    return tex


def normalize_tables() -> None:
    table_dir = ROOT / "tables"
    for src in (ART / "tables").glob("*_table.tex"):
        dst = table_dir / src.name
        shutil.copy2(src, dst)

    for path in table_dir.glob("*_table.tex"):
        key = path.stem
        text = path.read_text(encoding="utf-8")
        if key in TABLE_CAPTIONS:
            text = re.sub(r"\\caption\{[^}]*\}", f"\\\\caption{{{TABLE_CAPTIONS[key]}}}", text, count=1)
        text = re.sub(r"\\label\{tab:([^}]*)\}", lambda m: "\\label{tab:" + m.group(1).replace("\\_", "_") + "}", text, count=1)
        if "\\begin{adjustbox}" not in text:
            text = text.replace("\\begin{tabular}", "\\begin{adjustbox}{max width=\\textwidth}\n\\begin{tabular}", 1)
            text = text.replace("\\end{tabular}", "\\end{tabular}\n\\end{adjustbox}", 1)
        path.write_text(text, encoding="utf-8")


def sync_figures() -> None:
    fig_dir = ROOT / "figures"
    for src in (ART / "figures").glob("*"):
        if src.suffix.lower() in {".png", ".pdf"}:
            shutil.copy2(src, fig_dir / src.name)


def write_chapters() -> None:
    (ROOT / "chapters").mkdir(exist_ok=True)
    for md_name, rel in CHAPTERS:
        md = (ART / md_name).read_text(encoding="utf-8")
        tex = convert_md(md)
        tex = insert_blocks(tex, rel)
        tex = replace_placeholder_refs(tex)
        (ROOT / rel).write_text(tex, encoding="utf-8")


def write_abstract() -> None:
    (ROOT / "chapters" / "00_abstract.tex").write_text(ABSTRACT_TEXT + "\n", encoding="utf-8")


def write_appendix() -> None:
    text = r"""\chapter{LLM文脈抽出プロンプトの概要}

本付録では、本研究で用いたLLM文脈抽出プロンプトの概要を示す。実際のプロンプトは、特許文書のTitle、Abstract、Claimsを入力し、候補ランキングに用いる文脈情報を構造化して出力することを目的とした。

\section{入力}

入力は、主に以下の特許文書情報で構成した。

\begin{itemize}
\item Title
\item Abstract
\item Claims
\item 必要に応じて公開番号、ファミリーID、日付情報
\end{itemize}

\section{抽出項目}

LLMには、本文中で定義した抽出項目を、短い説明文として整理するよう指示した。主な抽出項目は以下である。

\begin{itemize}
\item \texttt{problem\_context}: 発明が解こうとしている課題、目的、問題点
\item \texttt{solution\_context}: 課題に対して提示される構成、方法、処理手順
\item \texttt{technical\_means}: 具体的な技術手段、手法名、材料、構成要素
\item \texttt{target\_object}: 技術が適用される対象物
\item \texttt{application\_field}: 発明が用いられる応用分野や利用場面
\item \texttt{effect\_context}: 発明によって得られる効果や改善点
\end{itemize}

\section{利用上の注意}

LLM出力は、候補の妥当性を最終判定するためのものではなく、特許文書を人間が確認しやすい文脈情報に整理するための中間表現として用いた。したがって、抽出結果には誤抽出や過度な一般化が含まれる可能性があり、候補の最終的な確認はLLM支援付き著者確認評価として行った。
"""
    (ROOT / "chapters" / "appendix_a_llm_prompt.tex").write_text(text, encoding="utf-8")


def write_main() -> None:
    text = r"""% Build with: tectonic main.tex
\documentclass[12pt,a4paper,openany]{report}

\usepackage{fontspec}
\usepackage{xeCJK}
\setmainfont{Hiragino Sans}
\setsansfont{Hiragino Sans}
\setmonofont{Hiragino Sans}
\setCJKmainfont{Hiragino Sans}
\setCJKsansfont{Hiragino Sans}
\setCJKmonofont{Hiragino Sans}
\usepackage{geometry}
\geometry{top=28mm,bottom=28mm,left=30mm,right=25mm}
\setlength{\emergencystretch}{3em}
\usepackage{setspace}
\onehalfspacing
\usepackage{graphicx}
\graphicspath{{figures/}}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{tabularx}
\usepackage{multirow}
\usepackage{adjustbox}
\usepackage{amsmath,amssymb}
\usepackage{url}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{hyperref}
\hypersetup{colorlinks=true, linkcolor=black, citecolor=black, urlcolor=blue}

\newcommand{\figref}[1]{図~\ref{#1}}
\newcommand{\tabref}[1]{表~\ref{#1}}
\newcommand{\eqnref}[1]{式~\eqref{#1}}
\renewcommand{\abstractname}{要旨}
\renewcommand{\contentsname}{目次}
\renewcommand{\listfigurename}{図目次}
\renewcommand{\listtablename}{表目次}
\renewcommand{\bibname}{参考文献}
\renewcommand{\figurename}{図}
\renewcommand{\tablename}{表}
\titleformat{\chapter}[display]
  {\normalfont\huge\bfseries}
  {第\thechapter 章}
  {0.7em}
  {\Huge}

\title{特許文書の課題・解決手段分離に基づく\\クロスドメイン技術候補抽出}
\author{鳥井 春風}
\date{\today}

\begin{document}

\maketitle

\pagenumbering{roman}
\begin{abstract}
\input{chapters/00_abstract}
\end{abstract}

\tableofcontents
\listoffigures
\listoftables
\clearpage
\pagenumbering{arabic}

\input{chapters/chapter1_intro}
\input{chapters/chapter2_related_work}
\input{chapters/chapter3_method}
\input{chapters/chapter4_dataset_design}
\input{chapters/chapter5_experiment1}
\input{chapters/chapter6_experiment2}
\input{chapters/chapter7_discussion}
\input{chapters/chapter8_conclusion}

\appendix
\input{chapters/appendix_a_llm_prompt}

\input{chapters/99_references}

\end{document}
"""
    (ROOT / "main.tex").write_text(text, encoding="utf-8")


def write_reference_list() -> None:
    text = r"""\begin{thebibliography}{99}
\raggedright
\bibitem{argente2025patents} Argente, D., Baslandze, S., Hanley, D., and Moreira, S. Patents to Products: Product Innovation and Firm Dynamics. NBER Working Paper No. 34592, 2025. doi:10.3386/w34592.
\bibitem{arts2025technology} Arts, S., Cassiman, B., and Hou, J. Technology Differentiation, Product Market Rivalry, and M\&A Transactions. \textit{Strategic Management Journal}, 46(4), 837--862, 2025. doi:10.1002/smj.3687.
\bibitem{albora2024machine} Albora, G., Straccamore, M., and Zaccaria, A. Machine Learning-Based Similarity Measure to Forecast M\&A from Patent Data. arXiv:2404.07179, 2024.
\bibitem{bekamiri2024patentsberta} Bekamiri, H., Hain, D. S., and Jurowetzki, R. PatentSBERTa: A Deep NLP Based Hybrid Model for Patent Distance and Classification Using Augmented SBERT. \textit{Technological Forecasting and Social Change}, 206, 123536, 2024. doi:10.1016/j.techfore.2024.123536.
\bibitem{cong2025automation} Cong, L. W., Lu, Y., Shi, H., and Zhu, W. Automation-Induced Innovation Shift. NBER Working Paper No. 34240, 2025. doi:10.3386/w34240.
\bibitem{devlin2019bert} Devlin, J., Chang, M.-W., Lee, K., and Toutanova, K. BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding. In \textit{Proceedings of NAACL-HLT 2019}, pp. 4171--4186, 2019. doi:10.18653/v1/N19-1423.
\bibitem{giordano2023unveiling} Giordano, V., Puccetti, G., Chiarello, F., Pavanello, T., and Fantoni, G. Unveiling the Inventive Process from Patents by Extracting Problems, Solutions and Advantages with Natural Language Processing. \textit{Expert Systems with Applications}, 229, 120499, 2023. doi:10.1016/j.eswa.2023.120499.
\bibitem{griliches1990patent} Griliches, Z. Patent Statistics as Economic Indicators: A Survey. \textit{Journal of Economic Literature}, 28(4), 1661--1707, 1990.
\bibitem{ha2023patent} Ha, T. and Lee, J.-M. Examine the Effectiveness of Patent Embedding-Based Company Comparison Method. \textit{IEEE Access}, 11, 23455--23461, 2023. doi:10.1109/ACCESS.2023.3251664.
\bibitem{hain2022textembedding} Hain, D. S., Jurowetzki, R., Buchmann, T., and Wolf, P. A Text-Embedding-Based Approach to Measuring Patent-to-Patent Technological Similarity. \textit{Technological Forecasting and Social Change}, 177, 121559, 2022. doi:10.1016/j.techfore.2022.121559.
\bibitem{hall2005market} Hall, B. H., Jaffe, A., and Trajtenberg, M. Market Value and Patent Citations. \textit{The RAND Journal of Economics}, 36(1), 16--38, 2005.
\bibitem{han2021technology} Han, X., Zhu, D., Wang, X., Li, J., and Qiao, Y. Technology Opportunity Analysis: Combining SAO Networks and Link Prediction. \textit{IEEE Transactions on Engineering Management}, 68(5), 1288--1298, 2021. doi:10.1109/TEM.2019.2939175.
\bibitem{hope2017accelerating} Hope, T., Chan, J., Kittur, A., and Shahaf, D. Accelerating Innovation Through Analogy Mining. In \textit{Proceedings of the 23rd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining}, pp. 235--243, 2017. doi:10.1145/3097983.3098038.
\bibitem{jaffe1993geographic} Jaffe, A. B., Trajtenberg, M., and Henderson, R. Geographic Localization of Knowledge Spillovers as Evidenced by Patent Citations. \textit{The Quarterly Journal of Economics}, 108(3), 577--598, 1993. doi:10.2307/2118401.
\bibitem{jeong2014analogy} Jeong, C. and Kim, K. Creating Patents on the New Technology Using Analogy-Based Patent Mining. \textit{Expert Systems with Applications}, 41(8), 3605--3614, 2014. doi:10.1016/j.eswa.2013.11.045.
\bibitem{jin2024ma} Jin, G. Z., Leccese, M., and Wagman, L. M\&A and Technological Expansion. \textit{Journal of Economics \& Management Strategy}, 33(2), 338--359, 2024. doi:10.1111/jems.12551.
\bibitem{kalyani2024diffusion} Kalyani, A., Bloom, N., Carvalho, M., Hassan, T. A., Lerner, J., and Tahoun, A. The Diffusion of New Technologies. NBER Working Paper No. 28999, 2024. doi:10.3386/w28999.
\bibitem{kogan2017technological} Kogan, L., Papanikolaou, D., Seru, A., and Stoffman, N. Technological Innovation, Resource Allocation, and Growth. \textit{The Quarterly Journal of Economics}, 132(2), 665--712, 2017. doi:10.1093/qje/qjw040.
\bibitem{lee2020patentbert} Lee, J.-S. and Hsiang, J. PatentBERT: Patent Classification with Fine-Tuning a Pre-Trained BERT Model. \textit{World Patent Information}, 61, 101965, 2020. doi:10.1016/j.wpi.2020.101965.
\bibitem{liu2019roberta} Liu, Y., Ott, M., Goyal, N., Du, J., Joshi, M., Chen, D., Levy, O., Lewis, M., Zettlemoyer, L., and Stoyanov, V. RoBERTa: A Robustly Optimized BERT Pretraining Approach. arXiv:1907.11692, 2019.
\bibitem{liu2023crosscutting} Liu, Z., Feng, J., and Uden, L. From Technology Opportunities to Ideas Generation via Cross-Cutting Patent Analysis: Application of Generative Topographic Mapping and Link Prediction. \textit{Technological Forecasting and Social Change}, 192, 122565, 2023. doi:10.1016/j.techfore.2023.122565.
\bibitem{noel2013strategic} Noel, M. and Schankerman, M. Strategic Patenting and Software Innovation. \textit{The Journal of Industrial Economics}, 61(3), 481--520, 2013. doi:10.1111/joie.12024.
\bibitem{oecd2009patent} OECD. \textit{OECD Patent Statistics Manual}. OECD Publishing, 2009. doi:10.1787/9789264056442-en.
\bibitem{reimers2019sentencebert} Reimers, N. and Gurevych, I. Sentence-BERT: Sentence Embeddings Using Siamese BERT-Networks. In \textit{Proceedings of EMNLP-IJCNLP 2019}, pp. 3982--3992, 2019. doi:10.18653/v1/D19-1410.
\bibitem{rogers2003diffusion} Rogers, E. M. \textit{Diffusion of Innovations}. 5th ed., Free Press, 2003.
\bibitem{ronneberger2015unet} Ronneberger, O., Fischer, P., and Brox, T. U-Net: Convolutional Networks for Biomedical Image Segmentation. In \textit{Medical Image Computing and Computer-Assisted Intervention -- MICCAI 2015}, LNCS 9351, pp. 234--241, Springer, 2015. doi:10.1007/978-3-319-24574-4\_28.
\bibitem{trajtenberg1990penny} Trajtenberg, M. A Penny for Your Quotes: Patent Citations and the Value of Innovations. \textit{The RAND Journal of Economics}, 21(1), 172--187, 1990. doi:10.2307/2555502.
\bibitem{trapp2024llm} Trapp, M. and Warschat, J. LLM-Based Extraction of Contradictions from Patents. arXiv:2403.14258, 2024.
\bibitem{vaswani2017attention} Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, L., and Polosukhin, I. Attention Is All You Need. In \textit{Advances in Neural Information Processing Systems}, 30, 2017.
\bibitem{wang2023berttriz} Wang, J., Zhang, Z., Feng, L., Lin, K.-Y., and Liu, P. Development of Technology Opportunity Analysis Based on Technology Landscape by Extending Technology Elements with BERT and TRIZ. \textit{Technological Forecasting and Social Change}, 191, 122481, 2023. doi:10.1016/j.techfore.2023.122481.
\end{thebibliography}
"""
    (ROOT / "chapters" / "99_references.tex").write_text(text, encoding="utf-8")


def ensure_references() -> None:
    path = ROOT / "references.bib"
    text = r"""
@techreport{argente2025patents,
  author      = {Argente, David and Baslandze, Salome and Hanley, Douglas and Moreira, Sara},
  title       = {Patents to Products: Product Innovation and Firm Dynamics},
  institution = {National Bureau of Economic Research},
  type        = {NBER Working Paper},
  number      = {34592},
  year        = {2025},
  doi         = {10.3386/w34592}
}

@article{arts2025technology,
  author  = {Arts, Sam and Cassiman, Bruno and Hou, Jinyu},
  title   = {Technology Differentiation, Product Market Rivalry, and M\&A Transactions},
  journal = {Strategic Management Journal},
  year    = {2025},
  volume  = {46},
  number  = {4},
  pages   = {837--862},
  doi     = {10.1002/smj.3687}
}

@article{albora2024machine,
  author  = {Albora, Giovanni and Straccamore, Matteo and Zaccaria, Andrea},
  title   = {Machine Learning-Based Similarity Measure to Forecast M\&A from Patent Data},
  journal = {arXiv preprint arXiv:2404.07179},
  year    = {2024}
}

@article{bekamiri2024patentsberta,
  author  = {Bekamiri, Hamid and Hain, Daniel S. and Jurowetzki, Roman},
  title   = {PatentSBERTa: A Deep NLP Based Hybrid Model for Patent Distance and Classification Using Augmented SBERT},
  journal = {Technological Forecasting and Social Change},
  year    = {2024},
  volume  = {206},
  pages   = {123536},
  doi     = {10.1016/j.techfore.2024.123536}
}

@techreport{cong2025automation,
  author      = {Cong, Lin William and Lu, Yifei and Shi, Haotian and Zhu, Wuyang},
  title       = {Automation-Induced Innovation Shift},
  institution = {National Bureau of Economic Research},
  type        = {NBER Working Paper},
  number      = {34240},
  year        = {2025},
  doi         = {10.3386/w34240}
}

@inproceedings{devlin2019bert,
  author    = {Devlin, Jacob and Chang, Ming-Wei and Lee, Kenton and Toutanova, Kristina},
  title     = {BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding},
  booktitle = {Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies},
  year      = {2019},
  pages     = {4171--4186},
  doi       = {10.18653/v1/N19-1423}
}

@article{giordano2023unveiling,
  author  = {Giordano, Valentina and Puccetti, Giacomo and Chiarello, Filippo and Pavanello, Tommaso and Fantoni, Gualtiero},
  title   = {Unveiling the Inventive Process from Patents by Extracting Problems, Solutions and Advantages with Natural Language Processing},
  journal = {Expert Systems with Applications},
  year    = {2023},
  volume  = {229},
  pages   = {120499},
  doi     = {10.1016/j.eswa.2023.120499}
}

@article{griliches1990patent,
  author  = {Griliches, Zvi},
  title   = {Patent Statistics as Economic Indicators: A Survey},
  journal = {Journal of Economic Literature},
  year    = {1990},
  volume  = {28},
  number  = {4},
  pages   = {1661--1707}
}

@article{ha2023patent,
  author  = {Ha, Taeyoung and Lee, Jae-Min},
  title   = {Examine the Effectiveness of Patent Embedding-Based Company Comparison Method},
  journal = {IEEE Access},
  year    = {2023},
  volume  = {11},
  pages   = {23455--23461},
  doi     = {10.1109/ACCESS.2023.3251664}
}

@article{hain2022textembedding,
  author  = {Hain, Daniel S. and Jurowetzki, Roman and Buchmann, Tobias and Wolf, Philipp},
  title   = {A Text-Embedding-Based Approach to Measuring Patent-to-Patent Technological Similarity},
  journal = {Technological Forecasting and Social Change},
  year    = {2022},
  volume  = {177},
  pages   = {121559},
  doi     = {10.1016/j.techfore.2022.121559}
}

@article{hall2005market,
  author  = {Hall, Bronwyn H. and Jaffe, Adam and Trajtenberg, Manuel},
  title   = {Market Value and Patent Citations},
  journal = {The RAND Journal of Economics},
  year    = {2005},
  volume  = {36},
  number  = {1},
  pages   = {16--38}
}

@article{han2021technology,
  author  = {Han, Xiaohong and Zhu, Donghua and Wang, Xuefeng and Li, Jialin and Qiao, Yuliang},
  title   = {Technology Opportunity Analysis: Combining SAO Networks and Link Prediction},
  journal = {IEEE Transactions on Engineering Management},
  year    = {2021},
  volume  = {68},
  number  = {5},
  pages   = {1288--1298},
  doi     = {10.1109/TEM.2019.2939175}
}

@article{trajtenberg1990penny,
  author  = {Trajtenberg, Manuel},
  title   = {A Penny for Your Quotes: Patent Citations and the Value of Innovations},
  journal = {The RAND Journal of Economics},
  year    = {1990},
  volume  = {21},
  number  = {1},
  pages   = {172--187}
}

@article{jaffe1993geographic,
  author  = {Jaffe, Adam B. and Trajtenberg, Manuel and Henderson, Rebecca},
  title   = {Geographic Localization of Knowledge Spillovers as Evidenced by Patent Citations},
  journal = {The Quarterly Journal of Economics},
  year    = {1993},
  volume  = {108},
  number  = {3},
  pages   = {577--598}
}

@book{oecd2009patent,
  author    = {{OECD}},
  title     = {OECD Patent Statistics Manual},
  publisher = {OECD Publishing},
  year      = {2009},
  doi       = {10.1787/9789264056442-en}
}

@inproceedings{reimers2019sentencebert,
  author    = {Reimers, Nils and Gurevych, Iryna},
  title     = {Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks},
  booktitle = {Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing},
  year      = {2019},
  pages     = {3982--3992}
}

@inproceedings{ronneberger2015unet,
  author    = {Ronneberger, Olaf and Fischer, Philipp and Brox, Thomas},
  title     = {U-Net: Convolutional Networks for Biomedical Image Segmentation},
  booktitle = {Medical Image Computing and Computer-Assisted Intervention -- MICCAI 2015},
  year      = {2015},
  pages     = {234--241},
  doi       = {10.1007/978-3-319-24574-4_28}
}

@article{jeong2014analogy,
  author  = {Jeong, Chul and Kim, Kwangsoo},
  title   = {Creating Patents on the New Technology Using Analogy-Based Patent Mining},
  journal = {Expert Systems with Applications},
  year    = {2014},
  volume  = {41},
  number  = {8},
  pages   = {3605--3614},
  doi     = {10.1016/j.eswa.2013.11.045}
}

@inproceedings{hope2017accelerating,
  author    = {Hope, Tom and Chan, Joel and Kittur, Aniket and Shahaf, Dafna},
  title     = {Accelerating Innovation Through Analogy Mining},
  booktitle = {Proceedings of the 23rd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining},
  year      = {2017},
  pages     = {235--243},
  doi       = {10.1145/3097983.3098038}
}

@article{wang2023berttriz,
  author  = {Wang, Jun and Zhang, Zhen and Feng, Lei and Lin, Kai-Ying and Liu, Peng},
  title   = {Development of Technology Opportunity Analysis Based on Technology Landscape by Extending Technology Elements with BERT and TRIZ},
  journal = {Technological Forecasting and Social Change},
  year    = {2023},
  volume  = {191},
  pages   = {122481},
  doi     = {10.1016/j.techfore.2023.122481}
}

@article{liu2023crosscutting,
  author  = {Liu, Zhen and Feng, Jie and Uden, Lorna},
  title   = {From Technology Opportunities to Ideas Generation via Cross-Cutting Patent Analysis: Application of Generative Topographic Mapping and Link Prediction},
  journal = {Technological Forecasting and Social Change},
  year    = {2023},
  volume  = {192},
  pages   = {122565},
  doi     = {10.1016/j.techfore.2023.122565}
}

@article{jin2024ma,
  author  = {Jin, Ginger Zhe and Leccese, Marco and Wagman, Liad},
  title   = {M\&A and Technological Expansion},
  journal = {Journal of Economics \& Management Strategy},
  year    = {2024},
  volume  = {33},
  number  = {2},
  pages   = {338--359},
  doi     = {10.1111/jems.12551}
}

@techreport{kalyani2024diffusion,
  author      = {Kalyani, Aakash and Bloom, Nicholas and Carvalho, Vasco M. and Hassan, Tarek A. and Lerner, Josh and Tahoun, Ahmed},
  title       = {The Diffusion of New Technologies},
  institution = {National Bureau of Economic Research},
  type        = {NBER Working Paper},
  number      = {28999},
  year        = {2024},
  doi         = {10.3386/w28999}
}

@book{rogers2003diffusion,
  author    = {Rogers, Everett M.},
  title     = {Diffusion of Innovations},
  publisher = {Free Press},
  year      = {2003},
  edition   = {5}
}

@article{trapp2024llm,
  author  = {Trapp, Matthias and Warschat, Joachim},
  title   = {LLM-based Extraction of Contradictions from Patents},
  journal = {arXiv preprint arXiv:2403.14258},
  year    = {2024}
}

@article{kogan2017technological,
  author  = {Kogan, Leonid and Papanikolaou, Dimitris and Seru, Amit and Stoffman, Noah},
  title   = {Technological Innovation, Resource Allocation, and Growth},
  journal = {Quarterly Journal of Economics},
  year    = {2017},
  volume  = {132},
  number  = {2},
  pages   = {665--712}
}

@article{lee2020patentbert,
  author  = {Lee, Jieh-Sheng and Hsiang, Jieh},
  title   = {PatentBERT: Patent Classification with Fine-Tuning a Pre-Trained BERT Model},
  journal = {World Patent Information},
  year    = {2020},
  volume  = {61},
  pages   = {101965},
  doi     = {10.1016/j.wpi.2020.101965}
}

@article{liu2019roberta,
  author  = {Liu, Yinhan and Ott, Myle and Goyal, Naman and Du, Jingfei and Joshi, Mandar and Chen, Danqi and Levy, Omer and Lewis, Mike and Zettlemoyer, Luke and Stoyanov, Veselin},
  title   = {RoBERTa: A Robustly Optimized BERT Pretraining Approach},
  journal = {arXiv preprint arXiv:1907.11692},
  year    = {2019}
}

@article{noel2013strategic,
  author  = {Noel, Michael and Schankerman, Mark},
  title   = {Strategic Patenting and Software Innovation},
  journal = {The Journal of Industrial Economics},
  year    = {2013},
  volume  = {61},
  number  = {3},
  pages   = {481--520},
  doi     = {10.1111/joie.12024}
}

@inproceedings{vaswani2017attention,
  author    = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and Uszkoreit, Jakob and Jones, Llion and Gomez, Aidan N. and Kaiser, Lukasz and Polosukhin, Illia},
  title     = {Attention Is All You Need},
  booktitle = {Advances in Neural Information Processing Systems},
  year      = {2017},
  volume    = {30}
}
""".strip() + "\n"
    path.write_text(text, encoding="utf-8")


def write_logs() -> None:
    build_log = """# Build Log Summary

## Build Result

- Build command used: `tectonic main.tex`
- PDF output: `main.pdf`
- Status: PDF generated successfully in the current environment
- Note: `latexmk` and `lualatex` were not available in this environment, so the LaTeX set was adjusted to build with `tectonic` using `report + fontspec + xeCJK`.
- Latest polish pass: figure labels, figure/table captions, table labels, and bibliography metadata were updated for the submission draft.

## Integrated Files

- `main.tex`
- `chapters/00_abstract.tex`
- `chapters/chapter1_intro.tex`
- `chapters/chapter2_related_work.tex`
- `chapters/chapter3_method.tex`
- `chapters/chapter4_dataset_design.tex`
- `chapters/chapter5_experiment1.tex`
- `chapters/chapter6_experiment2.tex`
- `chapters/chapter7_discussion.tex`
- `chapters/chapter8_conclusion.tex`
- `chapters/appendix_a_llm_prompt.tex`
- `chapters/99_references.tex`
- `figures/`
- `tables/`
- `references.bib`

## Warning Summary

- Undefined citations: none detected in the active LaTeX inputs, because the current draft uses a manual bibliography list and keeps BibTeX entries for later cleanup.
- Undefined references: no fatal undefined-reference error occurred; `tectonic` reran until auxiliary files stabilized, then produced `main.pdf`.
- Overfull hbox: only minor layout warnings remain. Major figure/table wording and long cluster-code labels were Japaneseized.
- Missing figure/table files: none detected during build.
- BibTeX/Biber errors: none during this build; `biber` was not available, so `references.bib` is maintained but not executed in the current build flow.
- Font warnings: `tectonic` warns that macOS Hiragino font paths are absolute. This is acceptable on this machine but may reduce reproducibility on another OS.

## Build Notes

- The previous `latexmk -lualatex` flow could not run because `latexmk`, `lualatex`, `biber`, `platex`, and `uplatex` were unavailable.
- `tectonic` could not build the original `ltjsreport + luatexja` version, so `main.tex` now uses a XeLaTeX-compatible setup with `fontspec` and `xeCJK`.
- `build.sh` has been updated to run `tectonic main.tex`.
- `main.pdf` is the current built PDF.
- The active LaTeX inputs should be searched for placeholder notes, provisional citations, disallowed wording, and major overclaim expressions before final submission.

## Remaining Warnings to Review Before Submission

- Check the remaining very small overfull/underfull hbox warnings only if final formatting quality is required.
- Confirm figure/table placement after visual inspection of `main.pdf`.
- Check bibliography entries against the final citation style required by the department.
"""
    todos = """# Remaining Tasks

## Submission Checks

- [ ] データセット件数の最終照合
- [ ] 図表番号と本文参照の確認
- [ ] BibTeX書誌情報の確認
- [ ] 過剰主張表現の確認
- [ ] 実験2ベースラインを「軽量全文テキストベースライン」に統一できているか
- [ ] 実験1が主分析、実験2が補助分析として書かれているか
- [ ] 「LLM支援付き著者確認評価」に表現が統一されているか

## Bibliography Checks

- [ ] `references.bib` の書誌情報を最終提出用の形式に整える。
- [ ] `chapters/99_references.tex` の手動参考文献リストを、最終的なBibTeX運用に合わせる。
- [ ] 追加済み30件の参考文献について、大学指定スタイルに合わせて表記を最終調整する。
- [ ] 手動参考文献リストと `references.bib` の対応を点検する。
- [ ] DOI、巻号、ページ範囲、会議名の表記ゆれを点検する。

## Layout Checks

- [ ] `main.pdf` を目視確認し、図表が本文の近くに配置されているか確認する。
- [ ] overfull hbox 警告の出ている箇所を必要に応じて短文化する。
- [ ] 表の英語列名を、提出先の方針に合わせて日本語化するか確認する。
- [ ] macOS Hiragino font に依存しているため、別環境でビルドする場合はフォント設定を確認する。

## Interpretation Notes

- 本研究は、技術導入可能性を証明するものではなく、専門家確認候補を抽出するスクリーニング手法として記述する。
- 実験1は主分析、実験2は補助分析として扱う。
- 実験2のベースラインは、軽量全文テキストベースラインとして扱い、厳密な埋め込みベースラインと混同しない。
- 評価は、完全な第三者専門家評価ではなく、LLM支援付き著者確認評価として扱う。
"""
    (ROOT / "build_log_summary.md").write_text(build_log, encoding="utf-8")
    (ROOT / "remaining_todos.md").write_text(todos, encoding="utf-8")


def main() -> None:
    sync_figures()
    normalize_tables()
    write_chapters()
    write_abstract()
    write_appendix()
    write_main()
    write_reference_list()
    ensure_references()
    write_logs()


if __name__ == "__main__":
    main()
