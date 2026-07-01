# Build Log Summary

## Build Result

- Build command used: `tectonic main.tex`
- PDF output: `main.pdf`
- Status: PDF generated successfully in the current environment
- Note: `latexmk` and `lualatex` were not available in this environment, so the LaTeX set was adjusted to build with `tectonic` using `report + fontspec + xeCJK`.
- Latest polish pass: 表5.2を件数中心の後ろ向き確認表に変更し、表5.3と図5.3を提案手法と全文類似上位ベースラインの主比較に絞った。実験2には既知事例を用いた後ろ向き評価であること、S0_pre_filteredとC1候補のproblem_contextベクトル比較、軽量全文テキストベースラインとの重複11件の評価内訳を追記した。

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
- Overfull hbox: final build has one very small overfull warning in Chapter 5 (0.11409pt) and minor underfull warnings in Chapters 1 and 7. Long cluster-code labels in active text were Japaneseized.
- Missing figure/table files: none detected during build.
- BibTeX/Biber errors: none during this build; `biber` was not available, so `references.bib` is maintained but not executed in the current build flow.
- Font warnings: `tectonic` warns that macOS Hiragino font paths are absolute. This is acceptable on this machine but may reduce reproducibility on another OS.

## Build Notes

- The previous `latexmk -lualatex` flow could not run because `latexmk`, `lualatex`, `biber`, `platex`, and `uplatex` were unavailable.
- `tectonic` could not build the original `ltjsreport + luatexja` version, so `main.tex` now uses a XeLaTeX-compatible setup with `fontspec` and `xeCJK`.
- `build.sh` has been updated to run `tectonic main.tex`.
- `main.pdf` is the current built PDF.
- Active LaTeX inputs used by `main.tex` were searched for old wording such as Hit@K, strict評価, unique families, 全文BERT, lightweight-fulltext baseline wording in English, unresolved figure/table placeholders, TODO, and 仮引用. No matches were found in the active PDF inputs.

## Remaining Warnings to Review Before Submission

- Check the remaining very small overfull/underfull hbox warnings only if final formatting quality is required.
- Confirm figure/table placement after visual inspection of `main.pdf`.
- Check bibliography entries against the final citation style required by the department.
