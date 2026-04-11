# Salary benchmark CSV ingestion

This project supports **Concept A benchmark grounding** using a local CSV file (no scraping).

## Required CSV schema

Each row must contain these columns:

- `dataset_version` (`str`): semantic version or snapshot id of the benchmark dataset.
- `year` (`int`): reference year for the salary distribution.
- `country_code` (`str`): ISO country code (e.g., `DE`).
- `region_id` (`str`): stable region key (e.g., `DE`, `DE-BE`).
- `occupation_id` (`str`): normalized occupation key, e.g. `title::<normalized>` or `esco::<uri>`.
- `currency` (`str`): ISO currency code (e.g., `EUR`).
- `period` (`str`): salary period (e.g., `year`, `month`, `hour`).
- `n` (`int | empty`): optional sample size for that benchmark slice.
- `p10` (`float`): lower percentile baseline.
- `p50` (`float`): median baseline.
- `p90` (`float`): upper percentile baseline.
- `source_label` (`str`): human-readable source provenance label.

## Provenance checklist

Before using a benchmark dataset, verify:

1. **Year quality**: `year` matches the published statistical period.
2. **Source traceability**: `source_label` clearly maps to the official publication/export.
3. **Granularity fit**: `region_id` and `occupation_id` align with product lookup behavior.
4. **Sample transparency**: `n` is provided when published; leave empty only when unavailable.
5. **License compliance**: usage rights are compatible with product and redistribution constraints.

## Compliance statement

**Do not scrape BA (Bundesagentur für Arbeit) or other portals.**
Only ingest officially exported/downloaded tables from permitted sources and keep provenance metadata in the CSV.

## Local override

By default, the app resolves benchmark CSV from:

- `data/salary_benchmarks/demo_de.csv`

Override locally with:

```bash
export SALARY_BENCHMARK_PATH=/absolute/path/to/benchmarks.csv
```
