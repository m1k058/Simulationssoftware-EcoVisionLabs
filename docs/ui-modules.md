# UI-Module

Die Streamlit-Oberfläche in `ui/`.

## streamlit_ui.py (Main Entry)

**Zweck:** Haupteinstieg der App

**Aufgaben:**
- Initialisiert Streamlit
- Lädt alle Manager (Config, Data, Scenario)
- Zeigt Sidebar mit Navigation
- Routet zu einzelnen Pages

**Session State:**
- `dm` - DataManager Instanz
- `cfg` - ConfigManager Instanz
- `sm` - ScenarioManager Instanz
- `debug_mode` - Debug-Ausgaben an/aus

**Wichtig:**
- Lädt Daten beim ersten Start (Auto-Load)
- Cached alles in Session State
- Nur ein Reload wenn explizit gewünscht

---

## ui/home.py

**Zweck:** Startseite der App

**Inhalt:**
- Willkommensnachricht
- Quick-Start Buttons
- System-Status (geladene Daten)
- Reload-Button

**Funktionalität:**
```python
home_page(dm, cfg, sm)
```

---

## ui/analysis.py

**Zweck:** Analyse-Seite für historische Daten

**Features:**
- Zeigt Rohdaten an
- Historische Erzeugung/Verbrauch
- Vergleich verschiedener Jahre
- Daten-Export

**Use Case:**
User will wissen: "Wie viel Wind wurde 2019 erzeugt?"

---

## ui/simulation_standard.py

**Zweck:** Standard-Simulation (ein Szenario, ein Jahr)

**Workflow:**
1. User wählt Szenario
2. User wählt Jahr (2030 oder 2045)
3. Klick auf "Simulieren"
4. Zeigt alle Ergebnisse

**Ausgaben:**
- Jahresdauerlinie
- Monatssummen
- Kennzahlen (Autarkie, etc.)
- Kosten

---

## ui/simulation_diff.py

**Zweck:** Differenz zwischen Szenarien

**Use Case:**
"Was ändert sich wenn ich doppelt so viel Speicher habe?"
Für kleine Änderungen einzelner Parameter gedacht.

**Features:**
- Vergleicht einzelner Parameter
- Zeigt Unterschiede (Delta)
- Highlight der Änderungen
- Zeigt Score

---

## ui/simulation_comparison.py

**Zweck:** Vergleich mehrerer Szenarien

**Use Case:**
"Welches Szenario ist besser: S0 oder S1?"
Für komplett unterschiedliche Szenarien Gedacht

**Features:**
- Multi-Select für Szenarien
- Scoring-Übersicht

---

## ui/scenario_generation.py

**Zweck:** Eigenes Szenario erstellen

**Workflow:**
1. User startet mit Template
2. Passt Werte an (Slider, Input)
3. Preview der Auswirkungen
4. Speichern als neue YAML

**Features:**
- Validierung (negative Werte verhindern)
- Plausibilitätschecks
- Direktes Testen

---

## plotting/

**Struktur:**
```
plotting/
  - __init__.py
  - economic_plots.py    # Kosten, LCOE
  - generation_plots.py  # Erzeugungsdiagramme
  - consumption_plots.py # Verbrauchsdiagramme
  - balance_plots.py     # Residuallast, Jahresdauerlinie
  - comparison_plots.py  # Multi-Szenario-Vergleich
```

**Technologie:** Plotly (interaktiv)

**Beispiel:**
```python
from plotting.balance_plots import plot_balance_over_time

fig = plot_balance_over_time(balance_data)
st.plotly_chart(fig)
```

**Stil:**
- Einheitliche Farben (aus constants.py)
- Deutsche Labels
- Hover-Tooltips
- Zoom/Pan aktiviert
