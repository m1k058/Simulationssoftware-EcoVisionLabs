# Clean Structure Plan (Neustart in `src`)

## 1) Ist-Zustand (kurz)

Aktuell existieren **zwei Strukturen parallel**:

- `source-code/` enthält die echte App-Logik (Entry, UI, Engine, Data Processing)
- `src/` enthält nur `run_ui.py` (Stub/Platzhalter)

Wichtige Ist-Bausteine:

- Entry/UI: `source-code/streamlit_ui.py`, `source-code/ui/*`
- Core: `source-code/config_manager.py`, `source-code/data_manager.py`, `source-code/scenario_manager.py`
- Simulation: `source-code/data_processing/*`
- Plotting: `source-code/plotting/*`
- Tests referenzieren aktuell direkt `data_processing.*` (ohne Paketpräfix)

## 2) Probleme im aktuellen Aufbau

- **Doppelte Struktur** (`source-code` + `src`) erschwert Wartung.
- Viele **top-level Module** ohne saubere Paketgrenzen.
- `source-code` ist als Name mit Bindestrich unglücklich für Python-Imports.
- UI enthält Debug/Legacy-Funktionen gemischt mit Produktivfluss.
- Große „God Files“ (z. B. `plotting_plotly_st.py`, `simulation_engine.py`) sind schwer zu überblicken.

## 3) Zielbild: neue saubere Paketstruktur

Empfehlung: Ein einziges App-Paket unter `src/ecovision/`.

```text
src/
  ecovision/
    __init__.py
    app.py                         # Streamlit entry (ersetzt streamlit_ui.py)

    config/
      __init__.py
      manager.py                   # aus config_manager.py
      schema.py                    # optionale Config-Validierung (später)
      constants.py                 # domänenweite Konstanten

    data/
      __init__.py
      manager.py                   # aus data_manager.py
      io.py                        # aus io_handler.py
      catalog.py                   # optional: Dataset-IDs/Namen zentral

    scenarios/
      __init__.py
      manager.py                   # aus scenario_manager.py
      models.py                    # optionale TypedDict/Dataclasses (später)

    simulation/
      __init__.py
      engine.py                    # aus simulation_engine.py
      balance.py                   # aus balance_calculator.py
      consumption.py               # aus consumption_simulation.py
      generation.py                # aus generation_simulation.py
      storage.py                   # aus storage_simulation.py
      heatpump.py                  # aus heat_pump_simulation.py
      emobility.py                 # aus e_mobility_simulation.py
      economics.py                 # aus economic_calculator.py
      calculation_engine.py        # aus calculation_engine.py
      logging.py                   # aus simulation_logger.py
      scoring.py                   # aus scoring_system.py

    ui/
      __init__.py
      pages/
        __init__.py
        home.py
        analysis.py
        simulation_standard.py
        simulation_diff.py
        simulation_comparison.py
        scenario_generation.py
      components/
        __init__.py
        kpi_dashboard.py

    plotting/
      __init__.py
      simulation_plots.py          # aus plotting_plotly_st.py
      economic_plots.py
      scoring_plots.py

    services/
      __init__.py
      bootstrap.py                 # Initialisierung von cfg/dm/sm + session-state
      export.py                    # Excel/ZIP Export aus Engine auslagern

    shared/
      __init__.py
      types.py
      exceptions.py

src/run_ui.py                      # sehr dünner Starter, ruft ecovision.app.main()
```

## 4) Was kann raus / ersetzt werden

### Sofortige Entfallkandidaten

- `source-code/ui/step_simulation/` (leer, nur `__pycache__`)
- Doppel-Entry-Logik in `src/run_ui.py` (aktuell Stub ohne Mehrwert)

### In Produktivpfad optional entfernen

- `source-code/ui/debug_scoring.py` als eigene Seite (nur behalten, wenn aktiv genutzt)
- `render_debug_scoring_dashboard()` in `ui/home.py` (bei „clean“ eher separieren oder entfernen)

### Technische Schulden beim Umzug direkt mitnehmen

- Doppelte Imports (`import warnings` mehrfach in einzelnen Dateien)
- Einheitliche Importpfade auf Paketstil: `from ecovision...`
- Datei-/Modulnamen konsistent (z. B. `plotting_plotly_st.py` → `simulation_plots.py`)

## 5) Saubere Modulgrenzen (Empfehlung)

- `config`: nur Konfig lesen/schreiben/validieren
- `data`: nur Laden/Caching von Rohdaten
- `scenarios`: nur YAML und Szenariozugriff
- `simulation`: reine Fachlogik, keine Streamlit-Aufrufe
- `ui`: nur Darstellung + Interaktion, keine Rechenlogik
- `plotting`: reine Figure-Erstellung
- `services`: App-Orchestrierung (Bootstrap/Export)

Regel: **UI ruft Services/Simulation an, aber Simulation kennt keine UI.**

## 6) Migrationsplan (empfohlen in 6 Schritten)

1. Paketgrundlage erstellen (`src/ecovision/...`) + `__init__.py`
2. Core-Manager migrieren (`config`, `data`, `scenarios`) und Importpfade anpassen
3. Simulationsmodule migrieren (`simulation/*`) und internen Importbaum stabilisieren
4. Plotting + UI in neue Struktur schieben (`ui/pages`, `ui/components`)
5. `src/run_ui.py` als einzigen Startpunkt verdrahten (`ecovision.app.main()`)
6. Altes `source-code/` entfernen, Tests auf neue Imports anpassen

## 7) Was für „Clean v1“ bewusst *nicht* nötig ist

- Keine sofortige Komplett-Neuschreibung der Algorithmen
- Keine zusätzliche Framework-Komplexität
- Kein Over-Engineering (DI-Container etc.)

Ziel von Clean v1: **klare Struktur + stabile Funktionalität + einfache Verständlichkeit**.

## 8) Konkretes Ziel für deinen nächsten Arbeitsschritt

Als nächstes nur den **Struktur-Umzug ohne Verhaltensänderung** machen:

- gleiche Features
- gleiche Outputs
- neue saubere Ordnerstruktur
- anschließend erst fachliche Vereinfachungen
