# Debugging Incident Template

Nutze dieses Template für jede Incident-/Fehlermeldung, damit Engineering und Betrieb sofort reproduzierbare Informationen haben.

## Pflichtfelder

### 1) Repro-Schritte
- Schritt 1:
- Schritt 2:
- Schritt 3:
- Eingaben/Dateien/Feature-Flags:

### 2) Expected vs. Actual
- **Expected (erwartetes Verhalten):**
- **Actual (tatsächliches Verhalten):**

### 3) Vollständiger Traceback
> Wichtig: Den kompletten Block erfassen, inkl. **letzter Exception-Zeile** im Format `ExceptionType: message`.

```text
<vollständiger traceback hier>
```

### 4) Commit / Branch / Deploy-Zeit
- **Commit SHA:**
- **Branch:**
- **Deploy-Zeit (UTC):**
- **Umgebung (z. B. local/staging/prod):**

---

## Optional (empfohlen)
- Betroffene Nutzergruppe/Scope:
- Häufigkeit/Trigger:
- Screenshots:
- Erste Hypothese:
