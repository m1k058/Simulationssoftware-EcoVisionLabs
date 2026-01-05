# CAPEX/OPEX Implementierung im EconomicCalculator

**Datum:** 5. Januar 2026  
**Datei:** `source-code/data_processing/economic_calculator.py`

## Übersicht der Implementierung

Die Logik für CAPEX (Capital Expenditures) und OPEX (Operational Expenditures) wurde gemäß den präzisen Spezifikationen implementiert.

---

## 1. CAPEX (Investitionskosten)

### Bedeutung
Einmalige Kosten für den Bau der Anlagen.

### Eingabe-Einheit
- **EUR/MW** für Erzeugungsanlagen (Wind, Solar, etc.)
- **EUR/MWh** für Speicher

### Unterstützung für Ranges
Falls Daten als Liste `[Min, Max]` vorliegen, wird der **Durchschnittswert** berechnet:
```python
CAPEX = (Min + Max) / 2
```

### Berechnungen

#### 1a. Investitionsbedarf (Delta) - Nur neue Kapazität
```python
Investment = (Kapazität_Zieljahr - Kapazität_Basisjahr) * Spezifische_CAPEX
```
- Nur positive Deltas werden berücksichtigt
- Wird in `investment_by_tech` gespeichert

#### 1b. Kapitalkosten (für LCOE) - Auf Gesamtkapazität
```python
Annual_Capital_Cost = Kapazität_Zieljahr * Spezifische_CAPEX * Annuitätenfaktor
```
- Der Annuitätenfaktor wird mit WACC und Lebensdauer berechnet
- Wird in `capex_annual_by_tech` gespeichert

### Implementierte Methode
```python
def _get_capex(self, params: Dict[str, Any]) -> float:
    """Extrahiere CAPEX aus Parametern.
    
    Unterstützt:
    - 'capex_eur_per_mw': Basis CAPEX
    - 'capex_eur_per_mwh': Für Speicher
    
    Konvertiert Liste [Min, Max] zu Durchschnitt.
    """
```

---

## 2. OPEX FIX (Fixe Betriebskosten)

### Bedeutung
Kosten, die jedes Jahr anfallen, **unabhängig** von der Auslastung:
- Wartung
- Personal
- Versicherung

### Eingabe-Einheit
**EUR/kW pro Jahr**

### Umrechnung zur Simulation
Die Simulation arbeitet mit **MW**, daher erforderliche Umrechnung:
```
1 kW = 0.001 MW
→ Multiplikator = 1000
```

### Berechnung
```python
Annual_Fix_Cost = Kapazität_Zieljahr_MW * (Input_Wert_EUR_per_kW * 1000)
```

### Implementierte Methode
```python
def _get_opex_fix(self, params: Dict[str, Any]) -> float:
    """Extrahiere OPEX FIX aus Parametern in EUR/kW.
    
    Quelle: 'opex_eur_per_kw_year' oder 'opex_fix_eur_per_kw_year'.
    Konvertiert Liste [Min, Max] zu Durchschnitt.
    """
```

---

## 3. OPEX VAR (Variable Betriebskosten)

### Bedeutung
Kosten pro erzeugter Energiemenge:
- Verschleiß
- Schmierstoffe
- **Brennstoffe** (nur bei thermischen Kraftwerken!)

### Eingabe-Einheit
**EUR/kWh_el**

### Umrechnung zur Simulation
Die Simulation arbeitet mit **MWh**, daher erforderliche Umrechnung:
```
1 kWh = 0.001 MWh
→ Multiplikator = 1000
```

### Berechnung - Basis (Verschleiß)
```python
Base_Var_Cost_EUR_per_MWh = Input_Wert_EUR_per_kWh * 1000
```

### Berechnung - Thermische Kraftwerke (mit Brennstoff)
```python
Total_Var_Cost = Base_Var_Cost_EUR_per_MWh + (Brennstoffpreis / Wirkungsgrad)
```

**Thermische Technologien:**
- Erdgas, Biomasse
- Steinkohle, Braunkohle
- Wasserstoff-Kraftwerke (H2)

**Nicht-thermische (kein Brennstoff):**
- Wind, Photovoltaik
- Wasserkraft
- Speicher

### Implementierte Methoden
```python
def _get_opex_var(self, params: Dict[str, Any]) -> float:
    """Extrahiere OPEX VAR aus Parametern in EUR/kWh."""

def _is_thermal_technology(self, tech_id: str, params: Dict[str, Any]) -> bool:
    """Prüfe, ob Technologie thermisch ist."""

def _get_variable_opex_cost(self, tech_id: str, year: int, 
                           efficiency: Optional[float], 
                           params: Dict[str, Any]) -> float:
    """Berechne Brennstoffkosten-Beitrag in EUR/MWh."""
```

---

## 4. Hilfsmethode: Normalisierung

### Zweck
Einheitliche Behandlung von Kostenwerten, insbesondere **Listen [Min, Max]**.

### Funktionalität
```python
def _normalize_cost_value(self, value: Any) -> float:
    """Normalisiere CAPEX/OPEX-Werte.
    
    - Liste [Min, Max] → Durchschnitt: (Min+Max)/2
    - Einzelwert → Direkte Konvertierung zu float
    - Fehler → 0.0
    """
```

---

## 5. Hauptmethode: `perform_calculation()`

### Prozess

1. **Initialisierung**
   - WACC und Quellparameter aus `ECONOMICS_CONSTANTS` laden
   - Akumulatoren initialisieren

