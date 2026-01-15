# Code Review & Refactoring Plan
**Datum:** 10. Januar 2026  
**Status:** Analyse der aktuellen Codebase  
**Ziel:** Saubere, einheitliche, wartbare Struktur mit professionellem Debug-System

---

## 📊 Executive Summary

### Stärken der aktuellen Codebase
✅ Klare Modulstruktur (data_processing, ui, plotting)  
✅ Gute Trennung von Logik und UI (Streamlit in ui/)  
✅ ConfigManager/DataManager/ScenarioManager Architektur  
✅ Umfassende Test-Suite in tests/  
✅ Dokumentation in docs/  

### Kritische Probleme
⚠️ **Legacy Code:** Deprecated Funktionen noch in Verwendung  
⚠️ **Inkonsistente Debug-Ausgaben:** Mix aus print(), commented prints, simulation_logger  
⚠️ **Duplikate:** Mehrere Plotting-Module mit ähnlicher Funktionalität  
⚠️ **Fehlende Logging-Strategie:** Keine zentrale Log-Verwaltung  
⚠️ **Test-Datei im Source:** `test.py` gehört nicht in source-code/  

---

## 🗑️ LEGACY CODE - Was kann weg?

### 1. Deprecated Funktionen
**Datei:** `source-code/data_processing/simulation.py`

```python
# Zeile 47-210: calc_scaled_consumption()
# Status: DEPRECATED (siehe Docstring Zeile 51)
# Verwendet von: ui/step_simulation/steps.py (Zeile 194)
```

**Problem:**
- Alte "Top-Down" Logik
- Sollte durch `simulate_consumption_BDEW` (Bottom-Up) ersetzt werden
- Wird noch in Step-by-Step Simulation verwendet

**Empfehlung:** 
```python
# OPTION 1: Sofort entfernen
# - ui/step_simulation/steps.py auf simulate_consumption_BDEW umstellen
# - calc_scaled_consumption() + calc_scaled_consumption_multiyear() löschen

# OPTION 2: Deprecation Warning
import warnings
def calc_scaled_consumption(...):
    warnings.warn(
        "calc_scaled_consumption ist deprecated. Nutze simulate_consumption_BDEW.",
        DeprecationWarning,
        stacklevel=2
    )
    # ... alter Code
```

### 2. Test-Datei im falschen Ordner
**Datei:** `source-code/test.py`

```python
# Plotly Radar-Chart Demo (102 Zeilen)
# Gehört nicht in source-code/
```

**Empfehlung:**
```bash
# Verschieben nach:
mv source-code/test.py scratch/radar_chart_example.py
# ODER löschen, falls nicht mehr benötigt
```

### 3. Doppelte venv-Ordner
**Struktur:**
```
.venv/          # Aktiv genutzt
venv/           # Legacy? Duplicate?
```

**Empfehlung:**
```bash
# Prüfen ob venv/ noch genutzt wird
# Falls nicht: löschen
```

---

## 🔄 DUPLIKATE & REDUNDANZ

### Plotting-Module Chaos

**Aktuelle Struktur:**
```
plotting/
├── plotting.py              # Matplotlib (alt?)
├── plotting_plotly.py       # Plotly ohne Streamlit
├── plotting_plotly_st.py    # Plotly mit Streamlit
├── plotting_formated.py     # Matplotlib mit Formatierung
├── plotting_formated_st.py  # Matplotlib mit Streamlit
└── economic_plots.py        # Spezielle Wirtschafts-Plots
```

**Problem:**
- 6 Plotting-Module mit teilweise überlappender Funktionalität
- Nicht klar, welches Modul für welchen Zweck

**Empfehlung - Konsolidierung:**
```
plotting/
├── __init__.py
├── base.py                  # Basis-Klassen & Utilities
├── matplotlib_plots.py      # Alle Matplotlib (non-streamlit)
├── plotly_plots.py          # Alle Plotly (non-streamlit)
├── streamlit_plots.py       # Streamlit-spezifische Wrapper
└── economic_plots.py        # Behalten (spezifisch)
```

**Migration Plan:**
1. `plotting.py` + `plotting_formated.py` → `matplotlib_plots.py`
2. `plotting_plotly.py` → `plotly_plots.py`
3. `plotting_plotly_st.py` + `plotting_formated_st.py` → `streamlit_plots.py`

---

## 🐛 DEBUG-STRATEGIE - Aktueller Zustand

### Problem: Drei verschiedene Debug-Systeme

