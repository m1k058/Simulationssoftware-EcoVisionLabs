# Simulationsmodule

Die einzelnen Berechnungsmodule in `data_processing/`.

## simulation_engine.py

**Zweck:** Koordiniert alle Simulationen

**Hauptaufgaben:**
- Ruft alle Submodule in der richtigen Reihenfolge auf
- Sammelt Ergebnisse
- Berechnet Gesamtbilanz

**Ablauf:**
1. Generation (Wind, Solar, etc.)
2. Consumption (Haushalte, Gewerbe, etc.)
3. Spezielle Verbraucher (E-Mobility, Wärmepumpen)
4. Storage (Batterien, Wasserstoff)
5. Balance (Angebot - Nachfrage)
6. Economics (Kosten, Emissionen)

**Wichtige Methode:**
```python
engine = SimulationEngine(dm, cfg, sm)
results = engine.run_simulation(year=2030, scenario_data=scenario)
```

---

## generation_simulation.py

**Zweck:** Berechnet Stromerzeugung

**Technologien:**
- Wind Onshore/Offshore
- Photovoltaik
- Biomasse
- Wasserkraft
- Geothermie
- Erdgas/Kohle (Backup)

**Methodik:**
- Nutzt historische Einspeisedaten als Profil
- Skaliert auf Zielkapazität aus Szenario
- Liefert stündliche Zeitreihe (8760h)

**Beispiel:**
```python
# Szenario: 215 GW Solar in 2030
# Historisches Profil: 54 GW in 2019
# Skalierung: 215/54 = 4x
# Result: 8760 Stundenwerte mit 4x Erzeugung
```

---

## consumption_simulation.py

**Zweck:** Berechnet Stromverbrauch

**Verbrauchsgruppen:**
- Haushalt (BDEW H0-Profil)
- Gewerbe (BDEW G0-Profil)
- Landwirtschaft (BDEW L0-Profil)

**Methodik:**
- Nutzt BDEW-Standardlastprofile
- Normiert auf Jahresverbrauch aus Szenario
- Liefert stündliche Zeitreihe

---

## e_mobility_simulation.py

**Zweck:** Simuliert Ladeverhalten von E-Autos

**Parameter:**
- Ziel-Jahresverbrauch (TWh)
- Ladevariante (Smart/Dumb Charging)

**Methodik:**
- Typisches Ladeprofil (mehr am Abend)
- Optionale Flexibilität (Smart Charging)
- Liefert Lastprofil

---

## heat_pump_simulation.py

**Zweck:** Simuliert Wärmepumpen-Stromverbrauch


**Parameter:**
- Anzahl Wärmepumpen
- COP (Coefficient of Performance)
- Außentemperatur (aus Rohdaten)

**Methodik:**
- COP hängt von Temperatur ab (kälter = mehr Strom)
- Stündliche Berechnung für jede WP
- Numba-optimiert (sonst zu langsam)


---

## storage_simulation.py

**Zweck:** Simuliert Speichersysteme

**Technologien:**
- Batteriespeicher (Kurzzeit)
- Pumpspeicher
- Wasserstoff (Langzeit)

**Methodik:**
- Lädt wenn Überschuss
- Entlädt wenn Defizit
- Berücksichtigt Wirkungsgrad


---

## balance_calculator.py

**Zweck:** Berechnet Angebot - Nachfrage

**Hauptaufgabe:**
```
Bilanz = Erzeugung - Verbrauch + Speicher
```

**Ergebnisse:**
- Überschuss (positiv)
- Defizit (negativ)
- Residuallast
- Autarkiegrad

---

## economic_calculator.py

**Zweck:** Berechnet Kosten und Emissionen

**Metriken:**
- CAPEX (Investitionskosten)
- OPEX (Betriebskosten)
- LCOE (Levelized Cost of Energy)
- CO2-Emissionen

**Datenquelle:**
- Kosten aus Szenario oder Defaults
- Emissionsfaktoren aus config

---

## scoring_system.py

**Zweck:** Bewertet Szenarien

**Kriterien:**
- Technische Machbarkeit
- Wirtschaftlichkeit
- Klimaziel-Erreichung
- Versorgungssicherheit

**Output:** Score von 0-100