2. **Technologie-Schleife** für jede Technologie:
   - CAPEX, OPEX FIX, OPEX VAR extrahieren
   - Kapazitäten (Basis- und Zieljahr) abrufen
   - **CAPEX berechnen:**
     - Investitionsbedarf (Delta)
     - Kapitalkosten (Annuität)
   - **OPEX FIX berechnen:**
     - Mit Umrechnung EUR/kW → EUR/MW (* 1000)
   - **OPEX VAR berechnen:**
     - Basis-Verschleiß (EUR/kWh * 1000)
     - + Brennstoffkosten (für Thermal)

3. **Aggregation**
   - Summen bilden
   - Pro Technologie speichern

4. **System-LCOE berechnen**
   ```python
   System_LCOE = Total_Annual_Cost / Total_Consumption
   ```
   Ausgabe in **ct/kWh** (Umrechnung: EUR/MWh * 0.1)

### Rückgabe
Dictionary mit Struktur:
```python
{
    "year": int,
    "total_investment_bn": float,          # Mrd. €
    "total_annual_cost_bn": float,         # Mrd. €/Jahr
    "system_lco_e": float,                 # ct/kWh
    "investment_by_tech": {...},           # Mrd. €
    "capex_annual_bn": float,              # Mrd. €/Jahr
    "opex_fix_bn": float,                  # Mrd. €/Jahr
    "opex_var_bn": float,                  # Mrd. €/Jahr
    "capex_annual_by_tech": {...},         # Mrd. €/Jahr
    "opex_fix_by_tech": {...},             # Mrd. €/Jahr
    "opex_var_by_tech": {...},             # Mrd. €/Jahr
}
```

---

## 6. Debug-Ausgaben

Die Methode gibt ausführliche Logs aus für:
- **Pro Technologie:**
  - CAPEX, OPEX FIX, OPEX VAR Eingabewerte
  - Kapazitäten (Basis / Ziel)
  - Investitionsbedarf und Kapitalkosten
  - Generation und Brennstoffkosten
  
- **Zusammenfassung:**
  - Gesamtinvestition
  - Gesamte jährliche Kosten
  - Gesamtverbrauch
  - System LCOE

**Format:** `[CALC DEBUG]` Präfix

---

## 7. Beispiel-Datenflusses

### Photovoltaik 2030
```
Eingabeparameter:
  CAPEX: 800.000 EUR/MW
  OPEX FIX: 12.000 EUR/MW/Jahr (wird als 12.000 EUR/kW gelesen)
  OPEX VAR: 0 EUR/kWh (kein Brennstoff)
  Lifetime: 25 Jahre

Kapazitäten:
  Basisjahr (2025): 50 MW
  Zieljahr (2030): 100 MW
  Delta: 50 MW

Berechnungen:
  Investment = 50 MW * 800.000 EUR/MW = 40 Mio. €
  Annuity_Factor = (1.05^25 * 0.05) / (1.05^25 - 1) ≈ 0.0710
  Annual_Capital = 100 MW * 800.000 * 0.0710 = 5,68 Mio. €/Jahr
  Annual_OpEx_Fix = 100 MW * (12.000 * 1000) = 1.200 Mio. €/Jahr
  Annual_OpEx_Var = Generation * 0 = 0 €/Jahr
```

### Erdgaskraftwerk 2030
```
Eingabeparameter:
  CAPEX: 600.000 EUR/MW
  OPEX FIX: 9.000 EUR/MW/Jahr
  OPEX VAR: 2 EUR/kWh (Verschleiß)
  Lifetime: 25 Jahre
  Efficiency: 45%
  Fuel Type: Erdgas

Kapazitäten:
  Basisjahr (2025): 30 MW
  Zieljahr (2030): 30 MW (keine Änderung)
  Delta: 0 MW

Berechnungen:
  Investment = 0 (kein Delta)
  Annual_Capital = 30 MW * 600.000 * 0.0710 = 1,28 Mio. €/Jahr
  Annual_OpEx_Fix = 30 MW * (9.000 * 1000) = 270 Mio. €/Jahr
  
  Annual_OpEx_Var:
    Base = 2 EUR/kWh * 1000 = 2.000 EUR/MWh
    Fuel = (Brennstoffpreis + CO2) / 0.45
    Total_Var_Cost = 2.000 + Fuel_Cost
    Annual = Generation_2030 * Total_Var_Cost
```

---

## 8. Wichtige Anmerkungen

✅ **Implementiert:**
- ✓ CAPEX-Delta für neue Kapazität
- ✓ CAPEX-Annuität für LCOE (auf Gesamtkapazität)
- ✓ OPEX FIX mit EUR/kW → EUR/MW Umrechnung (* 1000)
- ✓ OPEX VAR mit EUR/kWh → EUR/MWh Umrechnung (* 1000)
- ✓ Brennstoffkosten-Addition für thermische Kraftwerke
- ✓ Normalisierung von [Min, Max] Ranges
- ✓ Detaillierte Debug-Ausgaben

⚠️ **Voraussetzungen:**
- `ECONOMICS_CONSTANTS` muss in `constants.py` korrekt strukturiert sein
- Kapazitätsdaten müssen in MW vorliegen
- Generationsdaten müssen in MWh vorliegen
- Gesamtverbrauch muss in MWh vorliegen

---

## 9. Testing-Hinweise

Um die Implementierung zu testen:

1. **Test mit Fotovoltaik (einfach, kein Brennstoff)**
2. **Test mit Windkraft (mit Betriebskosten, kein Brennstoff)**
3. **Test mit Gaskraftwerk (mit Brennstoffkosten)**
4. **Test mit Speicher (andere CAPEX-Einheit)**

Debugging aktivieren durch Konsolenausgaben unter `[CALC DEBUG]`.