#### 1. Direkte print() Statements (80+ Stellen)
```python
# simulation.py
print(f"Gesamter Energieverbrauch: {formatierte_zahl} [TWh]")  # Zeile 85
print(f"Verfügbare Prognosejahre: {available_years}")          # Zeile 120

# plotting/plotting.py
print("Plot saved: {filename}")                                # Zeile 139
print(f"Error creating histogram: {e}")                        # Zeile 220
```

#### 2. Auskommentierte print() Statements (50+ Stellen)
```python
# simulation.py (Zeile 532-598)
# print(f"\n{'='*80}")
# print(f"Simuliere {type_name}:")
# print(f"Kapazität: {capacity_mwh:,.0f} MWh")
# ... 15 weitere auskommentierte prints
```

#### 3. simulation_logger.py (Teilweise genutzt)
```python
# Existiert, aber nicht konsistent verwendet
from data_processing.simulation_logger import SimulationLogger
logger = SimulationLogger()
logger.log_info("Nachricht")
```

### Problem mit st.write() in UI
```python
# Gemischt: Manchmal st.write(), manchmal st.success/info/error
st.write(f"**Simulationsjahr: {selected_year}**")  # OK für Daten
st.write("Wähle die Daten...")                     # Besser: st.info()
```

---

## ✅ REFACTORING-EMPFEHLUNGEN

### 1. Zentrales Logging-System

**Neue Datei:** `source-code/logging_config.py`

```python
import logging
import sys
from pathlib import Path

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Erstellt einen konfigurierbaren Logger.
    
    Args:
        name: Logger-Name (üblicherweise __name__)
        level: Log-Level ("DEBUG", "INFO", "WARNING", "ERROR")
    
    Returns:
        Konfigurierter Logger
    """
    logger = logging.getLogger(name)
    
    # Verhindere doppelte Handler
    if logger.handlers:
        return logger
    
    # Level setzen
    logger.setLevel(getattr(logging, level.upper()))
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger

def setup_file_logger(name: str, log_file: Path, level: str = "DEBUG") -> logging.Logger:
    """Logger mit zusätzlichem File-Output."""
    logger = setup_logger(name, level)
    
    # File Handler
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger
```

**Verwendung:**

```python
# In jedem Modul:
from logging_config import setup_logger

logger = setup_logger(__name__)

# Statt print():
logger.debug("Detaillierte Debug-Info")
logger.info("Normale Info")
logger.warning("Warnung")
logger.error("Fehler")

# Mit Session-State Steuerung:
if st.session_state.get("debug_mode", False):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
```

### 2. Einheitliche UI-Ausgaben

**Regel-Set:**

```python
# ✅ GUT - Strukturierte Ausgaben
st.success("✅ Erfolgreich geladen")
st.info("ℹ️ Wähle ein Szenario")
st.warning("⚠️ Keine Daten verfügbar")
st.error("❌ Fehler beim Laden")

# ✅ GUT - Daten-Ausgabe
st.write(f"**Simulationsjahr:** {year}")
st.metric("Verbrauch", "450 TWh", "15%")

# ❌ VERMEIDEN - Unstrukturiert
st.write("Wähle die Daten für die Simulation aus.")  # → st.info()
print("Daten geladen")  # → logger.info() oder st.success()
```

### 3. Debug-Mode Integration

**In streamlit_ui.py:**

```python
def ensure_base_session_state() -> None:
    defaults = {
        "dm": None,
        "cfg": None,
        "sm": None,
        "load_log": "",
        "debug_mode": False,
        "log_level": "INFO",  # NEU
        "auto_load_attempted": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Log-Level setzen basierend auf debug_mode
    import logging
    if st.session_state.debug_mode:
        logging.getLogger().setLevel(logging.DEBUG)
        st.session_state.log_level = "DEBUG"
    else:
        logging.getLogger().setLevel(logging.INFO)
        st.session_state.log_level = "INFO"
```

**In home.py:**

```python
# Debug-Mode mit Log-Level Auswahl
col1, col2 = st.columns([1, 1])
with col1:
    debug = st.checkbox("🐛 Debug Modus", value=st.session_state.debug_mode, key="debug_mode")
with col2:
    if debug:
        log_level = st.selectbox(
            "Log-Level",
            ["DEBUG", "INFO", "WARNING", "ERROR"],
            index=["DEBUG", "INFO", "WARNING", "ERROR"].index(st.session_state.log_level)
        )
        st.session_state.log_level = log_level
```

