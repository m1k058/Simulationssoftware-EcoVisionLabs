# Cleanup Summary - Deprecated Code Entfernung & UI-Update

## Datum: 2024-01-XX

## Übersicht
Vollständige Bereinigung der Codebase: Entfernung aller deprecated Funktionen, Wrapper-Funktionen und Umbenennung von SimulationOrchestrator → SimulationEngine.

---

## 1. Datei-Umbenennungen

### simulation_orchestrator.py → simulation_engine.py
- **Alter Pfad**: `source-code/data_processing/simulation_orchestrator.py`
- **Neuer Pfad**: `source-code/data_processing/simulation_engine.py`
- **Begründung**: Bessere Namensgebung - "Engine" beschreibt die Rolle als zentrale Koordinationskomponente genauer

### simulation.py → Komplett neugeschrieben
- **Vorher**: 1,936 Zeilen (monolithischer God Object)
- **Nachher**: ~700 Zeilen (4 Kern-Funktionen)
- **Reduktion**: ~65% weniger Code

---

## 2. Entfernte Funktionen aus simulation.py

### Deprecated Funktionen (komplett entfernt)
1. ✅ `calc_scaled_consumption()` - Ersetzt durch `simulate_consumption_all()`
2. ✅ `calc_scaled_consumption_multiyear()` - Ersetzt durch `simulate_consumption_all()` mit Jahr-Parameter
3. ✅ `calc_scaled_production_multiyear()` - Duplikat entfernt

### Wrapper-Funktionen (komplett entfernt)
1. ✅ `simulate_battery_storage()` - Wrapper für StorageSimulation.simulate_battery_storage()
2. ✅ `simulate_pump_storage()` - Wrapper für StorageSimulation.simulate_pump_storage()
3. ✅ `simulate_hydrogen_storage()` - Wrapper für StorageSimulation.simulate_hydrogen_storage()
4. ✅ `simulate_consumption_heatpump()` - Wrapper für HeatPumpSimulation.simulate()
5. ✅ `calc_balance()` - Wrapper für BalanceCalculator.calculate_balance()
6. ✅ `kobi()` - Wrapper für SimulationEngine.run_scenario()

---

## 3. Behaltene Kern-Funktionen in simulation.py

Diese 4 Funktionen bilden das Kern-API:

### 1. `simulate_production()`
- **Zweck**: Erzeugungssimulation basierend auf SMARD-Daten
- **Input**: ConfigManager, SMARD-Daten, Zielkapazitäten, Wetterprofil
- **Output**: DataFrame mit Erzeugung für alle Technologien [MWh]

### 2. `simulate_consumption_BDEW()`
- **Zweck**: BDEW-Lastprofile (H25, G25, L25) skalieren
- **Input**: BDEW-Profile, Zielwerte [TWh], Simulationsjahr
- **Output**: DataFrame mit Verbrauch Haushalte/Gewerbe/Landwirtschaft [MWh]

### 3. `simulate_consumption_all()`
- **Zweck**: Kompletter Verbrauch (BDEW + Wärmepumpen)
- **Input**: BDEW-Profile, Wärmepumpen-Parameter, Wetterdaten
- **Output**: DataFrame mit Gesamtverbrauch [MWh]

### 4. `economical_calculation()`
- **Zweck**: Wirtschaftlichkeitsanalyse (CAPEX/OPEX/LCOE)
- **Input**: ScenarioManager, DataManager, Simulationsergebnisse, Jahr
- **Output**: Dictionary mit Investitionskosten, Betriebskosten, LCOE

---

## 4. SimulationEngine Updates

### Imports bereinigt
**Entfernt**:
- `SimulationLogger` (alte Implementierung)
- `generation_profile` (nicht direkt benötigt)
- `load_profile` (nicht benötigt)
- `constants.HEATPUMP_LOAD_PROFILE_NAME`

**Hinzugefügt**:
- `_SimpleLogger` (neue interne Implementierung)
- Direkte Imports aus `simulation.py`

