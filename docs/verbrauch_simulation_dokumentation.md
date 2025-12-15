# Verbrauchssimulation - Dokumentation

## Implementierung der `simulate_consumption` Funktion

### Überblick
Die neue `simulate_consumption` Funktion in `source-code/data_processing/simulation.py` implementiert die in `docs/technische_planung.md` beschriebene Verbrauchssimulation basierend auf BDEW-Standardlastprofilen.

### Funktionsweise

1. **Lastprofile**: Verwendet die BDEW-Standardlastprofile für:
   - **H25**: Haushalte
   - **G25**: Gewerbe
   - **L25**: Landwirtschaft

2. **Kalenderlogik**: Erstellt einen vollständigen Jahreskalender mit:
   - **WT** (Werktage): Montag-Freitag
   - **SA** (Samstage): Samstag
   - **FT** (Feiertage): Sonntage + deutsche Feiertage

3. **Skalierung**: 
   - Berechnet Skalierungsfaktoren, sodass die Jahressummen exakt den Zielwerten entsprechen
   - Erhält die charakteristischen Lastgänge der Profile

4. **Ausgabe**: DataFrame mit Viertelstunden-Auflösung (35.040 Datenpunkte pro Jahr)

### Verwendung

```python
from io_handler import load_data
from data_processing.simulation import simulate_consumption

# Lastprofile laden
lastH = load_data("raw-data/BDEW-Standardlastprofile-H25.csv", datatype="BDEW-Last")
lastG = load_data("raw-data/BDEW-Standardlastprofile-G25.csv", datatype="BDEW-Last")
lastL = load_data("raw-data/BDEW-Standardlastprofile-L25.csv", datatype="BDEW-Last")

# Simulation durchführen
df = simulate_consumption(
    lastH=lastH,
    lastG=lastG,
    lastL=lastL,
    lastZielH=130.0,  # TWh
    lastZielG=150.0,  # TWh
    lastZielL=20.0,   # TWh
    simu_jahr=2030
)
```

### Ausgabeformat

Der zurückgegebene DataFrame enthält folgende Spalten:

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `Zeitpunkt` | datetime | Zeitstempel (15-Minuten-Auflösung) |
| `Haushalte [MWh]` | float | Verbrauch Haushalte in MWh |
| `Gewerbe [MWh]` | float | Verbrauch Gewerbe in MWh |
| `Landwirtschaft [MWh]` | float | Verbrauch Landwirtschaft in MWh |
| `Gesamt [MWh]` | float | Gesamtverbrauch in MWh |

### Features

✅ **Automatische Komma→Punkt Konvertierung**: CSV-Werte werden korrekt verarbeitet  
✅ **Jahreszahlen-Anpassung**: Zeitstempel werden auf das Simulationsjahr angepasst  
✅ **Validierung**: Ausgabe zeigt Soll/Ist-Vergleich der Jahressummen  
✅ **Performance-optimiert**: Verwendet pandas merge statt Schleifen  
✅ **Flexible Feiertage**: Optional mit `holidays` Package für präzise Feiertage  

### Test

Vollständiger Test mit Beispielwerten:

```bash
python test_final.py
```

Erzeugt CSV-Dateien in `output/csv/`:
- `Verbrauch_Simulation_2030.csv`
- `Verbrauch_Simulation_2045.csv`

### Validierung

Die Funktion zeigt nach der Simulation automatisch eine Validierung:

```
============================================================
VALIDIERUNG DER SIMULATION
============================================================
Haushalte:       130.0000 TWh (Ziel: 130.0000 TWh, Abweichung: 0.000000 TWh)
Gewerbe:         150.0000 TWh (Ziel: 150.0000 TWh, Abweichung: 0.000000 TWh)
Landwirtschaft:  20.0000 TWh (Ziel: 20.0000 TWh, Abweichung: 0.000000 TWh)
GESAMT:          300.0000 TWh (Ziel: 300.0000 TWh)
============================================================
```

### Integration

Die Funktion kann direkt in bestehende Workflows integriert werden und ist kompatibel mit:
- `config_manager.py`
- `data_manager.py`
- `io_handler.py`
- Bestehenden Plotting-Funktionen

### Nächste Schritte

Für die UI-Integration (z.B. Streamlit) können die Zielwerte als Eingabefelder bereitgestellt werden:
- Jahr 2030: Haushalte, Gewerbe, Landwirtschaft [TWh]
- Jahr 2045: Haushalte, Gewerbe, Landwirtschaft [TWh]

Die Ergebnisse können dann mit den bestehenden Plotting-Funktionen visualisiert werden.
