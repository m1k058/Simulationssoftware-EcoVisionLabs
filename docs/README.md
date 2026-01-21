# Dokumentation

Übersicht über die Software-Architektur und Module.

## Inhaltsverzeichnis

- [Architektur-Übersicht](architecture.md) - Wie die Module zusammenspielen
- [Core-Module](core-modules.md) - Zentrale Verwaltungskomponenten
- [Simulationsmodule](simulation-modules.md) - Einzelne Berechnungsmodule
- [UI-Module](ui-modules.md) - Streamlit-Oberfläche

## Schnelleinstieg

**Was macht was?**
- `streamlit_ui.py` - Haupteinstieg, startet die Web-App
- `data_manager.py` - Lädt und verwaltet CSV-Daten
- `scenario_manager.py` - Lädt und speichert YAML-Szenarien
- `simulation_engine.py` - Koordiniert alle Berechnungen
- `plotting/` - Alle Visualisierungen

**Typischer Ablauf:**
1. User startet App (`streamlit_ui.py`)
2. DataManager lädt CSV-Rohdaten
3. ScenarioManager lädt Szenario (z.B. S0_Balanced_Reference)
4. SimulationEngine berechnet Ergebnisse
5. Plotting-Module erstellen Diagramme

