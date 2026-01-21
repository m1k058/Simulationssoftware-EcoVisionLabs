# Architektur-Übersicht

Grundlegende Struktur der Software.

## Komponenten

```
streamlit_ui.py (Entry Point)
    |
    |-- ConfigManager (Lädt config.json)
    |-- DataManager (Lädt CSVs aus raw-data/)
    |-- ScenarioManager (Lädt YAMLs aus scenarios/)
    |
    |-- SimulationEngine
            |
            |-- generation_simulation (Wind, Solar, etc.)
            |-- consumption_simulation (Verbrauchsprofile)
            |-- e_mobility_simulation (E-Autos)
            |-- heat_pump_simulation (Wärmepumpen)
            |-- storage_simulation (Batterien, Wasserstoff)
            |-- balance_calculator (Angebot vs Nachfrage)
            |-- economic_calculator (Kosten, Emissionen)
            |
            |-- Results
                    |
                    |-- plotting/ (Visualisierung)
```

## Datenfluss

1. **Initialisierung**
   - ConfigManager liest `config.json`
   - DataManager lädt alle CSV-Dateien
   - ScenarioManager lädt Standard-Szenario

2. **Simulation**
   - User wählt Szenario und Jahr (2030/2045)
   - SimulationEngine ruft alle Simulationsmodule auf
   - Jedes Modul berechnet Zeitreihen (8760h)
   - balance_calculator summiert alles

3. **Visualisierung**
   - Plotting-Module bekommen Ergebnisse
   - Erstellen interaktive Plotly-Diagramme
   - Streamlit zeigt Diagramme an

## Design-Entscheidungen

**Warum CSVs?**
- Einfach zu editieren
- Einfach einzulesen
- Keine Datenbank nötig

**Warum YAMLs für Szenarien?**
- Lesbar für Menschen
- Versionierbar
- Einfaches Format

**Warum Streamlit?**
- Schnell Prototypen bauen
- Automatisches Reloading
- Kein Frontend-Code nötig

**Warum Numba?**
- Simulation ist rechenintensiv
- getestete Beschleunigung: x20
