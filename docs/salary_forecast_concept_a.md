# Salary Forecast – Concept A (indikativ)

Kurzfassung: Concept A liefert eine **indikative** Gehaltsbandbreite (p10/p50/p90) auf Basis von strukturierter Stellen- und Kontextinformation. Es ist ein Entscheidungs-Input, **keine** statistisch kalibrierte Vorhersage mit Garantien.

## 1) Inputs

Die Berechnung kombiniert vier Input-Schichten:

1. **JobAdExtract** (normalisierte Jobdaten)
   - Beispiele: `job_title`, `seniority_level`, `location_city`, `location_country`, `must_have_skills`, `responsibilities`, `languages`, `certifications`, `salary_range`, `remote_policy`, `recruitment_steps`.
2. **Wizard-Antworten** (`answers`)
   - Anzahl sinnvoll befüllter Antworten geht in `answers_count` ein.
3. **ESCO-Kontext** (`SalaryEscoContext`)
   - `occupation_uri`, `skill_uris_must`, `skill_uris_nice`, `esco_version`.
4. **Szenario-Inputs** (`SalaryScenarioInputs` + Preset-Overrides)
   - z. B. Standort-Override, Suchradius, Remote-Anteil sowie begrenzte Multiplikator-Deltas.

## 2) Benchmark-Layer Contract (CSV)

Die Benchmark-Ebene erwartet eine CSV mit folgenden Pflichtspalten:

- `dataset_version` (str)
- `year` (int)
- `country_code` (str)
- `region_id` (str)
- `occupation_id` (str)
- `currency` (str)
- `period` (str)
- `n` (int | leer)
- `p10` (float)
- `p50` (float)
- `p90` (float)
- `source_label` (str)

Lookup/Fallback-Reihenfolge:
1. `occupation_id + region_id`
2. `occupation_id + DE`
3. `ANY + region_id`
4. `ANY + DE`
5. kein Treffer → heuristische Baseline

## 3) Adjustments & Driver-Logik

Ausgehend von der Baseline (Benchmark-Treffer oder heuristische Baseline) werden additive Deltas auf die Bandwerte angewandt. Relevante Treiber sind u. a.:

- Anforderungsdichte
- Seniorität
- Remote-Policy
- Interviewprozess
- Standortfaktor
- Jobtitelfaktor
- Suchradius
- ESCO Skill-Premiums

Die Treiber werden als strukturierte Driver-Liste ausgegeben (`key`, `label`, `category`, `impact_eur`, `detail`).

## 4) Datenqualitätssignale (`quality.kind = data_quality_score`)

`data_quality_score` ist ein **heuristischer Qualitätsindikator** im Bereich 0–1.

Was der Wert abbildet (Signalqualität der Inputs):
- Vorhandensein eines Benchmark-Treffers (`benchmark_hit`)
- gewählter Fallback-Pfad (`fallback_path`)
- Mapping-IDs (`occupation_id`, `region_id`)
- Abdeckung durch befüllte Wizard-Felder (`answers_count`)
- ESCO-Skill-/Coverage-Signale

Was der Wert **nicht** bedeutet:
- **keine** kalibrierte Eintrittswahrscheinlichkeit
- **keine** statistische Konfidenz im inferenzstatistischen Sinn
- **keine** Garantie, dass Marktgehälter in p10/p50/p90 mit dieser Genauigkeit getroffen werden

## 5) Bekannte Grenzen

- **Entgeltatlas-/Median-Logik:** p50 ist als Median-Orientierung zu lesen, nicht als Erwartungswert je Einzelfall.
- **Upper Tail (p90):** obere Verteilungsschwänze sind typischerweise instabiler (kleine Teilmengen, Sonderprofile, Equity/Bonus-Effekte).
- **Mapping-Risiko:** Fehlzuordnung von Occupation/Region kann die gesamte Bandlage verschieben.
- **Heuristischer Fallback:** ohne Benchmark-Treffer greift eine regelbasierte Baseline mit begrenzter Marktabdeckung.
- **Komponenten außerhalb des Modells:** variable Vergütung, Unternehmensgröße, Tarifbindung, Branchenzyklen und Verhandlungseffekte sind nur teilweise oder indirekt enthalten.

## 6) Praktische Leseregel

- Nutze Concept A als **indikative Vergleichsbasis** zwischen Szenarien.
- Prüfe `provenance` + `quality.signals` vor Entscheidung.
- Für verbindliche Budget-/Offer-Entscheidungen immer externes Markt-Benchmarking ergänzen.
