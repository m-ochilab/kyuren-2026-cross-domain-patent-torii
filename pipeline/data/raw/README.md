# raw data directory

このディレクトリには生データを配置してください。

- `A0_orbis_publication_level.csv`, `B0_orbis_publication_level.csv` は，分割された Orbis IP の Excel export（`A0-Core *.xlsx`, `B0-Core *.xlsx`）から生成した publication-level CSV です。
- `A1_orbis_publication_level.csv`, `B1_orbis_publication_level.csv` は，Orbis IP の Excel export（`A1-Core*.xlsx`, `B1-Core*.xlsx`）から生成した publication-level CSV です。
- 生成には `pipeline/src/00a_build_orbis_publication_csv.py` を使用します。
- 1 publication が複数行に展開されている Orbis の `Results` シートを，`Publication number` で1行に正規化しています。
- Title，Abstract，Claims は LLM に渡せるように XML/HTML タグを除去したプレーンテキストとして保存しています。
- `pipeline/config/config.yaml` は，このCSVを `a0_csv`, `b0_csv` として参照します。
- U-Net判定は下流の `01_preprocess_patents.py` で `is_unet_title_abstract`, `is_unet_claims`, `is_unet_full_text`, `is_unet_final` に分けます。既定の最終判定は Title/Abstract 由来です。
