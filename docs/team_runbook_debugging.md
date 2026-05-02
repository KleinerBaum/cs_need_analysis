# Team Runbook – Debugging & Incident Intake

## Log-Erfassung bei Fehlern (Pflicht)

- Abgeschnittene Logs mit Encoding-Artefakten wie `â”€` oder `â±` sind **nicht ausreichend**.
- Immer den **kompletten** Traceback-/Log-Block erfassen.
- Der Block muss bis zur finalen Exception-Zeile reichen: `ExceptionType: message`.
- Für Incident-Meldungen das Template unter `docs/debugging_incident_template.md` verwenden.
