# Data Manifest

## Tracked Data

`pipeline/data/raw/` contains small sample CSV files for smoke testing.

These files are intentionally lightweight and are not the full research dataset:

- `A0_orbis_publication_level.csv`
- `A1_orbis_publication_level.csv`
- `B0_orbis_publication_level.csv`
- `B1_orbis_publication_level.csv`
- `README.md`

The sample files preserve the pipeline input schema so the repository can be tested after cloning.

## Local-Only Full Data

Full source data and large pipeline inputs are stored under `data_external/`, which is ignored by Git.

```text
data_external/source_data/
data_external/pipeline_raw_full/
```

`source_data/` contains original or near-original exported files, including Orbis IP Excel exports and legacy CSV files.

`pipeline_raw_full/` contains the full CSV inputs used by the main pipeline:

- `A0_orbis_publication_level.csv`
- `A1_orbis_publication_level.csv`
- `B0_orbis_publication_level.csv`
- `B1_orbis_publication_level.csv`

## Public Release Notes

Before pushing this repository to GitHub, check whether the source datasets can be redistributed. If redistribution is not allowed, keep `data_external/` local and publish only:

- source code
- configuration
- sample data
- final aggregate tables and figures
- thesis LaTeX source, if permitted

## Reproduction

For a quick executable check, run:

```bash
bash scripts/smoke_test.sh
```

For full-data reproduction, copy or symlink the full CSV files from `data_external/pipeline_raw_full/` into `pipeline/data/raw/`, then run:

```bash
cd pipeline
bash run_all.sh
```

Embedding steps require model downloads and are intentionally disabled unless `--with-embeddings` is supplied.
