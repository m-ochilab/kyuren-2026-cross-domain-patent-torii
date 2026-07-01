# Verification Log

Date: 2026-06-17

Target directory:

```text
/Users/h-torii4649/sotsuron_crossdomain_research_repo_20260617
```

## Checks Performed

### Python syntax check

Command:

```bash
python3 -m py_compile pipeline/src/*.py pipeline/scripts/*.py scripts/*.py legacy_tools/*.py thesis/figures/make_figures.py
```

Result: passed through `scripts/smoke_test.sh`.

### Pipeline sample run

Command:

```bash
cd pipeline
SAMPLE_N=20 bash run_all.sh
```

Result: passed.

The sample run completed the following steps:

- column check
- preprocessing
- method-term extraction
- heuristic problem/solution context extraction
- method gap calculation
- ranking generation
- temporal evaluation
- baseline comparison
- thesis figure/table export

Embedding steps were skipped because `--with-embeddings` was not supplied. This is intentional for a lightweight GitHub smoke test.

### Main thesis LaTeX build

Command:

```bash
cd thesis
tectonic main.tex
```

Result: passed. `thesis/main.pdf` was generated.

Warnings observed:

- local macOS Hiragino font paths are referenced by the TeX engine
- minor overfull/underfull hbox warnings

These warnings did not stop PDF generation.

### Research plan LaTeX check

Command path:

```bash
cd research_plan_latex
```

Result: not built in the current environment because `lualatex` is not installed.

The research plan template uses `ltjsreport` / `luatexja`, so it should be built in a LuaLaTeX-capable TeX Live environment.

## Data Organization Check

Repository size after organization:

```text
2.6G total
2.5G data_external/       # Git ignored local full data
11M  pipeline/            # GitHub-friendly code + sample data
15M  results/
2.3M thesis/
2.1M research_plan_latex/
```

`data_external/` is intentionally ignored by Git. It contains:

- `source_data/`
- `pipeline_raw_full/`

Tracked sample inputs are in:

```text
pipeline/data/raw/
```

## Conclusion

The organized repository is executable for lightweight reproduction and contains local full-data storage for the complete research assets. Before publishing to GitHub, confirm that external data redistribution is permitted.
