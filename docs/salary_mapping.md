# Salary Mapping (deterministic)

## Overview

The salary engine now uses deterministic mapping helpers from `salary/mapping.py`:

- `normalize_token(s)` normalizes free-text values (lowercase, ASCII fold, compact spaces).
- `infer_region_id(country, city)` maps location to a region id.
- `infer_occupation_id(esco_context, job_title)` maps occupation to an id.

## Region mapping

- Primary rule: use `country + city`.
- Germany (`DE`) uses a seeded city-to-region mapping (e.g. `Berlin -> DE-BE`, `München -> DE-BY`).
- If a German city is unknown, fallback is `DE`.
- For non-DE countries, country aliases are normalized to deterministic country ids (e.g. `US`, `CH`).

## Occupation mapping

- Primary: ESCO URI from `SalaryEscoContext` as `esco::<uri>`.
- Secondary fallback: normalized title as `title::<normalized title>`.
- Empty title fallback: `title::unknown`.

## Deprecated behavior

- Session key `cs.salary.scenario.location_override` is kept for backward compatibility only.
- New scenario inputs are:
  - `cs.salary.scenario.location_city_override`
  - `cs.salary.scenario.location_country_override`
- The summary page no longer writes city overrides into `JobAdExtract.location_country`.