### 4. Datenstruktur-Konsistenz

**Problem:** Inkonsistente Dict-Keys

```python
# simulation.py verwendet manchmal:
hp_config.get("weather_data")
hp_config.get("installed_units")

# scenario_manager.py verwendet:
scenario.get("target_heat_pump_parameters")
scenario.get("target_load_demand_twh")

# Empfehlung: Pydantic Models für Type-Safety
```

**Lösung mit Pydantic:**

```python
# source-code/models.py (NEU)
from pydantic import BaseModel, Field
from typing import Dict, Optional

class HeatPumpParameters(BaseModel):
    capacity_gw: float = Field(gt=0, description="Kapazität in GW")
    installed_units: int = Field(ge=0, description="Anzahl Wärmepumpen")
    cop_avg: float = Field(gt=0, le=5, description="COP Durchschnitt")
    weather_data: str = Field(description="Name des Wetterdatensatzes")

class ScenarioConfig(BaseModel):
    scenario_name: str
    valid_for_years: list[int]
    target_heat_pump_parameters: Dict[int, HeatPumpParameters]
    # ... weitere Felder
    
    class Config:
        extra = "allow"  # Erlaube zusätzliche Felder
```

---

## 📁 EMPFOHLENE ORDNER-STRUKTUR

### Vorher (Aktuell):
```
source-code/
├── config.json
├── test.py                      # ❌ Gehört nicht hier
├── config_manager.py
├── data_manager.py
├── scenario_manager.py
├── constants.py
├── io_handler.py
├── streamlit_ui.py
├── data_processing/
│   ├── simulation.py            # 1930 Zeilen! ⚠️
│   ├── load_profile.py
│   ├── generation_profile.py
│   ├── economic_calculator.py
│   ├── simulation_logger.py     # Nicht konsistent genutzt
│   ├── col.py
│   └── gen.py
├── plotting/
│   ├── plotting.py              # ⚠️ Duplikat
│   ├── plotting_plotly.py       # ⚠️ Duplikat
│   ├── plotting_plotly_st.py    # ⚠️ Duplikat
│   ├── plotting_formated.py     # ⚠️ Duplikat
│   ├── plotting_formated_st.py  # ⚠️ Duplikat
│   └── economic_plots.py
└── ui/
    ├── home.py
    ├── simulation_standard.py
    ├── simulation_diff.py
    ├── scenario_generation.py
    ├── analysis.py
    └── step_simulation/
        └── steps.py             # Nutzt deprecated calc_scaled_consumption
```

### Nachher (Vorgeschlagen):
```
source-code/
├── config.json
├── constants.py
├── logging_config.py            # ✅ NEU - Zentrales Logging
├── models.py                    # ✅ NEU - Pydantic Models
├── streamlit_ui.py
│
├── core/                        # ✅ NEU - Kern-Manager
│   ├── __init__.py
│   ├── config_manager.py
│   ├── data_manager.py
│   └── scenario_manager.py
│
├── data_processing/
│   ├── __init__.py
│   ├── simulation/              # ✅ Simulation aufgeteilt
│   │   ├── __init__.py
│   │   ├── consumption.py       # BDEW-Verbrauchssimulation
│   │   ├── generation.py        # Erzeugungs-Profile
│   │   ├── heatpump.py          # Wärmepumpen-Simulation
│   │   └── storage.py           # Speicher-Simulation
│   ├── profiles/
│   │   ├── __init__.py
│   │   ├── load_profile.py
│   │   └── generation_profile.py
│   ├── economic_calculator.py
│   ├── col.py                   # Umbenennen → column_utils.py
│   └── gen.py                   # Umbenennen → generation_utils.py
│
├── io/                          # ✅ NEU - I/O Operations
│   ├── __init__.py
│   └── io_handler.py
│
├── plotting/
│   ├── __init__.py
│   ├── base.py                  # ✅ Basis-Klassen
│   ├── matplotlib_plots.py      # ✅ Konsolidiert
│   ├── plotly_plots.py          # ✅ Konsolidiert
│   ├── streamlit_plots.py       # ✅ Konsolidiert
│   └── economic_plots.py
│
└── ui/
    ├── __init__.py
    ├── home.py
    ├── simulation_standard.py
    ├── simulation_diff.py
    ├── scenario_generation.py
    └── analysis.py
    # step_simulation/ wird deprecated (nutzt alte Logik)
```

---

## 🔧 MIGRATIONS-PLAN (Priorität)