### Klasseninitialisierung vereinfacht
**Vorher**:
```python
self.storage_sim = StorageSimulation(logger=self.logger)
self.heatpump_sim = HeatPumpSimulation(logger=self.logger)
self.balance_calc = BalanceCalculator(logger=self.logger)
```

**Nachher**:
```python
self.storage_sim = StorageSimulation()
self.heatpump_sim = HeatPumpSimulation()
self.balance_calc = BalanceCalculator()
```
→ Logger nicht mehr als Dependency (saubere Trennung)

### _simulate_consumption() vereinfacht
**Vorher**: 50 Zeilen (separate BDEW + WP Schritte)
**Nachher**: 30 Zeilen (nutzt `simulate_consumption_all()` direkt)

---

## 5. UI-Updates

### simulation_standard.py
**Vorher (Zeile 292)**:
```python
st.session_state.fullSimResults = simu.kobi(
    st.session_state.cfg,
    st.session_state.dm,
    st.session_state.sm
)
```

**Nachher**:
```python
engine = SimulationEngine(
    st.session_state.cfg,
    st.session_state.dm,
    st.session_state.sm
)
st.session_state.fullSimResults = engine.run_scenario()
```

**Import-Änderung**:
```python
# Vorher
import data_processing.simulation as simu

# Nachher
from data_processing.simulation_engine import SimulationEngine
```

### simulation_diff.py
**Vorher (Zeile 102)**:
```python
results = simu.kobi(
    st.session_state.cfg,
    st.session_state.dm,
    st.session_state.sm
)
```

**Nachher**:
```python
engine = SimulationEngine(
    st.session_state.cfg,
    st.session_state.dm,
    st.session_state.sm
)
results = engine.run_scenario()
```

**Import-Änderung**:
```python
# Vorher
import data_processing.simulation as simu

# Nachher
from data_processing.simulation_engine import SimulationEngine
```

---

## 6. Neue Architektur

```
SimulationEngine (simulation_engine.py)
├── run_scenario()
│   ├── _load_base_data()
│   └── für jedes Jahr:
│       ├── _simulate_consumption() → simulation.simulate_consumption_all()
│       ├── _simulate_production() → simulation.simulate_production()
│       ├── _calculate_balance() → BalanceCalculator.calculate_balance()
│       ├── _simulate_storage() → StorageSimulation.simulate_*()
│       └── _calculate_economics() → simulation.economical_calculation()
│
Kern-Funktionen (simulation.py)
├── simulate_production()
├── simulate_consumption_BDEW()
├── simulate_consumption_all()
└── economical_calculation()

Spezialisierte Module
├── StorageSimulation (storage_simulation.py)
├── HeatPumpSimulation (heat_pump_simulation.py)
└── BalanceCalculator (balance_calculator.py)
```

---

## 7. Vorteile der neuen Struktur

### Code-Qualität
- ✅ **-65% Code in simulation.py** (1,936 → 700 Zeilen)
- ✅ **Keine Duplikate mehr** (calc_scaled_production_multiyear entfernt)
- ✅ **Keine Wrapper mehr** (direkte Modulverwendung)
- ✅ **Keine deprecated Funktionen** (vollständig entfernt)

### Wartbarkeit
- ✅ **Klare Verantwortlichkeiten**: Jedes Modul hat eine Aufgabe
- ✅ **Testbarkeit**: Kleine Funktionen sind einfacher zu testen
- ✅ **Dokumentation**: Jede Funktion hat klare Docstrings

### Performance
- ✅ **Weniger Indirektion**: UI ruft Engine direkt auf
- ✅ **Keine unnötigen Wrapper-Aufrufe**
- ✅ **Optimierte Imports**: Nur was benötigt wird

---

## 8. Breaking Changes

### Für externe Nutzer (falls vorhanden)
1. ❌ `simu.kobi()` existiert nicht mehr → Nutze `SimulationEngine.run_scenario()`
2. ❌ Alle Wrapper-Funktionen entfernt → Nutze Module direkt
3. ❌ `calc_scaled_consumption()` entfernt → Nutze `simulate_consumption_all()`

