# Core-Module

Die zentralen Verwaltungskomponenten.

## config_manager.py

**Zweck:** Lädt und verwaltet `config.json`

**Hauptaufgaben:**
- Definiert Pfade zu Rohdaten (CSV-Dateien)
- Speichert globale Settings (z.B. max_datasets)
- Mapping zwischen Datenbank-IDs und Dateien

**Wichtige Methoden:**
```python
cfg = ConfigManager()
dataset_path = cfg.get_dataset_path(10)  # Gibt Pfad zu Dataset 10
value = cfg.get_global("max_datasets")    # Globale Config
```

**Wann nutzen?**
Wenn du neue Rohdaten einbinden willst, musst du sie in `config.json` registrieren.

---

## data_manager.py

**Zweck:** Lädt alle CSV-Dateien beim Start

**Hauptaufgaben:**
- Lädt CSVs aus `raw-data/`
- Cached DataFrames im RAM
- Stellt Daten für Simulationen bereit

**Wichtige Methoden:**
```python
dm = DataManager(config_manager=cfg)
df = dm.get(10)  # Gibt DataFrame mit ID 10
df = dm.get_by_name("Lufttemperatur-2019")  # By Name
```

**Performance:**
- Lädt alle Daten beim Start (dauert 2-5 Sekunden)
- Danach schneller Zugriff (RAM-cached)

**Wann nutzen?**
Alle Simulationsmodule nutzen DataManager um an Rohdaten zu kommen.

---

## scenario_manager.py

**Zweck:** Verwaltet Szenario-Konfigurationen (YAML)

**Hauptaufgaben:**
- Lädt Szenarien aus `scenarios/`
- Validiert Szenario-Struktur
- Speichert neue Szenarien

**Wichtige Methoden:**
```python
sm = ScenarioManager()
scenarios = sm.list_scenarios()           # Alle verfügbaren
scenario = sm.load_scenario("S0_...")    # Lade Szenario
sm.save_scenario(data, "MyScenario")     # Speichere neues
```

**Szenario-Struktur:**
```yaml
metadata:
  name: "Beispiel"
  valid_for_years: [2030, 2045]
  
target_load_demand_twh:
  Haushalt_Basis: {2030: 130, 2045: 120}
  
target_generation_capacities_mw:
  Photovoltaik: {2030: 215000, 2045: 400000}
```

**Wann nutzen?**
Wenn User ein Szenario auswählt oder ein eigenes erstellt.

---

## constants.py

**Zweck:** Zentrale Konstanten und Konfigurationswerte

**Inhalt:**
- Zeitreihen-Länge (8760 Stunden)
- Umrechnungsfaktoren (TWh zu MWh)
- Standard-Farben für Plots
- Technologie-Namen

**Beispiel:**
```python
from constants import HOURS_PER_YEAR, TWH_TO_MWH

hours = HOURS_PER_YEAR  # 8760
factor = TWH_TO_MWH     # 1e6
```

**Wann nutzen?**
Standarisierung

---

## io_handler.py

**Zweck:** CSV-Dateien einlesen (Low-Level)

**Hauptaufgaben:**
- Einheitliches CSV-Parsing
- Error-Handling bei fehlenden Dateien
- Encoding-Detection

**Wann nutzen?**
Normalerweise nicht direkt - DataManager nutzt es intern.