### Phase 1: KRITISCH - Sofortige Verbesserungen (1-2 Tage)

#### 1.1 Logging-System implementieren
- [ ] `logging_config.py` erstellen
- [ ] In allen Modulen implementieren (schrittweise)
- [ ] `simulation_logger.py` deprecated markieren
- [ ] Alle `print()` zu `logger.debug/info()` ändern

#### 1.2 Legacy Code entfernen/deprecaten
- [ ] `test.py` nach `scratch/` verschieben
- [ ] `calc_scaled_consumption()` deprecated Warning hinzufügen
- [ ] Step-by-Step Simulation analysieren (verwendet Legacy)

#### 1.3 Debug-Mode Integration
- [ ] Log-Level Auswahl in UI
- [ ] Debug-Ausgaben über session_state.debug_mode steuern

### Phase 2: WICHTIG - Strukturverbesserungen (3-5 Tage)

#### 2.1 Plotting-Module konsolidieren
- [ ] `base.py` mit gemeinsamen Utilities erstellen
- [ ] Matplotlib-Module zusammenführen
- [ ] Plotly-Module zusammenführen
- [ ] Streamlit-Wrapper konsolidieren
- [ ] Alte Module als deprecated markieren

#### 2.2 simulation.py aufteilen (1930 Zeilen!)
- [ ] `consumption.py` extrahieren (BDEW-Logik)
- [ ] `heatpump.py` extrahieren
- [ ] `storage.py` extrahieren
- [ ] `generation.py` extrahieren

#### 2.3 Pydantic Models einführen
- [ ] `models.py` erstellen
- [ ] ScenarioConfig implementieren
- [ ] HeatPumpParameters implementieren
- [ ] Migration in config_manager/scenario_manager

### Phase 3: OPTIONAL - Architektur (5-7 Tage)

#### 3.1 Ordner-Umstrukturierung
- [ ] `core/` Ordner erstellen
- [ ] `io/` Ordner erstellen
- [ ] `simulation/` Unterordner
- [ ] Imports aktualisieren

#### 3.2 Tests aktualisieren
- [ ] Tests an neue Struktur anpassen
- [ ] Neue Tests für Logging
- [ ] Integration-Tests erweitern

#### 3.3 Dokumentation
- [ ] README aktualisieren
- [ ] API-Dokumentation (Sphinx?)
- [ ] Migration-Guide für Nutzer

---

## 📊 CODE-QUALITÄT METRIKEN

### Aktuelle Messungen:

| Metrik | Wert | Ziel | Status |
|--------|------|------|--------|
| Größte Datei | simulation.py (1930 Zeilen) | < 500 Zeilen | ❌ |
| Anzahl Plotting-Module | 6 | 3-4 | ⚠️ |
| TODO/FIXME | 3 | 0 | ⚠️ |
| Deprecated Functions | 2 | 0 | ❌ |
| Print Statements | 80+ | 0 (nutze logger) | ❌ |
| Auskommentierte Debug-Prints | 50+ | 0 | ❌ |
| Test Coverage | ? | > 80% | ❓ |

---

## 🎯 QUICK WINS (Sofort umsetzbar)

### 1. Kommentierte Prints entfernen
```python
# Alle # print(...) löschen in simulation.py (50+ Zeilen)
# Entweder aktivieren mit logger oder ganz entfernen
```

### 2. test.py verschieben
```bash
mv source-code/test.py scratch/radar_chart_example.py
```

### 3. Deprecated Warnings hinzufügen
```python
# simulation.py
def calc_scaled_consumption(...):
    import warnings
    warnings.warn(
        "calc_scaled_consumption ist deprecated. Nutze simulate_consumption_BDEW.",
        DeprecationWarning,
        stacklevel=2
    )
    # ... Rest des Codes
```

### 4. st.write() zu strukturierten Ausgaben ändern
```python
# Vorher:
st.write("Wähle die Daten für die Simulation aus.")

# Nachher:
st.info("ℹ️ Wähle die Daten für die Simulation aus.")
```

### 5. Debug-Mode Log-Level
```python
# home.py - Erweitere Debug-Checkbox:
if st.checkbox("🐛 Debug Modus", value=False, key="debug_mode"):
    st.selectbox("Log-Level", ["DEBUG", "INFO", "WARNING", "ERROR"])
```

---

## 📝 CODING STANDARDS (Für die Zukunft)

