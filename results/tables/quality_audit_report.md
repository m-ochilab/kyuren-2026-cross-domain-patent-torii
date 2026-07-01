# Quality Audit Summary

## Adoption Rules

- `is_unet_final = is_unet_title_abstract` in the main analysis.
- `is_unet_claims` and `is_unet_full_text` are kept for supplementary analysis.
- Rows with `domain_noise_flag = 1` are review targets before final exclusion.
- Family-level U-Net flags are aggregated by max: if any publication in a family is U-Net, the family flag is 1.

## A0

- input records: 1000
- review sample: `outputs/review_samples/A0_manual_review_sample.csv` (50 rows)

## B0

- input records: 1000
- review sample: `outputs/review_samples/B0_manual_review_sample.csv` (50 rows)

## Output Files

- `outputs/tables/quality_audit_summary.csv`
- `outputs/review_samples/A0_manual_review_sample.csv`
- `outputs/review_samples/B0_manual_review_sample.csv`
