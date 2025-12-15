# Tests

Dieser Ordner enthält alle Unit- und Integrationstests für die Simulationssoftware.

## Test-Dateien

### Konfiguration & Datenverarbeitung
- **`test_config_manager.py`** - Tests für ConfigManager (Konfigurationsverwaltung)
- **`test_load_profile_calculation.py`** - Tests für Lastprofil-Berechnungen
- **`test_load_profile_detail.py`** - Detaillierte Tests für Lastprofil-Details
- **`test_load_profile_integration.py`** - Integrationstests für Lastprofile
- **`test_summengleichheit.py`** - Tests zur Validierung von Summengleichheit

### Verbrauchssimulation (simulate_consumption)
- **`test_consumption_simulation_full.py`** - Vollständiger Test mit Export für beide Jahre (2030, 2045)
- **`test_consumption_holidays.py`** - Test für korrekte Feiertagserkennung mit holidays Package
- **`test_consumption_validation.py`** - Detaillierte Validierung (Schaltjahre, fehlende Werte, etc.)

## Tests ausführen

### Alle Tests ausführen
```bash
pytest tests/
```

### Einzelner Test
```bash
python tests/test_consumption_simulation_full.py
```

### Mit Coverage
```bash
pytest tests/ --cov=source-code --cov-report=html
```

## Anforderungen

Stelle sicher, dass alle Dependencies installiert sind:
```bash
pip install -r requirements.txt
pip install holidays  # Für Feiertagstests
```
