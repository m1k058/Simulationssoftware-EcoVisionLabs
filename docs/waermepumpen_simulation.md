# Wärmepumpen-Simulation - Dokumentation

## Übersicht

Die Wärmepumpen-Simulation berechnet den stündlichen Stromverbrauch von Wärmepumpen basierend auf:
- Außentemperatur (Wetterdaten)
- Standardlastprofilen für Wärmepumpen
- Anzahl installierter Wärmepumpen
- Jahreswärmebedarf pro Wärmepumpe
- Durchschnittlichem COP (Coefficient of Performance)

## Funktion

`simulate_consumption_heatpump()` in [simulation.py](../source-code/data_processing/simulation.py)

### Parameter

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `weather_df` | DataFrame | Wetterdaten mit Außentemperatur (z.B. "Lufttemperatur-2019") |
| `hp_profile_matrix` | DataFrame | BDEW-Lastprofil-Matrix für Wärmepumpen (96 Zeitschritte/Tag × Temperaturstufen) |
| `n_heatpumps` | int | Anzahl der installierten Wärmepumpen |
| `Q_th_a` | float | Jahreswärmebedarf pro Wärmepumpe [kWh] |
| `COP_avg` | float | Durchschnittlicher Coefficient of Performance |
| `dt` | float | Zeitintervall in Stunden (0.25 für 15 Minuten) |
| `simu_jahr` | int | Simulationsjahr (z.B. 2030) |
| `debug` | bool | Debug-Modus (optional) |

### Rückgabewert

DataFrame mit Spalten:
- `Zeitpunkt`: DateTime-Index mit Viertelstunden-Auflösung
- `Wärmepumpen [MWh]`: Stromverbrauch in MWh pro Zeitschritt

## Berechnungslogik

### 1. Wetterdaten-Vorbereitung
- Konvertierung auf 15-Minuten-Auflösung
- Entfernung von Duplikaten (Zeitumstellung)
- Interpolation fehlender Werte

### 2. Lastprofil-Normierung
- Berechnung der Jahressumme aller Profilwerte
- Normierungsfaktor: `f = Q_th_a / summe_lp_dt`

### 3. Viertelstundenwerte berechnen
Für jeden Zeitschritt:
1. **Profilwert holen**: `lp_wert = get_hp_faktor(time, temp)`
   - Temperaturstufen: -14°C bis +17°C (außerhalb: LOW/HIGH)
2. **Thermische Leistung**: `P_th = lp_wert × f` [kW]
3. **Elektrische Leistung (pro WP)**: `P_el = P_th / COP_avg` [kW]
4. **Gesamtleistung**: `P_el_ges = P_el × n_heatpumps` [MW]
5. **Energie**: `E = P_el_ges × dt` [MWh]

## Beispiel

```python
# Agora 2030 Szenario
df_heatpump = simulate_consumption_heatpump(
    weather_df=weather_2019,
    hp_profile_matrix=hp_matrix,
    n_heatpumps=3_000_000,      # 3 Mio. Wärmepumpen
    Q_th_a=51_000,              # 51 MWh Wärmebedarf/Jahr
    COP_avg=3.4,                # COP 3.4
    dt=0.25,                    # 15 Minuten
    simu_jahr=2030,
    debug=False
)

# Erwarteter Jahresverbrauch: (3M × 51.000 kWh) / 3.4 = 45 TWh
```

## Konfiguration im Szenario

```yaml
target_heat_pump_parameters:
  2030:
    installed_units: 3000000                    # Anzahl Wärmepumpen
    annual_heat_demand_kwh: 51000               # Wärmebedarf pro WP [kWh]
    cop_avg: 3.4                                # Durchschnittlicher COP
    weather_data: Lufttemperatur-2019           # Wetterdatensatz
    load_profile: Wärmepumpen Lastprofile       # Lastprofil-Matrix
```

## Integration in Gesamtsimulation

Die Wärmepumpen-Simulation wird automatisch in `simulate_consumption_all()` integriert:
- Merge mit BDEW-Verbrauch (Haushalte, Gewerbe, Landwirtschaft)
- Outer-Merge, damit keine Zeitpunkte verloren gehen
- Automatisches Fallback auf Nullwerte bei Fehlern


Ausführen: `python tests/test_heatpump_simulation.py`

## Datenquellen

- **Wetterdaten**: DWD (Deutscher Wetterdienst) Lufttemperatur
- **Lastprofile**: Standardlastprofile für Wärmepumpen

## Bekannte Einschränkungen

1. **Konstanter COP**: Der COP wird als Jahresdurchschnitt angenommen (vereinfacht, tatsächlich temperaturabhängig)
2. **Keine Speicher**: Wärmespeicher werden nicht berücksichtigt
3. **Vereinfachtes Lastprofil**: Nur Außentemperatur-abhängig (keine Gebäudetypologie, Nutzerverhalten)

