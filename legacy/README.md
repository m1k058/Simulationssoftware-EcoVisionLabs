# Legacy Code Archive

**Stand:** 10. Januar 2026  
**Status:** Archiviert - Nicht mehr in Verwendung

Dieser Ordner enthält alten Code, der aus dem aktiven Projekt entfernt wurde.

---

## 📁 Ordnerstruktur

```
legacy/
├── deprecated_code/     # Alte Utility-Module
│   ├── col.py          # Spalten-Utilities (ersetzt durch inline-Code)
│   └── gen.py          # Erzeugungs-Utilities (nicht mehr verwendet)
├── old_plotting/        # Alte Plotting-Module (Matplotlib, non-Streamlit)
│   ├── plotting.py
│   ├── plotting_plotly.py
│   ├── plotting_formated.py
│   └── plotting_formated_st.py
└── step_simulation/     # Step-by-Step UI (nicht mehr zugänglich)
```

---

## ⚠️ Wichtige Hinweise

### deprecated_code/

**col.py** - Spalten-Operationen
- `get_column_total()` → Ersetzt durch `df[column].sum()`
- `show_first_rows()` → Ersetzt durch `df.head()`
- Andere Funktionen wurden nicht mehr verwendet

**gen.py** - Erzeugungs-Utilities
- Wurde überhaupt nicht mehr verwendet
- Funktionalität wurde in `generation_profile.py` integriert

### old_plotting/

Alle diese Module wurden durch modernere Streamlit+Plotly Versionen ersetzt:
- **plotting.py** → Alte Matplotlib-Implementierung
- **plotting_plotly.py** → Plotly ohne Streamlit
- **plotting_formated.py** → Matplotlib mit Formatierung
- **plotting_formated_st.py** → Matplotlib mit Streamlit (deprecated)

**Aktuell in Verwendung:**
- `source-code/plotting/plotting_plotly_st.py` - Hauptmodul für alle Plots
- `source-code/plotting/economic_plots.py` - Wirtschaftliche Auswertungen

### step_simulation/

Die Step-by-Step Simulation-UI wurde entfernt:
- War nicht mehr über die UI erreichbar
- Verwendete deprecated `calc_scaled_consumption()` Funktion
- Funktionalität ist in `simulation_standard.py` integriert

---

## 🔧 Migration Notes

### Wenn col.py Funktionen benötigt werden:

```python
# Alt (col.py):
total = col.get_column_total(df, "Spalte [MWh]")

# Neu (inline):
total = df["Spalte [MWh]"].sum()
```

```python
# Alt (col.py):
col.show_first_rows(df)

# Neu (pandas):
print(df.head())  # oder im Notebook: df.head()
```

### Wenn alte Plotting-Funktionen benötigt werden:

Alle Plotting-Funktionen wurden durch `plotting_plotly_st.py` ersetzt.

**Beispiel:**

```python
# Alt (plotting.py):
from plotting.plotting import plot_balance

# Neu (plotting_plotly_st.py):
from plotting.plotting_plotly_st import plot_balance_plotly_st
```

---

## 🗑️ Kann vollständig gelöscht werden?

**Ja**, wenn:
- ✅ Alle Tests nach dem Refactoring erfolgreich laufen
- ✅ Keine externen Skripte diese Module importieren
- ✅ Git-Historie bleibt erhalten (Code kann aus Commits wiederhergestellt werden)

**Empfehlung:**
Behalte diesen Ordner für ~1-2 Monate, um sicherzustellen, dass nichts fehlt.
Danach kann er komplett gelöscht werden.

---

## 📝 Entfernte deprecated Funktionen aus simulation.py

Die folgenden Funktionen wurden aus `simulation.py` entfernt, da sie deprecated waren:

### calc_scaled_consumption()
- **Status:** DEPRECATED seit [Datum]
- **Grund:** Alte "Top-Down" Logik
- **Ersetzt durch:** `simulate_consumption_BDEW()` (Bottom-Up mit BDEW-Profilen)
- **Letzte Verwendung:** In `step_simulation/steps.py` (auch entfernt)

### calc_scaled_consumption_multiyear()
- **Status:** DEPRECATED
- **Grund:** Wrapper für deprecated `calc_scaled_consumption()`
- **Ersetzt durch:** Loop über `simulate_consumption_BDEW()`

### calc_scaled_production_multiyear()
- **Status:** DEPRECATED  
- **Grund:** Teil der alten Top-Down Logik
- **Ersetzt durch:** Moderne Erzeugungs-Simulation mit Kapazitätsfaktoren

**Code-Backup:**
Falls diese Funktionen doch noch benötigt werden, können sie aus diesem Git-Commit wiederhergestellt werden:
```bash
git show <commit-hash>:source-code/data_processing/simulation.py
```

---

## 📅 Timeline

| Datum | Aktion |
|-------|--------|
| 10.01.2026 | Legacy-Code nach `legacy/` verschoben |
| 10.01.2026 | Deprecated Funktionen aus `simulation.py` entfernt |
| 10.01.2026 | `col.py` und `gen.py` Imports entfernt |
| 10.01.2026 | Alte Plotting-Module archiviert |
| 10.01.2026 | `step_simulation/` entfernt |

---

**Fragen?** Siehe [CODE_REVIEW_UND_REFACTORING.md](../docs/CODE_REVIEW_UND_REFACTORING.md)