### Python Style Guide
```python
# 1. Imports gruppieren
import sys  # Standard library
import warnings

import pandas as pd  # Third-party
import numpy as np
import streamlit as st

from config_manager import ConfigManager  # Local imports
from logging_config import setup_logger

# 2. Logger am Modulanfang
logger = setup_logger(__name__)

# 3. Type Hints verwenden
def simulate_consumption(
    year: int,
    target_twh: float,
    profile_name: str
) -> pd.DataFrame:
    """Simuliert Verbrauch für ein Jahr."""
    ...

# 4. Docstrings mit Google Style
def example_function(param1: str, param2: int) -> bool:
    """
    Kurze Beschreibung.
    
    Längere Beschreibung falls nötig.
    
    Args:
        param1: Beschreibung Parameter 1
        param2: Beschreibung Parameter 2
    
    Returns:
        True wenn erfolgreich, sonst False
    
    Raises:
        ValueError: Wenn param2 < 0
    """
    ...

# 5. Konstanten in UPPERCASE
MAX_CAPACITY = 1000
DEFAULT_YEAR = 2030

# 6. Private Functions mit _
def _internal_helper():
    """Interne Hilfsfunktion."""
    ...
```

### Logging Best Practices
```python
# ✅ GUT
logger.debug(f"Verarbeite Daten für Jahr {year}")
logger.info("Simulation abgeschlossen")
logger.warning(f"Keine Daten für {sector} gefunden")
logger.error(f"Fehler beim Laden: {e}", exc_info=True)

# ❌ VERMEIDEN
print("Debug: Processing...")
print(f"ERROR: {e}")
st.write(f"Info: {message}")  # Nutze st.info()
```

### UI Best Practices (Streamlit)
```python
# ✅ GUT - Strukturiert
st.success("✅ Erfolgreich")
st.info("ℹ️ Information")
st.warning("⚠️ Warnung")
st.error("❌ Fehler")

# ✅ GUT - Daten
st.metric("Verbrauch", "450 TWh", delta="15%")
st.dataframe(df, use_container_width=True)

# ❌ VERMEIDEN - Unstrukturiert
st.write("Info: ...")  # Nutze st.info()
st.write(f"Error: ...")  # Nutze st.error()
```

---

## 🔍 NÄCHSTE SCHRITTE

### Sofort (diese Woche):
1. ✅ Dieses Dokument mit dir besprechen
2. [ ] Entscheidung: Welche Phase zuerst?
3. [ ] Quick Wins umsetzen (1-2h)
4. [ ] Logging-System implementieren (4-6h)

### Kurzfristig (nächste 2 Wochen):
1. [ ] Plotting-Module konsolidieren
2. [ ] simulation.py aufteilen
3. [ ] Legacy Code entfernen

### Mittelfristig (nächster Monat):
1. [ ] Pydantic Models einführen
2. [ ] Ordner-Umstrukturierung
3. [ ] Test Coverage erhöhen

---

## 💡 EMPFEHLUNG

**Priorität 1 - Starte mit:**
1. **Logging-System** (logging_config.py) - Fundamentale Verbesserung
2. **Quick Wins** (test.py verschieben, deprecated warnings) - Sofortige Sauberkeit
3. **Debug-Mode Integration** - Bessere User Experience

**Warum diese Reihenfolge?**
- Logging ist die Basis für alle weiteren Verbesserungen
- Quick Wins zeigen sofort Fortschritt
- Debug-Mode macht weitere Arbeiten einfacher

**Danach:**
- Plotting-Module konsolidieren (größter Duplikations-Gewinn)
- simulation.py aufteilen (Wartbarkeit)
- Ordner-Struktur optimieren (Langfristige Architektur)

---

## ❓ FRAGEN ZUR ENTSCHEIDUNG

1. **Wie wichtig ist dir die Step-by-Step Simulation?**
   - Falls wichtig → auf neue Logik migrieren
   - Falls unwichtig → deprecated lassen oder entfernen

2. **Welche Plotting-Library ist primär?**
   - Plotly (interaktiv, modern) → Fokus auf Plotly
   - Matplotlib (statisch, bekannt) → Fokus auf Matplotlib
   - Beide → Beide behalten, aber sauber trennen

3. **Logging-Dateien gewünscht?**
   - Ja → File-Handler in logging_config.py aktivieren
   - Nein → Nur Console-Output

4. **Test Coverage Ziel?**
   - 80%+ → Viel Test-Arbeit
   - 60%+ → Moderate Tests
   - < 50% → Aktuell beibehalten

---

**Was möchtest du als erstes anpacken?** 🚀
