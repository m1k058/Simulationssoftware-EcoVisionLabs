# Überblick
Implementation des Wirtschaftlichkeitsmoduls

Festzulegende Parameter sind:
- CAPEX (Investitionskosten) in `EUR/kW` für alle zu Ausbauende Erzeuger/Speicher (siehe unten)
- OPEX (Betriebskosten) in `% von CAPEX pro Jahr` oder `Eur/kW/Jahr` für alle Erzeuger und Speicher (siehe unten)
- Lebensdauer (Nutzungsdauer) in `Jahren` für alle zu Ausbauende Erzeuger/Speicher (siehe unten)
- WACC (Weighted Average Cost of Capital) Zinssatz für Erneuerbare Erzeuger (standart ist 5-7%)

# Kostenparameter (Datenbasis: Fraunhofer ISE 2024 & Ergänzungen)

Alle Werte sind auf Systemebene umgerechnet:
* **Invest (CAPEX):** EUR pro MW (Leistung) bzw. EUR pro MWh (Speicherkapazität).
* **Fixe Betriebskosten (OPEX Fix):** EUR pro MW pro Jahr.
* **Variable Betriebskosten (OPEX Var):** EUR pro MWh (erzeugte Energie).

## 1. Technologien

| Technologie | CAPEX Min [EUR/MW] | CAPEX Max [EUR/MW] | OPEX Fix [EUR/MW/a] | OPEX Var [EUR/MWh] | Lebens- dauer [a] | Effizienz | Brennstoff-Typ | Anmerkung |
|---|---|---|---|---|---|---|---|---|
| **Erdgas (Gasturbine)** | 450.000 | 700.000 | 23.000 | 4,00 | 30 | 0.40 | Erdgas | |
| **Biomasse** | 3.470.000 | 5.790.000 | 185.000 | 4,00 | 25 | 0.45 | Biomasse | |
| **Wasserkraft** | ❓ (0) | ❓ (0) | ❓ (15.000) | - | 60 | 0.90 | - | |
| **Wind Offshore** | 2.200.000 | 3.400.000 | 39.000 | 8,00 | 25 | 1.00 | - | |
| **Wind Onshore** | 1.300.000 | 1.900.000 | 32.000 | 7,00 | 25 | 1.00 | - | |
| **Photovoltaik** | 700.000 | 900.000 | 13.300 | - | 30 | 1.00 | - | |
| **Elektrolyseur (H2)** | ❓ (800.000) | ❓ (1.200.000) | ❓ (20.000) | - | 20 | 0.68 | - | H2 Erzeugung|
| **Wasserstoffspeicher**| ❓ (400.000) | ❓ (600.000) | ❓ (5.000) | - | 30 | 1.00 | - | H2 Speicherung |
| **H2 Elektrifizierung** | 550.000 | 1.200.000 | 23.000 | 5,00 | 30 | 0.40 | Wasserstoff | H2 Elektrifizierung|
| **Batteriespeicher** | 400.000 | 600.000 | 10.000 | - | 15 | 0.92 | - | |
| **Pumpspeicher** | ❓ (0) | ❓ (0) | ❓ (10.000) | - | 60 | 0.85 | - | |

> **Hinweis zu ❓:** Werte in Klammern sind Schätzwerte (Bestandsanlagen oder fehlende Marktdaten), die verwendet werden sollen, solange keine genauen Quellen vorliegen.
> **Hinweis Speicher:** CAPEX bei Batterien und H2-Speichern bezieht sich auf die Kapazität (EUR/MWh).

---

## 2. Rohstoffpreise

Preise für variable Kosten (Brennstoffe & CO2).

| Rohstoff | Preis [EUR/MWh_th] | Anmerkung |
|---|---|---|
| **Erdgas** | ❓ (35.00) | Importpreis Prognose 2030 |
| **Wasserstoff** | ❓ (140.00) | Import/Erzeugung Mix |
| **Biomasse** | ❓ (30.00) | Feste Biomasse / Hackschnitzel |
| **CO2-Zertifikat**| ❓ (125.00) | Preis pro Tonne (EUR/t) ! |

# Umsetzung (Technische Logik)

Die Berechnung erfolgt nach der **Annuitätenmethode**. Damit werden die einmaligen Investitionskosten auf jährliche Raten umgelegt, um sie mit den laufenden Betriebskosten vergleichbar zu machen.

### 1. Hilfsfunktion: Wiedergewinnungsfaktor (Annuity Factor)
Dieser Faktor wandelt den Gesamt-Invest in eine Jahresrate um.

$$ANF = \frac{WACC \cdot (1+WACC)^n}{(1+WACC)^n - 1}$$

* `WACC`: Zinssatz (z.B. 0.06)
* `n`: Lebensdauer in Jahren

### 2. Berechnung pro Technologie
Für jede Technologie $i$ (z.B. Wind Onshore) wird berechnet:

**A. Jährliche Kapitalkosten (CAPEX_annual):**
$$Kost_{Kapital, i} = P_{installiert, i} \cdot Kosten_{Invest, i} \cdot ANF_i$$
*(Falls die Tech kein CAPEX benötigt (z.B. Wasserkraft), ist dieser Wert 0)*

**B. Jährliche Fixe Betriebskosten (OPEX_fix):**
$$Kost_{Fix, i} = P_{installiert, i} \cdot Kosten_{OpexFix, i}$$
*(Oft als % des Invests angegeben, z.B. 2%)*

**C. Jährliche Variable Kosten (OPEX_var) - Nur thermische KW:**
$$Kost_{Var, i} = E_{ErzeugungJahr, i} \cdot \frac{Preis_{Brennstoff} + (Faktor_{CO2} \cdot Preis_{CO2})}{\eta_{Wirkungsgrad}}$$
* Bei Wind/PV/Speicher ist dieser Wert **0**.
* Bei H2-Elektrifizierung entfällt der CO2-Teil.

### 3. Gesamtsystem-Metriken (Output)

**Summe aller jährlichen Kosten (Total Annual Cost):**
$$TAC_{Gesamt} = \sum_{i} (Kost_{Kapital, i} + Kost_{Fix, i} + Kost_{Var, i})$$

**Stromgestehungskosten des Systems (System LCOE):**
$$LCOE_{System} = \frac{TAC_{Gesamt}}{E_{Verbrauch, Gesamt}}$$
* Einheit: `EUR/MWh` (oder durch 10 teilen für `ct/kWh`).


 # Steps

- [x] Über CapEx und OpEx informieren und implementation absprechen

- [x] .yaml Datei erweitern (wenn nötig)

- [x] CapEx OpEx Daten laden

- [x] CapEx OpEx brechnungsfunktion implementieren

- [x] Funktion via Streamlit Testen

- [ ] Funktion in UI fest einbauen 

# Kommentare