### Migration Guide
```python
# ALT
import data_processing.simulation as simu
results = simu.kobi(cfg, dm, sm)

# NEU
from data_processing.simulation_engine import SimulationEngine
engine = SimulationEngine(cfg, dm, sm)
results = engine.run_scenario()
```

---

## 9. Testing

### Manuelle Tests erforderlich
1. ⚠️ **Standard-Simulation**: UI → Simulation starten → Ergebnisse prüfen
2. ⚠️ **Diff-Mode**: Zwei Szenarien laden → Interpolation → Vergleich
3. ⚠️ **Wirtschaftlichkeit**: LCOE-Berechnung validieren
4. ⚠️ **Speicher**: Batterie/Pumpspeicher/H2-Simulation prüfen

### Bekannte Risiken
- **Logger**: `_SimpleLogger` ersetzt `SimulationLogger` → Logging-Format kann abweichen
- **UI-State**: Session State muss korrekt umgewandelt werden
- **Error Handling**: Exception-Messages können sich geändert haben

---

## 10. Nächste Schritte

### Sofort
1. ✅ Tests durchführen: UI starten und Szenarien durchlaufen
2. ✅ Logging überprüfen: Sind alle wichtigen Infos sichtbar?
3. ✅ Error-Handling testen: Wie verhält sich die App bei Fehlern?

### Mittelfristig
1. Unit-Tests für Kern-Funktionen schreiben
2. Integration-Tests für SimulationEngine
3. Performance-Benchmarks (vorher/nachher Vergleich)

### Optional
1. `_SimpleLogger` durch strukturiertes Logging ersetzen (z.B. Python logging module)
2. Type Hints für alle Funktionen hinzufügen
3. Docstrings erweitern (Beispiele, Fehlerbehandlung)

---

## 11. Dateien geändert

| Datei | Änderung | Zeilen Vorher | Zeilen Nachher |
|-------|----------|---------------|----------------|
| `simulation.py` | Komplette Neufassung | 1,936 | ~700 |
| `simulation_orchestrator.py` | Umbenannt → simulation_engine.py | 450 | 413 |
| `simulation_engine.py` | Imports + Logger aktualisiert | 450 | 413 |
| `simulation_standard.py` | Import + kobi() ersetzt | 512 | 512 |
| `simulation_diff.py` | Import + kobi() ersetzt | 557 | 557 |

**Gesamt**: ~1,200 Zeilen Code entfernt, Architektur gestrafft

---

## 12. Commit Message Vorschlag

```
refactor: Complete cleanup - remove deprecated code and update UI

BREAKING CHANGE: Remove all wrapper functions and deprecated code from simulation.py

- Rename: simulation_orchestrator.py → simulation_engine.py
- Remove: kobi(), calc_scaled_consumption(), all storage/hp/balance wrappers
- Keep: 4 core functions (simulate_production, simulate_consumption_*, economical_calculation)
- Update: UI files to use SimulationEngine directly instead of wrappers
- Simplify: Logger implementation (_SimpleLogger replaces SimulationLogger)
- Result: -65% code in simulation.py (1,936 → 700 lines)

Migration: Replace `simu.kobi()` with `SimulationEngine().run_scenario()`
```

---

## 13. Anmerkungen

- ✅ **Keine Syntax-Errors**: Alle Dateien kompilieren fehlerfrei
- ✅ **Keine Import-Errors**: Alle Abhängigkeiten aufgelöst
- ⚠️ **Funktionalitäts-Tests ausstehend**: Manuelle Tests erforderlich
- 📝 **Dokumentation aktualisiert**: Dieses Dokument + docstrings in Code

---

**Erstellt von**: GitHub Copilot  
**Review erforderlich**: Ja (manuelle Funktionstests)  
**Status**: Bereit für Testing
